from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.telemetry import TelemetryTimelineResponse


class VercelSyncRequest(BaseModel):
    repository_url: HttpUrl | None = None
    project_id: str | None = Field(default=None, min_length=2, max_length=160)
    team_id: str | None = Field(default=None, min_length=2, max_length=160)
    lookback_minutes: int = Field(default=120, ge=5, le=1440)
    deploy_limit: int = Field(default=10, ge=1, le=50)
    event_limit_per_deploy: int = Field(default=100, ge=1, le=500)
    reconstruct_timeline: bool = True


class VercelAdapterStatus(BaseModel):
    configured: bool
    project_id: str | None
    team_id: str | None
    token_configured: bool
    runtime_logs_mode: str


class VercelSyncResponse(BaseModel):
    project_id: str
    team_id: str | None
    deployment_events: int
    build_events: int
    accepted_events: int
    storage: str
    runtime_logs_mode: str
    timeline: TelemetryTimelineResponse | None
