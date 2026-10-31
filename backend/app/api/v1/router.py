"""API v1 master router."""

from fastapi import APIRouter

from app.api.v1.endpoints import health

api_router = APIRouter()

# Mount health endpoints under /health & /ready as well as /api/v1/health & /ready
api_router.include_router(health.router)
