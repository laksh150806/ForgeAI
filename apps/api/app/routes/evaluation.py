from fastapi import APIRouter

from app.schemas.evaluation import BenchmarkRequest, BenchmarkResponse
from app.services.evaluation import run_benchmark


router = APIRouter(prefix="/api/v1/evaluation", tags=["evaluation"])


@router.post("/benchmark", response_model=BenchmarkResponse)
async def benchmark(payload: BenchmarkRequest) -> BenchmarkResponse:
    return await run_benchmark(
        cases=payload.cases,
        top_k=payload.top_k,
        run_full_pipeline=payload.run_full_pipeline,
    )
