from fastapi import APIRouter

from app.schemas.telemetry import (
    TelemetryIngestRequest,
    TelemetryIngestResponse,
    TelemetryTimelineRequest,
    TelemetryTimelineResponse,
)
from app.services.telemetry_store import save_events
from app.services.telemetry_timeline import reconstruct_timeline


router = APIRouter(prefix="/api/v1/telemetry", tags=["telemetry"])


@router.post("/events", response_model=TelemetryIngestResponse)
async def ingest_events(payload: TelemetryIngestRequest) -> TelemetryIngestResponse:
    storage = await save_events(payload.events)
    return TelemetryIngestResponse(
        accepted=len(payload.events),
        storage=storage,
        event_ids=[event.event_id for event in payload.events],
    )


@router.post("/timeline", response_model=TelemetryTimelineResponse)
async def build_timeline(payload: TelemetryTimelineRequest) -> TelemetryTimelineResponse:
    return await reconstruct_timeline(payload)
