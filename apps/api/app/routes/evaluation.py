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


IMPACT_SEED_CASES = [
    BenchmarkCase(
        id="impact-analysis-route-regression",
        repository_url="https://github.com/laksh150806/ForgeAI",
        task="Localize the blast-radius implementation and its API entrypoint after the dependency graph change.",
        expected_files=["apps/api/app/services/impact_analysis.py"],
        expected_symbols=["analyze_impact"],
        impact_commit_sha="3dd89c8b4ebebf24a70aef672f8c13846853eab8",
        impact_runtime_text=(
            "Production traceback points to apps/api/app/services/impact_analysis.py "
            "inside analyze_impact while calculating the blast radius."
        ),
        impact_lookback_commits=80,
        expected_changed_symbols=["analyze_impact"],
        expected_runtime_symbols=["analyze_impact"],
        expected_affected_entrypoints=["analyze"],
    ),
    BenchmarkCase(
        id="incident-correlation-graph-regression",
        repository_url="https://github.com/laksh150806/ForgeAI",
        task="Localize incident correlation after graph evidence was added to regression scoring.",
        expected_files=["apps/api/app/services/incident_correlation.py"],
        expected_symbols=["correlate_incident"],
        impact_commit_sha="3dd89c8b4ebebf24a70aef672f8c13846853eab8",
        impact_runtime_text=(
            "Runtime failure in apps/api/app/services/incident_correlation.py "
            "inside correlate_incident after a production deploy."
        ),
        impact_lookback_commits=80,
        expected_changed_symbols=["correlate_incident"],
        expected_runtime_symbols=["correlate_incident"],
        expected_affected_entrypoints=["correlate"],
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


@router.get("/impact-seed", response_model=BenchmarkResponse)
async def impact_seed_benchmark() -> BenchmarkResponse:
    return await run_benchmark(
        cases=IMPACT_SEED_CASES,
        top_k=3,
        run_full_pipeline=False,
    )
