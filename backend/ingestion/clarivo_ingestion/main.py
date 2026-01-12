from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from clarivo_ingestion.api.routes import documents, health, scope
from clarivo_ingestion.core.config import get_settings
from clarivo_ingestion.core.logging import configure_logging, get_logger

settings = get_settings()
configure_logging()
logger = get_logger(__name__)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust per environment security policy
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(documents.router)
app.include_router(scope.router)


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Starting %s in %s mode", settings.app_name, settings.environment)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    logger.info("Shutting down %s", settings.app_name)

