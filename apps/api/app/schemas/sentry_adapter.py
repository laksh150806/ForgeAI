from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.telemetry import TelemetryTimelineResponse


class SentrySyncRequest(BaseModel):
    repository_url: HttpUrl | None = None
    organization: str | None = Field(default=None, min_length=1, max_length=160)
    project: str | None = Field(default=None, min_length=1, max_length=160)
    environment: str | None = Field(default=None, min_length=1, max_length=160)
    lookback_minutes: int = Field(default=120, ge=5, le=10080)
    event_limit: int = Field(default=20, ge=1, le=50)
    reconstruct_timeline: bool = True


class SentryAdapterStatus(BaseModel):
    configured: bool
    organization: str | None
    project: str | None
    environment: str | None
    token_configured: bool
    ingestion_mode: str


class SentrySyncResponse(BaseModel):
    organization: str
    project: str
    environment: str | None
    error_events: int
    accepted_events: int
    storage: str
    ingestion_mode: str
    timeline: TelemetryTimelineResponse | None
