"""API v1 master router."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    assignments,
    brand_processes,
    brands,
    employees,
    health,
    pods,
    processes,
)

api_router = APIRouter()

# Master data & health routes
api_router.include_router(health.router)
api_router.include_router(pods.router)
api_router.include_router(employees.router)
api_router.include_router(processes.router)
api_router.include_router(brands.router)
api_router.include_router(brand_processes.router)
api_router.include_router(assignments.router)
