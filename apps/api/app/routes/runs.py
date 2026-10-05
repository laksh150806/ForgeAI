from fastapi import APIRouter, Query

from app.schemas.observability import WorkflowRunRequest, WorkflowRunResponse
from app.schemas.runtime import RecentRun
from app.services.observability import execute_workflow
from app.services.trace_store import recent_runs, save_run


router = APIRouter(prefix="/api/v1/runs", tags=["observability"])


@router.post("/execute", response_model=WorkflowRunResponse)
async def execute_run(payload: WorkflowRunRequest) -> WorkflowRunResponse:
    run = await execute_workflow(
        repository_url=str(payload.repository_url),
        task=payload.task,
        generate_patch=payload.generate_patch,
        validate_patch=payload.validate_patch,
    )

    try:
        await save_run(run)
    except Exception:
        # Trace persistence must never corrupt an otherwise valid engineering run.
        pass

    return run


@router.get("/recent", response_model=list[RecentRun])
async def get_recent_runs(
    limit: int = Query(default=20, ge=1, le=100),
) -> list[RecentRun]:
    rows = await recent_runs(limit)
    return [RecentRun(**row) for row in rows]
