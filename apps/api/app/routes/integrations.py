from fastapi import APIRouter

from app.schemas.render_adapter import RenderAdapterStatus, RenderSyncRequest, RenderSyncResponse
from app.services.render_adapter import adapter_status, sync_render


router = APIRouter(prefix="/api/v1/integrations/render", tags=["integrations"])


@router.get("/status", response_model=RenderAdapterStatus)
async def get_render_adapter_status() -> RenderAdapterStatus:
    return adapter_status()


@router.post("/sync", response_model=RenderSyncResponse)
async def sync_render_telemetry(payload: RenderSyncRequest) -> RenderSyncResponse:
    return await sync_render(payload)
