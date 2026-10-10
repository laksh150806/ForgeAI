from app.services.sentry_adapter import (
    _next_cursor,
    normalize_sentry_events,
    release_commit_sha,
)


def _sample_event():
    return {
        "eventID": "evt_123",
        "dateCreated": "2026-10-10T04:30:00Z",
        "level": "error",
        "title": "CheckoutError: payment failed",
        "culprit": "checkout.views.submit",
        "groupID": "issue_42",
        "release": {"version": "forgeai@abcdef1234567890"},
        "tags": [
            {"key": "environment", "value": "production"},
            {"key": "release", "value": "forgeai@abcdef1234567890"},
        ],
        "entries": [{
            "type": "exception",
            "data": {
                "values": [{
                    "type": "CheckoutError",
                    "value": "payment failed",
                    "stacktrace": {
                        "frames": [
                            {
                                "filename": "app/service.py",
                                "function": "charge",
                                "lineNo": 21,
                            },
                            {
                                "filename": "app/routes.py",
                                "function": "submit",
                                "lineNo": 88,
                            },
                        ]
                    },
                }]
            },
        }],
    }


def test_normalize_sentry_event_preserves_stack_and_release_sha():
    events = normalize_sentry_events(
        [_sample_event()],
        organization="acme",
        project="checkout-api",
        environment=None,
    )

    assert len(events) == 1
    event = events[0]
    assert event.source == "sentry"
    assert event.event_type == "error"
    assert event.service == "checkout-api"
    assert event.deploy_sha == "abcdef1234567890"
    assert "CheckoutError: payment failed" in event.message
    assert "at charge (app/service.py:21)" in event.message
    assert "at submit (app/routes.py:88)" in event.message
    assert event.metadata["sentry_issue_id"] == "issue_42"
    assert event.metadata["sentry_environment"] == "production"


def test_sentry_event_ids_are_deterministic():
    first = normalize_sentry_events(
        [_sample_event()],
        organization="acme",
        project="checkout-api",
        environment="production",
    )[0]
    second = normalize_sentry_events(
        [_sample_event()],
        organization="acme",
        project="checkout-api",
        environment="production",
    )[0]

    assert first.event_id == second.event_id


def test_release_sha_is_conservative_when_release_has_no_git_hash():
    event = {"release": {"version": "checkout-api@2026.10.10"}}
    assert release_commit_sha(event) is None


def test_next_cursor_reads_only_available_next_page():
    link = (
        '<https://sentry.io/api/0/projects/a/b/events/?cursor=prev>; '
        'rel="previous"; results="false"; cursor="prev", '
        '<https://sentry.io/api/0/projects/a/b/events/?cursor=next123>; '
        'rel="next"; results="true"; cursor="next123"'
    )
    assert _next_cursor(link) == "next123"
