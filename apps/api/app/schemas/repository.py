from pydantic import BaseModel, Field, HttpUrl


class RepositoryAnalyzeRequest(BaseModel):
    repository_url: HttpUrl = Field(
        ...,
        description="GitHub repository URL, for example https://github.com/owner/repo",
    )


class LanguageStat(BaseModel):
    language: str
    files: int
    share: float


class RepositoryFile(BaseModel):
    path: str
    size: int | None = None
    language: str | None = None
    kind: str
    ignored: bool = False
    ignore_reason: str | None = None


class RepositorySummary(BaseModel):
    owner: str
    name: str
    full_name: str
    default_branch: str
    visibility: str
    description: str | None = None
    stars: int = 0
    forks: int = 0
    total_files: int
    source_files: int
    ignored_files: int
    languages: list[LanguageStat]
    important_files: list[str]


class RepositoryAnalysisResponse(BaseModel):
    repository: RepositorySummary
    files: list[RepositoryFile]
