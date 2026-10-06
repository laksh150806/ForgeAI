from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.schemas.incident import IncidentCorrelationResponse


class TelemetryEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = Field(..., min_length=1, max_length=80)
    event_type: str = Field(..., min_length=2, max_length=80)
    severity: str = Field(default="info", min_length=2, max_length=20)
    service: str | None = Field(default=None, max_length=160)
    message: str = Field(..., min_length=1, max_length=8000)
    deploy_sha: str | None = Field(default=None, max_length=64)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("observed_at")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class TelemetryIngestRequest(BaseModel):
    events: list[TelemetryEvent] = Field(..., min_length=1, max_length=100)


class TelemetryIngestResponse(BaseModel):
    accepted: int
    storage: str
    event_ids: list[UUID]


class TelemetryTimelineRequest(BaseModel):
    repository_url: HttpUrl
    service: str | None = Field(default=None, max_length=160)
    lookback_minutes: int = Field(default=120, ge=5, le=10080)
    max_events: int = Field(default=100, ge=1, le=500)
    lookback_commits: int = Field(default=20, ge=2, le=40)
    code_limit: int = Field(default=6, ge=1, le=12)


class TelemetryTimelineEvent(BaseModel):
    event_id: UUID
    observed_at: datetime
    source: str
    event_type: str
    severity: str
    service: str | None
    message: str
    deploy_sha: str | None
    metadata: dict[str, Any]


class TelemetryTimelineResponse(BaseModel):
    repository: str
    service: str | None
    window_start: datetime
    window_end: datetime
    first_failure_at: datetime | None
    nearest_deploy: TelemetryTimelineEvent | None
    events: list[TelemetryTimelineEvent]
    correlation: IncidentCorrelationResponse | None
