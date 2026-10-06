from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.telemetry import TelemetryTimelineResponse


class RenderSyncRequest(BaseModel):
    repository_url: HttpUrl | None = None
    service_id: str | None = Field(default=None, min_length=3, max_length=128)
    workspace_id: str | None = Field(default=None, min_length=3, max_length=128)
    lookback_minutes: int = Field(default=60, ge=5, le=1440)
    log_limit: int = Field(default=100, ge=1, le=100)
    deploy_limit: int = Field(default=20, ge=1, le=100)
    reconstruct_timeline: bool = True


class RenderAdapterStatus(BaseModel):
    configured: bool
    service_id: str | None
    workspace_id: str | None
    api_key_configured: bool


class RenderSyncResponse(BaseModel):
    service_id: str
    workspace_id: str
    deploy_events: int
    log_events: int
    accepted_events: int
    storage: str
    timeline: TelemetryTimelineResponse | None
