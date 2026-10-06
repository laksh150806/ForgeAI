from __future__ import annotations

import os
from dataclasses import dataclass

from app.schemas.telemetry import TelemetryEvent, TelemetryTimelineRequest, TelemetryTimelineResponse
from app.services.telemetry_store import save_events
from app.services.telemetry_timeline import reconstruct_timeline


@dataclass(frozen=True)
class RuntimeProviderSyncResult:
    accepted_events: int
    storage: str
    timeline: TelemetryTimelineResponse | None


async def persist_provider_events(
    *,
    events: list[TelemetryEvent],
    repository_url: str | None,
    service: str,
    lookback_minutes: int,
    max_events: int,
    reconstruct: bool,
) -> RuntimeProviderSyncResult:
    unique = {str(event.event_id): event for event in events}
    ordered = sorted(unique.values(), key=lambda event: event.observed_at)

    storage = (
        await save_events(ordered)
        if ordered
        else ("postgres" if os.getenv("DATABASE_URL") else "memory")
    )

    timeline = None
    if reconstruct and repository_url:
        timeline = await reconstruct_timeline(
            TelemetryTimelineRequest(
                repository_url=repository_url,
                service=service,
                lookback_minutes=lookback_minutes,
                max_events=min(500, max(max_events, 20)),
                lookback_commits=20,
                code_limit=6,
            )
        )

    return RuntimeProviderSyncResult(
        accepted_events=len(ordered),
        storage=storage,
        timeline=timeline,
    )
