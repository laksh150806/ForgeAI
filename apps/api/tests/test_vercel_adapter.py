from app.services.vercel_adapter import (
    normalize_vercel_build_events,
    normalize_vercel_deployments,
)


def test_normalize_vercel_deployment_with_git_sha():
    raw = {
        "deployments": [{
            "uid": "dpl_123",
            "readyState": "READY",
            "target": "production",
            "url": "forgeai.vercel.app",
            "ready": 1791266400000,
            "meta": {"githubCommitSha": "abcdef1234567890"},
        }]
    }
    events = normalize_vercel_deployments(raw, "prj_123")

    assert len(events) == 1
    assert events[0].event_type == "deploy"
    assert events[0].deploy_sha == "abcdef1234567890"
    assert events[0].source == "vercel"


def test_normalize_vercel_failed_deployment():
    raw = {
        "deployments": [{
            "uid": "dpl_bad",
            "readyState": "ERROR",
            "created": 1791266400000,
            "meta": {},
        }]
    }
    event = normalize_vercel_deployments(raw, "prj_123")[0]

    assert event.event_type == "failure"
    assert event.severity == "error"


def test_normalize_vercel_build_error():
    raw = [{
        "id": "evt_1",
        "type": "stderr",
        "created": 1791266460000,
        "payload": {"text": "Error: failed to compile route"},
    }]
    events = normalize_vercel_build_events(
        raw,
        project_id="prj_123",
        deployment_id="dpl_123",
        deploy_sha="abcdef",
    )

    assert len(events) == 1
    assert events[0].event_type == "error"
    assert events[0].deploy_sha == "abcdef"


def test_vercel_event_ids_are_deterministic():
    raw = [{
        "id": "evt_stable",
        "type": "stdout",
        "created": 1791266460000,
        "payload": {"text": "build complete"},
    }]
    first = normalize_vercel_build_events(
        raw,
        project_id="prj_123",
        deployment_id="dpl_123",
        deploy_sha=None,
    )[0]
    second = normalize_vercel_build_events(
        raw,
        project_id="prj_123",
        deployment_id="dpl_123",
        deploy_sha=None,
    )[0]

    assert first.event_id == second.event_id
