from app.services.github_client import GitHubRepositoryRef
from app.services.git_repository import public_clone_url


def test_public_clone_url() -> None:
    ref = GitHubRepositoryRef(owner="openai", name="example")
    assert public_clone_url(ref) == "https://github.com/openai/example.git"
