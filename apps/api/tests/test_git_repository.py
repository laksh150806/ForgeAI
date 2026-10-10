import asyncio
from pathlib import Path

from app.services.github_client import GitHubRepositoryRef
from app.services import git_repository
from app.services.git_repository import (
    checkout_repository_commit,
    commit_patch_for_files,
    public_clone_url,
)


def test_public_clone_url() -> None:
    ref = GitHubRepositoryRef(owner="openai", name="example")
    assert public_clone_url(ref) == "https://github.com/openai/example.git"



def test_checkout_repository_commit_materializes_target_snapshot(monkeypatch) -> None:
    calls = []

    async def fake_run_git(*args, cwd=None, timeout=90):
        calls.append((args, cwd, timeout))
        return 0, "", ""

    monkeypatch.setattr(git_repository, "_run_git", fake_run_git)

    asyncio.run(checkout_repository_commit(Path("/tmp/repo"), "abc123def456"))

    assert calls == [
        (("checkout", "--detach", "--force", "abc123def456"), Path("/tmp/repo"), 30)
    ]



def test_commit_patch_for_files_fetches_each_file_without_cross_file_truncation(monkeypatch) -> None:
    calls = []

    async def fake_run_git(*args, cwd=None, timeout=90):
        calls.append((args, cwd, timeout))
        path = args[-1]
        return 0, f"diff --git a/{path} b/{path}\n@@ -1 +1 @@\n-old\n+new\n", ""

    monkeypatch.setattr(git_repository, "_run_git", fake_run_git)

    patch = asyncio.run(
        commit_patch_for_files(
            Path("/tmp/repo"),
            "abc123def456",
            ["app/a.py", "app/b.py"],
        )
    )

    assert "diff --git a/app/a.py b/app/a.py" in patch
    assert "diff --git a/app/b.py b/app/b.py" in patch
    assert [call[0][-1] for call in calls] == ["app/a.py", "app/b.py"]
