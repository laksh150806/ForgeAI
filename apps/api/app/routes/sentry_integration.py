from fastapi import APIRouter

from app.schemas.sentry_adapter import (
    SentryAdapterStatus,
    SentrySyncRequest,
    SentrySyncResponse,
)
from app.services.sentry_adapter import adapter_status, sync_sentry


router = APIRouter(prefix="/api/v1/integrations/sentry", tags=["integrations"])


@router.get("/status", response_model=SentryAdapterStatus)
async def get_sentry_adapter_status() -> SentryAdapterStatus:
    return adapter_status()


@router.post("/sync", response_model=SentrySyncResponse)
async def sync_sentry_telemetry(payload: SentrySyncRequest) -> SentrySyncResponse:
    return await sync_sentry(payload)
