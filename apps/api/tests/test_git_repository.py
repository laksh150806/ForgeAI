import asyncio
from pathlib import Path

from app.services.github_client import GitHubRepositoryRef
from app.services import git_repository
from app.services.git_repository import checkout_repository_commit, public_clone_url


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
