from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.schemas.telemetry import TelemetryTimelineEvent
from app.services.telemetry_timeline import nearest_preceding_deploy


def _event(*, minutes: int, event_type: str, severity: str = "info", deploy_sha: str | None = None):
    base = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    return TelemetryTimelineEvent(
        event_id=uuid4(),
        observed_at=base + timedelta(minutes=minutes),
        source="test",
        event_type=event_type,
        severity=severity,
        service="api",
        message=event_type,
        deploy_sha=deploy_sha,
        metadata={},
    )


def test_nearest_preceding_deploy_ignores_later_deploy():
    events = [
        _event(minutes=0, event_type="deploy", deploy_sha="aaa1111"),
        _event(minutes=4, event_type="error", severity="error"),
        _event(minutes=8, event_type="deploy", deploy_sha="bbb2222"),
    ]

    failure_at = events[1].observed_at
    deploy = nearest_preceding_deploy(events, failure_at)

    assert deploy is not None
    assert deploy.deploy_sha == "aaa1111"


def test_nearest_preceding_deploy_prefers_closest_prior_release():
    events = [
        _event(minutes=0, event_type="deploy", deploy_sha="old1111"),
        _event(minutes=3, event_type="release", deploy_sha="new2222"),
        _event(minutes=5, event_type="crash", severity="critical"),
    ]

    deploy = nearest_preceding_deploy(events, events[2].observed_at)

    assert deploy is not None
    assert deploy.deploy_sha == "new2222"


def test_no_preceding_deploy_returns_none():
    events = [
        _event(minutes=2, event_type="error", severity="error"),
        _event(minutes=5, event_type="deploy", deploy_sha="later333"),
    ]

    assert nearest_preceding_deploy(events, events[0].observed_at) is None
