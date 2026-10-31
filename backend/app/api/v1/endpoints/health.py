"""Health and readiness check endpoints."""

from typing import Any

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Liveness probe")
def get_health() -> dict[str, Any]:
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "env": settings.APP_ENV,
    }


@router.get("/ready", summary="Readiness probe")
def get_ready() -> dict[str, str]:
    return {"status": "ready"}
