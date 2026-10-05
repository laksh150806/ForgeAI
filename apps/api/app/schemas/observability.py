from pydantic import BaseModel, Field, HttpUrl

from app.schemas.planning import PlanResponse
from app.schemas.validation import ValidationResponse


class WorkflowRunRequest(BaseModel):
    repository_url: HttpUrl
    task: str = Field(..., min_length=4, max_length=2000)
    generate_patch: bool = True
    validate_patch: bool = True


class TraceStage(BaseModel):
    name: str
    status: str
    duration_ms: int
    details: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    error: str | None = None


class RunMetrics(BaseModel):
    total_duration_ms: int
    stages_completed: int
    stages_failed: int
    retrieval_mode: str | None = None
    evidence_count: int = 0
    patch_count: int = 0
    validation_commands: int = 0
    pr_gate_open: bool = False


class WorkflowRunResponse(BaseModel):
    run_id: str
    repository: str
    task: str
    status: str
    stages: list[TraceStage]
    metrics: RunMetrics
    plan: PlanResponse | None = None
    validation: ValidationResponse | None = None
