from fastapi import APIRouter

from app.schemas.repository import RepositoryAnalyzeRequest, RepositoryAnalysisResponse
from app.services.repository_intelligence import analyze_repository


router = APIRouter(prefix="/api/v1/repositories", tags=["repositories"])


@router.post("/analyze", response_model=RepositoryAnalysisResponse)
async def analyze(payload: RepositoryAnalyzeRequest) -> RepositoryAnalysisResponse:
    return await analyze_repository(str(payload.repository_url))
