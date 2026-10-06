from fastapi import APIRouter

from app.schemas.impact import ImpactAnalysisRequest, ImpactAnalysisResponse
from app.services.impact_analysis import analyze_impact


router = APIRouter(prefix="/api/v1/impact", tags=["impact"])


@router.post("/analyze", response_model=ImpactAnalysisResponse)
async def analyze(payload: ImpactAnalysisRequest) -> ImpactAnalysisResponse:
    return await analyze_impact(payload)
