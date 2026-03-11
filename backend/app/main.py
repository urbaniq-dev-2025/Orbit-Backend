from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

settings = get_settings()
configure_logging()
logger = get_logger(__name__)

app = FastAPI(title=settings.app_name, version="0.1.0")

# CORS Configuration
# Always allow localhost origins in development
if settings.environment == "development":
    default_origins = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001"]
    if settings.cors_origins:
        # Merge with existing origins
        cors_origins = list(settings.cors_origins)
        for origin in default_origins:
            if origin not in cors_origins:
                cors_origins.append(origin)
    else:
        cors_origins = default_origins
else:
    cors_origins = list(settings.cors_origins) if settings.cors_origins else ["*"]

# Convert AnyHttpUrl objects to strings
cors_origins = [str(origin) for origin in cors_origins]

logger.info(f"CORS origins configured: {cors_origins}")
logger.info(f"Environment: {settings.environment}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled exceptions and return proper error responses."""
    logger.exception(
        "Unhandled exception",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error": str(exc),
            "error_type": type(exc).__name__,
        },
    )
    content = {
        "detail": "An internal server error occurred. Please try again later.",
        "error_type": type(exc).__name__,
    }
    if settings.environment == "development":
        content["error_message"] = str(exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=content,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle validation errors with detailed messages."""
    logger.warning(
        "Validation error",
        extra={"path": request.url.path, "method": request.method, "errors": exc.errors()},
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


app.include_router(api_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


