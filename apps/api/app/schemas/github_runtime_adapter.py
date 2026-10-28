from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.telemetry import TelemetryTimelineResponse


class GitHubRuntimeSyncRequest(BaseModel):
    repository_url: HttpUrl
    service: str | None = Field(default=None, min_length=1, max_length=160)
    lookback_minutes: int = Field(default=1440, ge=5, le=10080)
    deployment_limit: int = Field(default=10, ge=1, le=20)
    workflow_limit: int = Field(default=15, ge=1, le=30)
    failed_job_limit: int = Field(default=3, ge=0, le=5)
    reconstruct_timeline: bool = True


class GitHubRuntimeStatus(BaseModel):
    token_configured: bool
    public_repository_reads: bool
    ingestion_mode: str


class GitHubRuntimeSyncResponse(BaseModel):
    repository: str
    branch: str
    service: str
    deployment_events: int
    workflow_events: int
    ci_failure_events: int
    failed_jobs_summarized: int
    accepted_events: int
    storage: str
    timeline: TelemetryTimelineResponse | None
