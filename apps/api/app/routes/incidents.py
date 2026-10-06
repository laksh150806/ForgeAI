from fastapi import APIRouter

from app.schemas.incident import IncidentCorrelationRequest, IncidentCorrelationResponse
from app.services.incident_correlation import correlate_incident


router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])


@router.post("/correlate", response_model=IncidentCorrelationResponse)
async def correlate(payload: IncidentCorrelationRequest) -> IncidentCorrelationResponse:
    return await correlate_incident(payload)
