from fastapi import APIRouter

from app.schemas.observability import WorkflowRunRequest, WorkflowRunResponse
from app.services.observability import execute_workflow


router = APIRouter(prefix="/api/v1/runs", tags=["observability"])


@router.post("/execute", response_model=WorkflowRunResponse)
async def execute_run(payload: WorkflowRunRequest) -> WorkflowRunResponse:
    return await execute_workflow(
        repository_url=str(payload.repository_url),
        task=payload.task,
        generate_patch=payload.generate_patch,
        validate_patch=payload.validate_patch,
    )
