from fastapi import APIRouter

from app.schemas.evaluation import BenchmarkCase, BenchmarkRequest, BenchmarkResponse
from app.services.evaluation import run_benchmark


router = APIRouter(prefix="/api/v1/evaluation", tags=["evaluation"])


SEED_CASES = [
    BenchmarkCase(
        id="github-url-validation",
        repository_url="https://github.com/laksh150806/ForgeAI",
        task="Find the implementation responsible for validating GitHub repository URLs.",
        expected_files=["apps/api/app/services/github_client.py"],
        expected_symbols=["parse_github_repository_url"],
    ),
    BenchmarkCase(
        id="sandbox-patch-validation",
        repository_url="https://github.com/laksh150806/ForgeAI",
        task="Find the code that applies proposed patches and runs isolated validation.",
        expected_files=["apps/api/app/services/sandbox_validation.py"],
        expected_symbols=["validate_patches"],
    ),
    BenchmarkCase(
        id="pr-approval-gate",
        repository_url="https://github.com/laksh150806/ForgeAI",
        task="Find the code that requires approval and fresh validation before opening a GitHub pull request.",
        expected_files=["apps/api/app/services/github_pr.py"],
        expected_symbols=["create_validated_pull_request"],
    ),
]


@router.post("/benchmark", response_model=BenchmarkResponse)
async def benchmark(payload: BenchmarkRequest) -> BenchmarkResponse:
    return await run_benchmark(
        cases=payload.cases,
        top_k=payload.top_k,
        run_full_pipeline=payload.run_full_pipeline,
    )


@router.get("/seed", response_model=BenchmarkResponse)
async def seed_benchmark() -> BenchmarkResponse:
    return await run_benchmark(
        cases=SEED_CASES,
        top_k=3,
        run_full_pipeline=False,
    )
