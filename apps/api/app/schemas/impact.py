from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class ImpactNode(BaseModel):
    id: str
    path: str
    symbol: str
    kind: str
    line_start: int
    line_end: int | None = None
    entrypoint: bool = False


class ImpactEdge(BaseModel):
    source: str
    target: str
    relation: str


class ImpactAnalysisRequest(BaseModel):
    repository_url: HttpUrl
    commit_sha: str | None = Field(default=None, min_length=4, max_length=64)
    runtime_text: str = Field(default="", max_length=16000)
    stack_trace: str | None = Field(default=None, max_length=16000)
    lookback_commits: int = Field(default=20, ge=2, le=40)
    max_depth: int = Field(default=3, ge=1, le=5)


class ImpactAnalysisResponse(BaseModel):
    repository: str
    commit_sha: str
    graph_mode: str
    graph_nodes: int
    graph_edges: int
    changed_symbols: list[ImpactNode]
    runtime_matches: list[ImpactNode]
    callers: list[ImpactNode]
    downstream: list[ImpactNode]
    affected_entrypoints: list[ImpactNode]
    evidence_paths: list[list[str]]
    blast_radius_score: float
    confidence: float
    explanation: list[str]
