"""API v1 master router."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    assignments,
    brand_processes,
    brands,
    comp_offs,
    coverage_rules,
    employees,
    health,
    holidays,
    leaves,
    pods,
    preferences,
    processes,
    weekly_off_rules,
)

api_router = APIRouter()

# Health routes
api_router.include_router(health.router)

# Master data routes
api_router.include_router(pods.router)
api_router.include_router(employees.router)
api_router.include_router(processes.router)
api_router.include_router(brands.router)
api_router.include_router(brand_processes.router)
api_router.include_router(assignments.router)

# Rules & availability routes
api_router.include_router(coverage_rules.router)
api_router.include_router(holidays.router)
api_router.include_router(weekly_off_rules.router)
api_router.include_router(preferences.router)
api_router.include_router(leaves.router)
api_router.include_router(comp_offs.router)
