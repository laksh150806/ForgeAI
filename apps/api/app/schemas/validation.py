from pydantic import BaseModel, Field, HttpUrl

from app.schemas.planning import PatchFile


class ValidationRequest(BaseModel):
    repository_url: HttpUrl
    patches: list[PatchFile] = Field(..., min_length=1, max_length=8)


class ValidationCommandResult(BaseModel):
    command: str
    status: str
    exit_code: int | None = None
    duration_ms: int
    stdout: str = ""
    stderr: str = ""


class PatchApplicationResult(BaseModel):
    status: str
    files: list[str]
    message: str


class ValidationResponse(BaseModel):
    repository: str
    sandbox: str
    status: str
    patch: PatchApplicationResult
    commands: list[ValidationCommandResult]
    passed: bool
    safe_to_propose_pr: bool
    notes: list[str]
