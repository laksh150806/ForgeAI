from pydantic import BaseModel, Field, HttpUrl


class PlanRequest(BaseModel):
    repository_url: HttpUrl
    task: str = Field(..., min_length=4, max_length=2000)
    generate_patch: bool = True


class PlanStep(BaseModel):
    order: int
    title: str
    description: str
    files: list[str]
    verification: str


class PatchFile(BaseModel):
    path: str
    rationale: str
    unified_diff: str


class EngineeringPlan(BaseModel):
    summary: str
    confidence: float
    target_files: list[str]
    steps: list[PlanStep]
    risks: list[str]
    validation_commands: list[str]


class PlanResponse(BaseModel):
    repository: str
    task: str
    plan: EngineeringPlan
    patch_status: str
    patches: list[PatchFile]
    approval_required: bool = True
