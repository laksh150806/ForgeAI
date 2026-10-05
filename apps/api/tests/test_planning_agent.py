from types import SimpleNamespace

from app.services.planning_agent import _validation_commands, build_plan


def _investigation_with_evidence():
    evidence = [
        SimpleNamespace(path="app/auth.py"),
        SimpleNamespace(path="tests/test_auth.py"),
    ]
    hypothesis = SimpleNamespace(confidence=0.82)
    return SimpleNamespace(evidence=evidence, hypothesis=hypothesis)


def test_build_plan_targets_ranked_files() -> None:
    plan = build_plan("fix expired token handling", _investigation_with_evidence())
    assert plan.target_files == ["app/auth.py", "tests/test_auth.py"]
    assert len(plan.steps) == 3
    assert plan.confidence == 0.82


def test_validation_commands_cover_python() -> None:
    commands = _validation_commands(["app/auth.py"])
    assert "pytest -q" in commands


def test_validation_commands_cover_web() -> None:
    commands = _validation_commands(["src/auth.ts"])
    assert "npm run build --if-present" in commands


def test_planning_public_context_loader_is_quota_free() -> None:
    import inspect
    from app.services import planning_agent

    source = inspect.getsource(planning_agent._load_patch_context)
    assert "public_repository_checkout" in source
    assert "if not os.getenv(\"GITHUB_TOKEN\")" in source
