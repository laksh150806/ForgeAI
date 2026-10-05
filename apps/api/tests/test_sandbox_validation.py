from pathlib import Path

from app.schemas.planning import PatchFile
from app.services.sandbox_validation import _safe_patch_paths, _validation_specs


def test_rejects_parent_traversal_patch_path() -> None:
    patches = [
        PatchFile(
            path="../secret.txt",
            rationale="bad",
            unified_diff="--- a/secret.txt\n+++ b/secret.txt\n",
        )
    ]
    assert _safe_patch_paths(patches) is False


def test_accepts_normal_patch_path() -> None:
    patches = [
        PatchFile(
            path="apps/api/app/main.py",
            rationale="normal",
            unified_diff="--- a/apps/api/app/main.py\n+++ b/apps/api/app/main.py\n",
        )
    ]
    assert safe_patch_paths(patches) is True


def test_detects_python_validation(tmp_path: Path) -> None:
    (tmp_path / "pytest.ini").write_text("[pytest]\n")
    specs = _validation_specs(tmp_path)
    labels = [item[0] for item in specs]
    assert "Python compile" in labels
    assert "Python tests" in labels


def test_detects_node_validation(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}")
    specs = validation_specs(tmp_path)
    labels = [item[0] for item in specs]
    assert "Node syntax/build" in labels
    assert "Node tests" in labels
