from fastapi import APIRouter

from app.schemas.code_intelligence import CodeSearchRequest, CodeSearchResponse
from app.services.code_intelligence import search_repository_code


router = APIRouter(prefix="/api/v1/code", tags=["code-intelligence"])


@router.post("/search", response_model=CodeSearchResponse)
async def search_code(payload: CodeSearchRequest) -> CodeSearchResponse:
    return await search_repository_code(
        repository_url=str(payload.repository_url),
        task=payload.task,
        limit=payload.limit,
    )
