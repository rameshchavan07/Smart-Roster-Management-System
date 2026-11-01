"""Roster generation, metadata, and lifecycle endpoints.

Conforms to API_DOCUMENTATION.md §4 and SCHEDULING_ENGINE.md §§7–9.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_ops_manager
from app.models.auth import User
from app.models.roster import ConflictSeverity
from app.schemas.roster import (
    RosterConflictRead,
    RosterCoverageCell,
    RosterDayViewResponse,
    RosterGenerateRequest,
    RosterGenerateResponse,
    RosterGridViewResponse,
    RosterImpactRequest,
    RosterImpactResponse,
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
    month: Annotated[str | None, Query(description="Target month in YYYY-MM format")] = None,
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


@router.get(
    "/{period_id}/grid",
    response_model=RosterGridViewResponse,
    summary="Get roster grid matrix",
    description="Retrieve matrix view for company, pod, brand, process, or employee.",
)
def get_roster_grid(
    period_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    view: Annotated[
        str, Query(description="View mode: company, pod, brand, process, employee")
    ] = "company",
    ref_id: Annotated[
        uuid.UUID | None,
        Query(
            description="Optional entity UUID to filter by (pod_id, brand_id, process_id, employee_id)"
        ),
    ] = None,
) -> RosterGridViewResponse:
    """Fetch full interactive schedule matrix for the chosen view."""
    service = RosterService(db)
    return service.get_grid_view(period_id=period_id, view=view, ref_id=ref_id)


@router.get(
    "/{period_id}/coverage",
    response_model=list[RosterCoverageCell],
    summary="Get coverage demand vs actuals",
    description="Retrieve required vs actual headcount per brand-process per date.",
)
def get_roster_coverage(
    period_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    brand_process_id: Annotated[
        uuid.UUID | None, Query(description="Optional brand-process filter")
    ] = None,
    date_from: Annotated[dt.date | None, Query(description="Optional start date")] = None,
    date_to: Annotated[dt.date | None, Query(description="Optional end date")] = None,
) -> list[RosterCoverageCell]:
    """Fetch coverage cells with required headcount, actual scheduled staff, and shortfall."""
    service = RosterService(db)
    return service.get_coverage(
        period_id=period_id,
        brand_process_id=brand_process_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.get(
    "/{period_id}/day",
    response_model=RosterDayViewResponse,
    summary="Get single-day operational view",
    description="Retrieve list of employees working on a specific date grouped by brand-process with coverage state.",
)
def get_roster_day_view(
    period_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    date: Annotated[dt.date, Query(description="Target date to inspect")],
) -> RosterDayViewResponse:
    """Fetch day view showing working vs off employees per brand-process."""
    service = RosterService(db)
    return service.get_day_view(period_id=period_id, target_date=date)


@router.get(
    "/{period_id}/conflicts",
    response_model=list[RosterConflictRead],
    summary="List roster validation conflicts",
    description="Retrieve conflicts with entity names, root causes, and suggestions.",
)
def get_roster_conflicts(
    period_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    severity: Annotated[
        ConflictSeverity | None, Query(description="Filter by BLOCKING, WARNING, INFO")
    ] = None,
    brand_id: Annotated[uuid.UUID | None, Query(description="Filter by brand ID")] = None,
    date: Annotated[
        dt.date | None, Query(description="Filter by date overlapping conflict range")
    ] = None,
    employee_id: Annotated[uuid.UUID | None, Query(description="Filter by employee ID")] = None,
) -> list[RosterConflictRead]:
    """Fetch validation conflicts for the roster period."""
    service = RosterService(db)
    return service.get_conflicts(
        period_id=period_id,
        severity=severity.value if severity else None,
        brand_id=brand_id,
        target_date=date,
        employee_id=employee_id,
    )


@router.post(
    "/{period_id}/impact",
    response_model=RosterImpactResponse,
    summary="Simulate proposed roster changes",
    description="Dry-run cell edits or leave additions without persisting to DB, returning diff of new, resolved, and unchanged conflicts.",
)
def simulate_roster_impact(
    period_id: uuid.UUID,
    data: RosterImpactRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> RosterImpactResponse:
    """Evaluate what-if impact for proposed schedule changes."""
    service = RosterService(db)
    return service.simulate_impact(period_id=period_id, request=data)
