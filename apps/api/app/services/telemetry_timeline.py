from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.incident import IncidentCorrelationRequest, RuntimeEvidence
from app.schemas.telemetry import (
    TelemetryTimelineEvent,
    TelemetryTimelineRequest,
    TelemetryTimelineResponse,
)
from app.services.incident_correlation import correlate_incident
from app.services.telemetry_store import recent_events


_FAILURE_TYPES = {"error", "exception", "failure", "crash", "alert"}
_FAILURE_SEVERITIES = {"error", "critical", "fatal"}
_DEPLOY_TYPES = {"deploy", "deployment", "release"}


def _is_failure(event: TelemetryTimelineEvent) -> bool:
    return (
        event.event_type.lower() in _FAILURE_TYPES
        or event.severity.lower() in _FAILURE_SEVERITIES
    )


def _is_deploy(event: TelemetryTimelineEvent) -> bool:
    return event.event_type.lower() in _DEPLOY_TYPES or bool(event.deploy_sha)


def nearest_preceding_deploy(
    events: list[TelemetryTimelineEvent],
    failure_at: datetime,
) -> TelemetryTimelineEvent | None:
    candidates = [
        event
        for event in events
        if _is_deploy(event) and event.observed_at <= failure_at
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda event: event.observed_at)


async def reconstruct_timeline(
    payload: TelemetryTimelineRequest,
) -> TelemetryTimelineResponse:
    rows = await recent_events(
        lookback_minutes=payload.lookback_minutes,
        service=payload.service,
        limit=payload.max_events,
    )
    events = [TelemetryTimelineEvent.model_validate(row) for row in rows]
    events.sort(key=lambda event: event.observed_at)

    now = datetime.now(timezone.utc)
    window_start = (
        events[0].observed_at
        if events
        else now
    )
    window_end = (
        events[-1].observed_at
        if events
        else now
    )

    failures = [event for event in events if _is_failure(event)]
    first_failure = failures[0] if failures else None
    first_failure_at = first_failure.observed_at if first_failure else None
    nearest_deploy = (
        nearest_preceding_deploy(events, first_failure_at)
        if first_failure_at
        else None
    )

    correlation = None
    if first_failure:
        context_events = [
            event
            for event in events
            if abs((event.observed_at - first_failure.observed_at).total_seconds()) <= 900
        ]
        logs = [
            f"[{event.observed_at.isoformat()}] {event.event_type}/{event.severity}: {event.message}"
            for event in context_events[:30]
        ]

        incident_text = (
            f"Production failure detected in {payload.service or first_failure.service or 'service'} "
            f"at {first_failure.observed_at.isoformat()}: {first_failure.message}"
        )
        deploy_sha = (
            nearest_deploy.deploy_sha
            if nearest_deploy
            else first_failure.deploy_sha
        )

        correlation = await correlate_incident(
            IncidentCorrelationRequest(
                repository_url=payload.repository_url,
                incident=incident_text,
                evidence=RuntimeEvidence(
                    error_message=first_failure.message,
                    logs=logs,
                    observed_at=first_failure.observed_at,
                    deploy_sha=deploy_sha,
                ),
                lookback_commits=payload.lookback_commits,
                code_limit=payload.code_limit,
            )
        )

    repository = (
        correlation.repository
        if correlation
        else str(payload.repository_url)
    )

    return TelemetryTimelineResponse(
        repository=repository,
        service=payload.service,
        window_start=window_start,
        window_end=window_end,
        first_failure_at=first_failure_at,
        nearest_deploy=nearest_deploy,
        events=events,
        correlation=correlation,
    )
