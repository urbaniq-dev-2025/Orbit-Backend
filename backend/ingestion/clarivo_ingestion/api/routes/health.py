from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/healthz", summary="Health check")
async def healthcheck() -> dict[str, str]:
    """Return basic service health information."""
    return {"status": "ok"}

