from fastapi import APIRouter

from app.schemas.vercel_adapter import VercelAdapterStatus, VercelSyncRequest, VercelSyncResponse
from app.services.vercel_adapter import adapter_status, sync_vercel


router = APIRouter(prefix="/api/v1/integrations/vercel", tags=["integrations"])


@router.get("/status", response_model=VercelAdapterStatus)
async def get_vercel_adapter_status() -> VercelAdapterStatus:
    return adapter_status()


@router.post("/sync", response_model=VercelSyncResponse)
async def sync_vercel_telemetry(payload: VercelSyncRequest) -> VercelSyncResponse:
    return await sync_vercel(payload)
