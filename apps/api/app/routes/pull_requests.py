from fastapi import APIRouter

from app.schemas.pull_requests import (
    PullRequestCreateRequest,
    PullRequestCreateResponse,
)
from app.services.github_pr import create_validated_pull_request


router = APIRouter(prefix="/api/v1/pull-requests", tags=["pull-requests"])


@router.post("/create", response_model=PullRequestCreateResponse)
async def create_pull_request(payload: PullRequestCreateRequest) -> PullRequestCreateResponse:
    return await create_validated_pull_request(
        repository_url=str(payload.repository_url),
        task=payload.task,
        patches=payload.patches,
        approved=payload.approved,
    )
