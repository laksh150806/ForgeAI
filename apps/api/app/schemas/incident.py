from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.investigation import InvestigationResponse


class RuntimeEvidence(BaseModel):
    error_message: str | None = Field(default=None, max_length=4000)
    stack_trace: str | None = Field(default=None, max_length=12000)
    logs: list[str] = Field(default_factory=list, max_length=30)
    observed_at: datetime | None = None
    deploy_sha: str | None = Field(default=None, min_length=4, max_length=64)


class IncidentCorrelationRequest(BaseModel):
    repository_url: HttpUrl
    incident: str = Field(..., min_length=6, max_length=4000)
    evidence: RuntimeEvidence = Field(default_factory=RuntimeEvidence)
    lookback_commits: int = Field(default=10, ge=2, le=30)
    code_limit: int = Field(default=6, ge=1, le=12)


class SuspectCommit(BaseModel):
    sha: str
    short_sha: str
    subject: str
    authored_at: datetime
    changed_files: list[str]
    score: float
    confidence: float
    matching_terms: list[str]
    reasons: list[str]


class IncidentCorrelationResponse(BaseModel):
    repository: str
    incident: str
    head_sha: str
    correlation_mode: str
    suspected_commit: SuspectCommit | None
    candidates: list[SuspectCommit]
    investigation: InvestigationResponse
