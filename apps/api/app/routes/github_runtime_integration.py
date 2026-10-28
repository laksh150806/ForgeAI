from fastapi import APIRouter

from app.schemas.github_runtime_adapter import (
    GitHubRuntimeStatus,
    GitHubRuntimeSyncRequest,
    GitHubRuntimeSyncResponse,
)
from app.services.github_runtime_adapter import adapter_status, sync_github_runtime


router = APIRouter(prefix="/api/v1/integrations/github-runtime", tags=["integrations"])


@router.get("/status", response_model=GitHubRuntimeStatus)
async def get_github_runtime_status() -> GitHubRuntimeStatus:
    return adapter_status()


@router.post("/sync", response_model=GitHubRuntimeSyncResponse)
async def sync_github_runtime_telemetry(
    payload: GitHubRuntimeSyncRequest,
) -> GitHubRuntimeSyncResponse:
    return await sync_github_runtime(payload)
