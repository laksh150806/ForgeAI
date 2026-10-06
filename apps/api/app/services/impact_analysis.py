from __future__ import annotations

import ast
import re
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from fastapi import HTTPException

from app.schemas.impact import (
    ImpactAnalysisRequest,
    ImpactAnalysisResponse,
    ImpactNode,
)
from app.services.code_intelligence import extract_js_symbols, extract_python_symbols
from app.services.git_repository import GitCommitSnapshot, public_repository_checkout, recent_commit_history
from app.services.repository_intelligence import classify_path


HUNK_RE = re.compile(r"^@@\s+-\d+(?:,\d+)?\s+\+(\d+)(?:,(\d+))?\s+@@")
DIFF_RE = re.compile(r"^diff --git a/(.+?) b/(.+)$")
JS_CALL_RE = re.compile(r"\b([A-Za-z_$][\w$]*)\s*\(")
JS_IMPORT_RE = re.compile(r"(?:from\s+|import\s*\()?['\"]([^'\"]+)['\"]")
ROUTE_DECORATORS = {"get", "post", "put", "patch", "delete", "options", "head", "api_route", "websocket"}


@dataclass(frozen=True)
class GraphEdge:
    source: str
    target: str
    relation: str


@dataclass
class ParsedFile:
    path: str
    nodes: list[ImpactNode]
    calls: dict[str, set[str]]
    imports: set[str]


def _node_id(path: str, symbol: str) -> str:
    return f"{path}::{symbol}"


def _module_node(path: str) -> ImpactNode:
    return ImpactNode(
        id=_node_id(path, "__module__"),
        path=path,
        symbol="__module__",
        kind="module",
        line_start=1,
        line_end=None,
        entrypoint=False,
    )


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _decorator_name(node: ast.AST) -> str | None:
    target = node.func if isinstance(node, ast.Call) else node
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Attribute):
        return target.attr
    return None


def _parse_python(path: str, source: str) -> ParsedFile:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ParsedFile(path=path, nodes=[_module_node(path)], calls={}, imports=set())

    symbols = extract_python_symbols(source)
    nodes: list[ImpactNode] = [_module_node(path)]
    calls: dict[str, set[str]] = defaultdict(set)
    imports: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    symbol_ast = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    by_key = {(node.name, node.lineno): node for node in symbol_ast}

    for symbol in symbols:
        ast_node = by_key.get((symbol.name, symbol.line_start))
        entrypoint = False
        if isinstance(ast_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            entrypoint = any(
                (_decorator_name(decorator) or "").lower() in ROUTE_DECORATORS
                for decorator in ast_node.decorator_list
            )
        graph_node = ImpactNode(
            id=_node_id(path, symbol.name),
            path=path,
            symbol=symbol.name,
            kind=symbol.kind,
            line_start=symbol.line_start,
            line_end=symbol.line_end,
            entrypoint=entrypoint,
        )
        nodes.append(graph_node)

        if ast_node is not None:
            for child in ast.walk(ast_node):
                if isinstance(child, ast.Call):
                    name = _call_name(child.func)
                    if name and name != symbol.name:
                        calls[graph_node.id].add(name)

    return ParsedFile(path=path, nodes=nodes, calls=dict(calls), imports=imports)


def _js_symbol_nodes(path: str, source: str) -> list[ImpactNode]:
    raw = extract_js_symbols(source)
    lines = source.splitlines()
    nodes = [_module_node(path)]
    for index, symbol in enumerate(raw):
        line_end = (raw[index + 1].line_start - 1) if index + 1 < len(raw) else max(len(lines), symbol.line_start)
        line_text = lines[symbol.line_start - 1] if symbol.line_start <= len(lines) else ""
        entrypoint = bool(re.search(r"\b(?:GET|POST|PUT|PATCH|DELETE)\b", symbol.name)) or "route" in path.lower()
        nodes.append(
            ImpactNode(
                id=_node_id(path, symbol.name),
                path=path,
                symbol=symbol.name,
                kind=symbol.kind,
                line_start=symbol.line_start,
                line_end=line_end,
                entrypoint=entrypoint,
            )
        )
    return nodes


def _parse_js(path: str, source: str) -> ParsedFile:
    nodes = _js_symbol_nodes(path, source)
    calls: dict[str, set[str]] = defaultdict(set)
    imports = set(JS_IMPORT_RE.findall(source))
    lines = source.splitlines()

    for node in nodes:
        if node.kind == "module":
            continue
        start = max(0, node.line_start - 1)
        end = node.line_end if node.line_end is not None else len(lines)
        body = "\n".join(lines[start:end])
        for match in JS_CALL_RE.finditer(body):
            name = match.group(1)
            if name != node.symbol and name not in {"if", "for", "while", "switch", "catch"}:
                calls[node.id].add(name)

    return ParsedFile(path=path, nodes=nodes, calls=dict(calls), imports=imports)


def _resolve_import(import_name: str, current_path: str, paths: set[str]) -> str | None:
    cleaned = import_name.strip()
    if not cleaned:
        return None

    current = PurePosixPath(current_path)
    candidates: list[str] = []

    if cleaned.startswith("."):
        base = current.parent
        for part in cleaned.split("/"):
            if part in {"", "."}:
                continue
            if part == "..":
                base = base.parent
            else:
                base = base / part
        stem = base.as_posix()
    else:
        stem = cleaned.replace(".", "/")

    for suffix in (".py", ".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.tsx", "/index.js"):
        candidates.append(stem + suffix)

    if cleaned.startswith("."):
        for candidate in list(candidates):
            candidates.append((current.parent / candidate).as_posix())

    for candidate in candidates:
        normalized = str(PurePosixPath(candidate))
        if normalized in paths:
            return normalized

    base_name = PurePosixPath(stem).name
    matches = [path for path in paths if PurePosixPath(path).stem == base_name]
    return matches[0] if len(matches) == 1 else None


def build_symbol_graph(files: dict[str, tuple[str, str | None]]) -> tuple[dict[str, ImpactNode], list[GraphEdge]]:
    parsed: list[ParsedFile] = []
    for path, (source, language) in files.items():
        if language == "Python":
            parsed.append(_parse_python(path, source))
        elif language in {"JavaScript", "TypeScript", "Vue", "Svelte"}:
            parsed.append(_parse_js(path, source))

    nodes = {node.id: node for item in parsed for node in item.nodes}
    paths = {item.path for item in parsed}
    by_symbol: dict[str, list[ImpactNode]] = defaultdict(list)
    for node in nodes.values():
        if node.kind != "module":
            by_symbol[node.symbol].append(node)

    edges: set[GraphEdge] = set()
    for item in parsed:
        module_id = _node_id(item.path, "__module__")
        for import_name in item.imports:
            target_path = _resolve_import(import_name, item.path, paths)
            if target_path:
                target = _node_id(target_path, "__module__")
                if target in nodes and target != module_id:
                    edges.add(GraphEdge(module_id, target, "imports"))

        for source_id, call_names in item.calls.items():
            source_node = nodes.get(source_id)
            if not source_node:
                continue
            for name in call_names:
                local = [
                    node for node in by_symbol.get(name, [])
                    if node.path == source_node.path
                ]
                candidates = local or by_symbol.get(name, [])
                if len(candidates) == 1:
                    edges.add(GraphEdge(source_id, candidates[0].id, "calls"))
                elif 1 < len(candidates) <= 3:
                    for candidate in candidates:
                        edges.add(GraphEdge(source_id, candidate.id, "references"))

    return nodes, sorted(edges, key=lambda edge: (edge.source, edge.target, edge.relation))


def parse_changed_lines(patch: str) -> dict[str, list[tuple[int, int]]]:
    changed: dict[str, list[tuple[int, int]]] = defaultdict(list)
    current_path: str | None = None

    for line in patch.splitlines():
        diff_match = DIFF_RE.match(line)
        if diff_match:
            current_path = diff_match.group(2)
            continue

        hunk = HUNK_RE.match(line)
        if hunk and current_path:
            start = int(hunk.group(1))
            count = int(hunk.group(2) or "1")
            if count > 0:
                changed[current_path].append((start, start + count - 1))

    return dict(changed)


def _changed_nodes(
    nodes: dict[str, ImpactNode],
    commit: GitCommitSnapshot,
) -> list[ImpactNode]:
    ranges = parse_changed_lines(commit.patch)
    result: dict[str, ImpactNode] = {}

    for path in commit.changed_files:
        file_nodes = [node for node in nodes.values() if node.path == path and node.kind != "module"]
        path_ranges = ranges.get(path, [])
        for node in file_nodes:
            node_end = node.line_end or node.line_start
            if any(start <= node_end and end >= node.line_start for start, end in path_ranges):
                result[node.id] = node

        if not any(node.path == path for node in result.values()):
            module = nodes.get(_node_id(path, "__module__"))
            if module:
                result[module.id] = module

    return sorted(result.values(), key=lambda node: (node.path, node.line_start, node.symbol))


def _runtime_matches(nodes: dict[str, ImpactNode], runtime_text: str) -> list[ImpactNode]:
    lowered = runtime_text.lower()
    if not lowered.strip():
        return []

    matches: dict[str, ImpactNode] = {}
    for node in nodes.values():
        filename = PurePosixPath(node.path).name.lower()
        symbol = node.symbol.lower()
        if node.path.lower() in lowered or (len(filename) > 4 and filename in lowered):
            matches[node.id] = node
        elif node.kind != "module" and len(symbol) > 3 and re.search(rf"\b{re.escape(symbol)}\b", lowered):
            matches[node.id] = node

    return sorted(matches.values(), key=lambda node: (node.path, node.line_start, node.symbol))


def _bounded(
    start_ids: set[str],
    adjacency: dict[str, set[str]],
    max_depth: int,
) -> tuple[set[str], dict[str, list[str]]]:
    seen = set(start_ids)
    queue = deque((node_id, 0, [node_id]) for node_id in start_ids)
    paths: dict[str, list[str]] = {}

    while queue:
        node_id, depth, path = queue.popleft()
        if depth >= max_depth:
            continue
        for neighbor in adjacency.get(node_id, set()):
            if neighbor not in seen:
                seen.add(neighbor)
                next_path = path + [neighbor]
                paths[neighbor] = next_path
                queue.append((neighbor, depth + 1, next_path))

    return seen - start_ids, paths


def _select_commit(history: list[GitCommitSnapshot], requested_sha: str | None) -> GitCommitSnapshot:
    if not history:
        raise HTTPException(status_code=404, detail="No Git commit history was available for impact analysis.")
    if not requested_sha:
        return history[0]

    for commit in history:
        if (
            commit.sha == requested_sha
            or commit.sha.startswith(requested_sha)
            or requested_sha.startswith(commit.sha[:7])
        ):
            return commit

    raise HTTPException(
        status_code=404,
        detail="Requested commit was not found inside the configured impact-analysis lookback window.",
    )


async def analyze_impact(payload: ImpactAnalysisRequest) -> ImpactAnalysisResponse:
    repository_url = str(payload.repository_url)
    depth = max(payload.lookback_commits + 2, 12)
    runtime_text = "\n".join(part for part in [payload.runtime_text, payload.stack_trace or ""] if part)

    async with public_repository_checkout(repository_url, depth=depth) as (ref, root, _):
        history = await recent_commit_history(root, limit=payload.lookback_commits)
        commit = _select_commit(history, payload.commit_sha)

        files: dict[str, tuple[str, str | None]] = {}
        candidates: list[tuple[str, str | None, Path]] = []
        for item in root.rglob("*"):
            if not item.is_file() or ".git" in item.parts:
                continue
            relative = item.relative_to(root).as_posix()
            try:
                size = item.stat().st_size
            except OSError:
                size = None
            classified = classify_path(relative, size)
            if classified.ignored or classified.kind != "source":
                continue
            if size is not None and size > 250_000:
                continue
            candidates.append((relative, classified.language, item))

        for relative, language, item in candidates[:160]:
            try:
                files[relative] = (item.read_text(encoding="utf-8", errors="replace"), language)
            except OSError:
                continue

    nodes, edges = build_symbol_graph(files)
    changed = _changed_nodes(nodes, commit)
    runtime_matches = _runtime_matches(nodes, runtime_text)

    forward: dict[str, set[str]] = defaultdict(set)
    reverse: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        forward[edge.source].add(edge.target)
        reverse[edge.target].add(edge.source)

    changed_ids = {node.id for node in changed}
    caller_ids, caller_paths = _bounded(changed_ids, reverse, payload.max_depth)
    downstream_ids, downstream_paths = _bounded(changed_ids, forward, payload.max_depth)

    callers = [nodes[node_id] for node_id in caller_ids if node_id in nodes]
    downstream = [nodes[node_id] for node_id in downstream_ids if node_id in nodes]
    entrypoints = [
        nodes[node_id]
        for node_id in caller_ids | changed_ids
        if node_id in nodes and nodes[node_id].entrypoint
    ]

    runtime_ids = {node.id for node in runtime_matches}
    direct_runtime_overlap = changed_ids & runtime_ids
    traversal_runtime_overlap = downstream_ids & runtime_ids

    score = 10.0 if changed else 0.0
    score += min(28.0, 14.0 * len(direct_runtime_overlap))
    score += min(18.0, 6.0 * len(traversal_runtime_overlap))
    score += min(18.0, 4.5 * len(entrypoints))
    score += min(14.0, 2.0 * len(callers))
    score += min(12.0, 1.2 * len(downstream))
    score = round(min(100.0, score), 2)

    confidence = round(min(0.98, 0.2 + (score / 100.0) * 0.75), 2) if score else 0.0

    evidence_paths: list[list[str]] = []
    for endpoint in entrypoints[:8]:
        path = caller_paths.get(endpoint.id)
        if path:
            evidence_paths.append(list(reversed(path)))
    for runtime_id in list(traversal_runtime_overlap)[:8]:
        path = downstream_paths.get(runtime_id)
        if path:
            evidence_paths.append(path)

    explanations = [
        f"Mapped commit {commit.sha[:8]} to {len(changed)} changed symbol/module node(s).",
        f"Graph contains {len(nodes)} nodes and {len(edges)} directed import/call/reference edges.",
    ]
    if runtime_matches:
        explanations.append(
            f"Runtime evidence matched {len(runtime_matches)} graph node(s); {len(direct_runtime_overlap)} directly changed and {len(traversal_runtime_overlap)} downstream."
        )
    if entrypoints:
        explanations.append(
            "Affected entrypoints: " + ", ".join(f"{node.symbol} ({node.path})" for node in entrypoints[:5]) + "."
        )
    if callers:
        explanations.append(f"Bounded upstream traversal found {len(callers)} caller/reference node(s).")
    if downstream:
        explanations.append(f"Bounded downstream traversal found {len(downstream)} dependency node(s).")
    if not runtime_matches:
        explanations.append("No explicit stack/runtime symbol match was found; blast radius is based on changed symbols and static graph reachability.")

    sort_key = lambda node: (node.path, node.line_start, node.symbol)
    return ImpactAnalysisResponse(
        repository=ref.full_name,
        commit_sha=commit.sha,
        graph_mode="static-symbol-graph+git-diff+runtime-match",
        graph_nodes=len(nodes),
        graph_edges=len(edges),
        changed_symbols=sorted(changed, key=sort_key)[:30],
        runtime_matches=sorted(runtime_matches, key=sort_key)[:30],
        callers=sorted(callers, key=sort_key)[:40],
        downstream=sorted(downstream, key=sort_key)[:40],
        affected_entrypoints=sorted(entrypoints, key=sort_key)[:20],
        evidence_paths=evidence_paths[:12],
        blast_radius_score=score,
        confidence=confidence,
        explanation=explanations,
    )
