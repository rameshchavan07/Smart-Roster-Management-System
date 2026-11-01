"""Roster generation, metadata, and lifecycle endpoints.

Conforms to API_DOCUMENTATION.md §4 and SCHEDULING_ENGINE.md §§7–9.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_ops_manager
from app.models.auth import User
from app.schemas.roster import (
    RosterGenerateRequest,
    RosterGenerateResponse,
    RosterPeriodRead,
)
from app.services.roster import RosterService

router = APIRouter(prefix="/rosters", tags=["Rosters"])


@router.post(
    "",
    response_model=RosterGenerateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate monthly roster",
    description="Trigger CP-SAT solver with automated greedy fallback to generate and persist a new roster version.",
)
def generate_roster(
    data: RosterGenerateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_ops_manager)],
) -> RosterGenerateResponse:
    """Generate and persist a new draft roster for the target month."""
    service = RosterService(db)
    return service.generate_roster(data, actor_id=current_user.id)


@router.get(
    "",
    response_model=list[RosterPeriodRead],
    summary="List roster periods",
    description="Retrieve roster periods optionally filtered by target month (YYYY-MM).",
)
def list_rosters(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    month: str | None = Query(None, description="Target month in YYYY-MM format"),
) -> list[RosterPeriodRead]:
    """List generated roster versions."""
    service = RosterService(db)
    return service.list_roster_periods(month)


@router.get(
    "/{period_id}",
    response_model=RosterPeriodRead,
    summary="Get roster period metadata",
    description="Retrieve status, version, solver status, and summary counts for a roster period.",
)
def get_roster(
    period_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> RosterPeriodRead:
    """Fetch metadata for a single roster version."""
    service = RosterService(db)
    return service.get_roster_period(period_id)
