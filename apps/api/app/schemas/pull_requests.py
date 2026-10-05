from pydantic import BaseModel, Field, HttpUrl

from app.schemas.planning import PatchFile
from app.schemas.validation import ValidationResponse


class PullRequestCreateRequest(BaseModel):
    repository_url: HttpUrl
    task: str = Field(..., min_length=4, max_length=2000)
    patches: list[PatchFile] = Field(..., min_length=1, max_length=8)
    approved: bool = False


class PullRequestCreateResponse(BaseModel):
    repository: str
    branch: str | None = None
    pull_request_url: str | None = None
    pull_request_number: int | None = None
    status: str
    validation: ValidationResponse
    committed_files: list[str] = []
    message: str
