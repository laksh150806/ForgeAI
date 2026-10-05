from fastapi import APIRouter

from app.schemas.planning import PlanRequest, PlanResponse
from app.services.planning_agent import create_engineering_plan


router = APIRouter(prefix="/api/v1/plans", tags=["planning"])


@router.post("/generate", response_model=PlanResponse)
async def generate_plan(payload: PlanRequest) -> PlanResponse:
    return await create_engineering_plan(
        repository_url=str(payload.repository_url),
        task=payload.task,
        generate_patch=payload.generate_patch,
    )
