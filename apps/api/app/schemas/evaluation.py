from pydantic import BaseModel, Field, HttpUrl


class BenchmarkCase(BaseModel):
    id: str = Field(..., min_length=1, max_length=80)
    repository_url: HttpUrl
    task: str = Field(..., min_length=4, max_length=2000)
    expected_files: list[str] = Field(..., min_length=1)
    expected_symbols: list[str] = []
    expected_gate_open: bool | None = None


class BenchmarkRequest(BaseModel):
    cases: list[BenchmarkCase] = Field(..., min_length=1, max_length=50)
    top_k: int = Field(default=3, ge=1, le=10)
    run_full_pipeline: bool = False


class BenchmarkCaseResult(BaseModel):
    id: str
    repository: str
    retrieval_mode: str
    latency_ms: int
    ranked_files: list[str]
    top1_hit: bool
    topk_recall: float
    reciprocal_rank: float
    symbol_hit: bool | None = None
    patch_generated: bool | None = None
    validation_passed: bool | None = None
    pr_gate_open: bool | None = None
    gate_correct: bool | None = None


class BenchmarkMetrics(BaseModel):
    cases: int
    top1_accuracy: float
    topk_recall: float
    mean_reciprocal_rank: float
    symbol_accuracy: float | None = None
    average_latency_ms: float
    patch_generation_rate: float | None = None
    validation_pass_rate: float | None = None
    pr_gate_accuracy: float | None = None


class BenchmarkResponse(BaseModel):
    metrics: BenchmarkMetrics
    results: list[BenchmarkCaseResult]
