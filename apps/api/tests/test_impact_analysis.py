from app.services.git_repository import GitCommitSnapshot
from app.services.impact_analysis import (
    _bounded,
    _changed_nodes,
    build_symbol_graph,
    parse_changed_lines,
)


def test_parse_changed_lines_and_map_to_python_symbol():
    source = """from fastapi import APIRouter

router = APIRouter()

def helper():
    return 1

@router.get("/health")
def health():
    return helper()
"""
    nodes, edges = build_symbol_graph({"app/routes/health.py": (source, "Python")})

    patch = """diff --git a/app/routes/health.py b/app/routes/health.py
--- a/app/routes/health.py
+++ b/app/routes/health.py
@@ -5,1 +5,2 @@
-def helper():
+def helper():
+    # changed
"""
    commit = GitCommitSnapshot(
        sha="a" * 40,
        authored_at_epoch=0,
        subject="change helper",
        changed_files=["app/routes/health.py"],
        patch=patch,
    )

    ranges = parse_changed_lines(patch)
    assert ranges["app/routes/health.py"] == [(5, 6)]

    changed = _changed_nodes(nodes, commit)
    assert [node.symbol for node in changed] == ["helper"]

    helper_id = "app/routes/health.py::helper"
    health_id = "app/routes/health.py::health"
    reverse = {}
    for edge in edges:
        reverse.setdefault(edge.target, set()).add(edge.source)

    callers, paths = _bounded({helper_id}, reverse, 3)
    assert health_id in callers
    assert paths[health_id] == [helper_id, health_id]
    assert nodes[health_id].entrypoint is True


def test_build_symbol_graph_resolves_unique_cross_file_call():
    files = {
        "app/service.py": (
            """def load_user():
    return {"id": 1}
""",
            "Python",
        ),
        "app/routes.py": (
            """from app.service import load_user

def handle_request():
    return load_user()
""",
            "Python",
        ),
    }
    nodes, edges = build_symbol_graph(files)

    assert "app/service.py::load_user" in nodes
    assert "app/routes.py::handle_request" in nodes
    assert any(
        edge.source == "app/routes.py::handle_request"
        and edge.target == "app/service.py::load_user"
        and edge.relation == "calls"
        for edge in edges
    )


def test_typescript_call_graph_is_approximate_but_directional():
    files = {
        "src/data.ts": (
            """export function loadData() {
  return 1;
}
""",
            "TypeScript",
        ),
        "src/page.ts": (
            """import { loadData } from "./data";

export function renderPage() {
  return loadData();
}
""",
            "TypeScript",
        ),
    }
    nodes, edges = build_symbol_graph(files)

    assert "src/data.ts::loadData" in nodes
    assert "src/page.ts::renderPage" in nodes
    assert any(
        edge.source == "src/page.ts::renderPage"
        and edge.target == "src/data.ts::loadData"
        for edge in edges
    )
