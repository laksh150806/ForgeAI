from fastapi import APIRouter

from app.schemas.validation import ValidationRequest, ValidationResponse
from app.services.sandbox_validation import validate_patches


router = APIRouter(prefix="/api/v1/validation", tags=["validation"])


@router.post("/run", response_model=ValidationResponse)
async def run_validation(payload: ValidationRequest) -> ValidationResponse:
    return await validate_patches(
        repository_url=str(payload.repository_url),
        patches=payload.patches,
    )
