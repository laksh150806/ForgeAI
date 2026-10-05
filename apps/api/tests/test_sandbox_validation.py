from pathlib import Path

from app.schemas.planning import PatchFile
from app.services.sandbox_validation import safe_patch_paths, validation_specs


def test_rejects_parent_traversal_patch_path() -> None:
    patches = [
        PatchFile(
            path="../secret.txt",
            rationale="bad",
            unified_diff="--- a/secret.txt\n+++ b/secret.txt\n",
        )
    ]
    assert safe_patch_paths(patches) is False


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
    specs = validation_specs(tmp_path)
    assert "python_compile" in specs
    assert "python_tests" in specs


def test_detects_node_validation(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}")
    specs = validation_specs(tmp_path)
    assert "node_build" in specs
    assert "node_tests" in specs
