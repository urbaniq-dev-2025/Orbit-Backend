from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from clarivo_ingestion.schemas.scope import ScopeDocument, ScopePreviewRequest
from clarivo_ingestion.services.scope import ScopeParser

router = APIRouter(prefix="/v1/scope", tags=["scope"])
parser = ScopeParser()


@router.post(
    "/preview",
    response_model=ScopeDocument,
    status_code=status.HTTP_200_OK,
    summary="Generate scope document preview from raw text",
)
async def generate_scope_preview(request: ScopePreviewRequest) -> ScopeDocument:
    if not request.content.strip():
        raise HTTPException(status_code=422, detail="Content cannot be empty.")
    return parser.parse(request.content)

