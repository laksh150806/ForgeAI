from fastapi import APIRouter

from app.schemas.investigation import InvestigationRequest, InvestigationResponse
from app.services.investigation_agent import investigate_repository


router = APIRouter(prefix="/api/v1/investigations", tags=["investigations"])


@router.post("/run", response_model=InvestigationResponse)
async def run_investigation(payload: InvestigationRequest) -> InvestigationResponse:
    return await investigate_repository(
        repository_url=str(payload.repository_url),
        task=payload.task,
        limit=payload.limit,
    )
