from fastapi import HTTPException

from app.services.github_client import parse_github_repository_url
from app.services.repository_intelligence import classify_path


def test_parse_standard_github_url() -> None:
    ref = parse_github_repository_url("https://github.com/openai/openai-python")
    assert ref.owner == "openai"
    assert ref.name == "openai-python"


def test_parse_git_suffix() -> None:
    ref = parse_github_repository_url("https://github.com/openai/openai-python.git")
    assert ref.full_name == "openai/openai-python"


def test_reject_non_github_url() -> None:
    try:
        parse_github_repository_url("https://example.com/owner/repo")
    except HTTPException as exc:
        assert exc.status_code == 422
    else:
        raise AssertionError("Expected HTTPException")


def test_source_file_classification() -> None:
    file = classify_path("apps/api/main.py", 250)
    assert file.kind == "source"
    assert file.language == "Python"
    assert file.ignored is False


def test_dependency_directory_is_ignored() -> None:
    file = classify_path("node_modules/pkg/index.js", 100)
    assert file.ignored is True
    assert file.ignore_reason == "generated_or_dependency_directory"


def test_lockfile_is_ignored() -> None:
    file = classify_path("package-lock.json", 500)
    assert file.ignored is True
    assert file.ignore_reason == "lockfile"
