from app.services.render_adapter import normalize_render_deploys, normalize_render_logs


def test_normalize_render_deploy_to_telemetry():
    raw = [{
        "id": "dep-123",
        "status": "live",
        "finishedAt": "2026-10-06T02:00:00Z",
        "trigger": "api",
        "commit": {"id": "abcdef123456", "message": "Fix checkout crash"},
    }]
    events = normalize_render_deploys(raw, "srv-abc")

    assert len(events) == 1
    assert events[0].event_type == "deploy"
    assert events[0].deploy_sha == "abcdef123456"
    assert events[0].service == "srv-abc"


def test_normalize_failed_render_deploy_as_failure():
    raw = [{
        "id": "dep-bad",
        "status": "build_failed",
        "updatedAt": "2026-10-06T02:00:00Z",
    }]
    events = normalize_render_deploys(raw, "srv-abc")

    assert events[0].event_type == "failure"
    assert events[0].severity == "error"


def test_normalize_render_error_log():
    raw = {
        "logs": [{
            "id": "log-1",
            "message": "Traceback: PaymentTimeout",
            "timestamp": "2026-10-06T02:05:00Z",
            "labels": [
                {"name": "level", "value": "error"},
                {"name": "type", "value": "app"},
            ],
        }]
    }
    events = normalize_render_logs(raw, "srv-abc")

    assert len(events) == 1
    assert events[0].event_type == "error"
    assert events[0].severity == "error"
    assert events[0].metadata["render_log_type"] == "app"


def test_render_event_ids_are_deterministic():
    raw = {
        "logs": [{
            "id": "log-stable",
            "message": "hello",
            "timestamp": "2026-10-06T02:05:00Z",
            "labels": [],
        }]
    }
    first = normalize_render_logs(raw, "srv-abc")[0]
    second = normalize_render_logs(raw, "srv-abc")[0]

    assert first.event_id == second.event_id
