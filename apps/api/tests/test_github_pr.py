from types import SimpleNamespace

from app.services.github_pr import _pr_body


def test_pr_body_contains_validation_and_files() -> None:
    validation = SimpleNamespace(
        sandbox="docker",
        passed=True,
        safe_to_propose_pr=True,
        commands=[
            SimpleNamespace(
                command="Python tests",
                status="passed",
                duration_ms=123,
            )
        ],
    )

    body = _pr_body(
        "Fix expired token handling",
        validation,
        ["app/auth.py", "tests/test_auth.py"],
    )

    assert "Fix expired token handling" in body
    assert "app/auth.py" in body
    assert "Python tests" in body
    assert "PR gate: **OPEN**" in body
