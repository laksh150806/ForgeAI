from pydantic import BaseModel, Field, HttpUrl


class CodeSearchRequest(BaseModel):
    repository_url: HttpUrl
    task: str = Field(..., min_length=4, max_length=2000)
    limit: int = Field(default=8, ge=1, le=25)


class CodeSymbol(BaseModel):
    name: str
    kind: str
    line_start: int
    line_end: int | None = None


class CodeEvidence(BaseModel):
    path: str
    language: str | None = None
    score: float
    reasons: list[str]
    symbols: list[CodeSymbol]
    snippet: str


class CodeSearchResponse(BaseModel):
    repository: str
    task: str
    retrieval_mode: str
    indexed_files: int
    indexed_chunks: int
    results: list[CodeEvidence]
