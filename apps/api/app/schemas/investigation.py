from pydantic import BaseModel, Field, HttpUrl

from app.schemas.code_intelligence import CodeEvidence


class InvestigationRequest(BaseModel):
    repository_url: HttpUrl
    task: str = Field(..., min_length=4, max_length=2000)
    limit: int = Field(default=6, ge=1, le=12)


class InvestigationHypothesis(BaseModel):
    summary: str
    confidence: float
    rationale: list[str]


class InvestigationResponse(BaseModel):
    repository: str
    task: str
    retrieval_mode: str
    hypothesis: InvestigationHypothesis
    evidence: list[CodeEvidence]
    suggested_next_actions: list[str]
