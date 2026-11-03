"""Roster generation, metadata, and lifecycle endpoints.

Conforms to API_DOCUMENTATION.md §4 and SCHEDULING_ENGINE.md §§7–9.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    get_db,
    require_ops_manager,
    require_pod_lead_or_manager,
)
from app.core.rate_limit import solver_rate_limiter
from app.models.auth import User
from app.models.roster import ConflictSeverity
from app.schemas.roster import (
    RosterAcknowledgeRequest,
    RosterCloneRequest,
    RosterCompareResponse,
    RosterConflictRead,
    RosterCoverageCell,
    RosterDayViewResponse,
    RosterEntriesBatchUpdateRequest,
    RosterEntriesLockRequest,
    RosterEntriesLockResponse,
    RosterEntriesUpdateResponse,
    RosterGenerateRequest,
    RosterGenerateResponse,
    RosterGridViewResponse,
    RosterImpactRequest,
    RosterImpactResponse,
    RosterPeriodRead,
    RosterRepairRequest,
    RosterRepairResponse,
    RosterSuggestionItem,
)
from app.schemas.rules import CompOffLedgerRead
from app.services.compoff import CompOffService
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
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_ops_manager)],
) -> RosterGenerateResponse:
    """Generate and persist a new draft roster for the target month."""
    client_ip = request.client.host if request.client else "unknown"
    solver_rate_limiter.check(f"solver:{client_ip}")

    service = RosterService(db)
    result = service.generate_roster(data, actor_id=current_user.id)
    db.commit()
    return result


@router.get(
    "",
    response_model=list[RosterPeriodRead],
    summary="List roster periods",
    description="List all generated and published roster periods, optionally filtered by month.",
)
def list_roster_periods(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    month: Annotated[
        str | None,
        Query(description="Filter by month in 'YYYY-MM' or 'YYYY-MM-DD' format"),
    ] = None,
) -> list[RosterPeriodRead]:
    """List historical and draft roster periods."""
    service = RosterService(db)
    return service.list_roster_periods(month=month)


@router.get(
    "/compare",
    response_model=RosterCompareResponse,
    summary="Compare two roster versions side-by-side",
    description="Compare two roster periods (Version A vs Version B): conflict counts and diffs, coverage %, weekend-off fairness spread, and granular cell modifications.",
)
def compare_rosters(
    a: Annotated[uuid.UUID, Query(description="UUID of baseline roster version (A)")],
    b: Annotated[uuid.UUID, Query(description="UUID of comparison roster version (B)")],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> RosterCompareResponse:
    """Compare two roster versions side-by-side."""
    service = RosterService(db)
    return service.compare_rosters(period_id_a=a, period_id_b=b)


@router.get(
    "/{period_id}",
    response_model=RosterPeriodRead,
    summary="Get roster period metadata",
    description="Retrieve metadata, summary counts, and solver status for a single roster version.",
)
def get_roster_period(
    period_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> RosterPeriodRead:
    """Get metadata for a specific roster period."""
    service = RosterService(db)
    return service.get_roster_period(period_id)


@router.get(
    "/{period_id}/grid",
    response_model=RosterGridViewResponse,
    summary="Get roster grid view",
    description="Retrieve complete monthly employee grid view with cells, notes, locks, and conflicts.",
)
def get_roster_grid(
    period_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    view: Annotated[
        str, Query(description="View mode: company, pod, brand, process, employee")
    ] = "company",
    ref_id: Annotated[
        str | None,
        Query(
            description="Optional entity UUID or code to filter by (pod_id, brand_id, process_id, employee_id)"
        ),
    ] = None,
) -> RosterGridViewResponse:
    """Fetch full interactive schedule matrix for the chosen view."""
    target_uuid: uuid.UUID | None = None
    if ref_id:
        try:
            target_uuid = uuid.UUID(ref_id)
        except (ValueError, TypeError):
            # Support fallback lookups by code (e.g. 'EMP-007' or 'emp-007')
            if view.lower().strip() == "employee":
                from app.models.employee import Employee as DbEmployee

                normalized = ref_id.upper().strip()
                emp = (
                    db.query(DbEmployee)
                    .filter((DbEmployee.code == normalized) | (DbEmployee.code == ref_id))
                    .first()
                )
                if emp:
                    target_uuid = emp.id

    service = RosterService(db)
    return service.get_grid_view(period_id=period_id, view=view, ref_id=target_uuid)


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
    date: Annotated[
        dt.date | None,
        Query(description="Specific date to inspect (defaults to month start)"),
    ] = None,
) -> RosterDayViewResponse:
    """Fetch single-day staffing operational view."""
    service = RosterService(db)
    target_date = date or service.get_roster_period(period_id).month
    return service.get_day_view(period_id=period_id, target_date=target_date)


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


@router.put(
    "/{period_id}/entries",
    response_model=RosterEntriesUpdateResponse,
    summary="Batch edit roster cells",
    description="Update cell statuses and notes manually. Validates against leaves and re-evaluates conflicts with full audit trail. Ops Manager only.",
)
def update_roster_entries(
    period_id: uuid.UUID,
    request: RosterEntriesBatchUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_ops_manager)],
) -> RosterEntriesUpdateResponse:
    """Apply manual edits to cells in a draft roster, re-evaluating conflicts."""
    service = RosterService(db)
    result = service.update_entries(period_id, request, user_id=current_user.id)
    db.commit()
    return result


@router.post(
    "/{period_id}/entries/lock",
    response_model=RosterEntriesLockResponse,
    summary="Lock or unlock roster cells",
    description="Lock cells to freeze them for subsequent solver re-runs, or unlock them. Ops Manager only.",
)
def lock_roster_cells(
    period_id: uuid.UUID,
    request: RosterEntriesLockRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_ops_manager)],
) -> RosterEntriesLockResponse:
    """Lock or unlock cells with audit logging."""
    service = RosterService(db)
    result = service.lock_cells(period_id, request, user_id=current_user.id)
    db.commit()
    return result


@router.get(
    "/{period_id}/suggestions",
    response_model=list[RosterSuggestionItem],
    summary="Ranked conflict suggestions",
    description="Retrieve ranked, actionable recommendations for resolving gaps with second-order net impact simulated.",
)
def get_roster_suggestions(
    period_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_pod_lead_or_manager)],
    conflict_id: Annotated[
        uuid.UUID | None, Query(description="Filter suggestions by conflict UUID")
    ] = None,
    brand_process_id: Annotated[
        uuid.UUID | None, Query(description="Filter by brand-process UUID")
    ] = None,
    date: Annotated[dt.date | None, Query(description="Filter by date")] = None,
) -> list[RosterSuggestionItem]:
    """Get actionable ranked recommendations to resolve gaps."""
    service = RosterService(db)
    return service.get_suggestions(
        period_id=period_id,
        conflict_id=conflict_id,
        brand_process_id=brand_process_id,
        target_date=date,
    )


@router.post(
    "/{period_id}/acknowledge",
    response_model=RosterConflictRead,
    summary="Acknowledge conflict with reason",
    description="Ops Manager acknowledges a BLOCKING conflict with a mandatory reason, unlocking publish gating.",
)
def acknowledge_roster_conflict(
    period_id: uuid.UUID,
    request: RosterAcknowledgeRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_ops_manager)],
) -> RosterConflictRead:
    """Acknowledge a conflict with a logged justification reason."""
    service = RosterService(db)
    result = service.acknowledge_conflict(period_id, request, user_id=current_user.id)
    db.commit()
    return result


@router.post(
    "/{period_id}/publish",
    response_model=RosterPeriodRead,
    summary="Publish draft roster",
    description="Publish roster version if no unacknowledged BLOCKING conflicts remain. Archives previously published version and credits holiday work comp-offs. Ops Manager only.",
)
def publish_roster(
    period_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_ops_manager)],
) -> RosterPeriodRead:
    """Publish a draft roster version."""
    service = RosterService(db)
    result = service.publish_roster(period_id, user_id=current_user.id)
    db.commit()
    return result


@router.post(
    "/{period_id}/accrue-compoffs",
    response_model=list[CompOffLedgerRead],
    status_code=status.HTTP_201_CREATED,
    summary="Accrue comp-off credits for holiday work",
    description="Accrue 1 comp-off credit per employee for each HOLIDAY_WORK entry in this roster.",
)
def accrue_roster_compoffs(
    period_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_pod_lead_or_manager)],
) -> list[CompOffLedgerRead]:
    """Accrue comp-off credits for holiday work in this roster period."""
    service = CompOffService(db)
    entries = service.accrue_holiday_work_credits(period_id, actor_id=current_user.id)
    db.commit()
    for e in entries:
        db.refresh(e)
    return [CompOffLedgerRead.model_validate(e) for e in entries]


@router.post(
    "/{period_id}/clone",
    response_model=RosterPeriodRead,
    status_code=status.HTTP_201_CREATED,
    summary="Clone roster as new version",
    description="Clone an existing roster (draft or published) into a new working draft version n+1. Ops Manager or Pod Lead.",
)
def clone_roster(
    period_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_pod_lead_or_manager)],
    request: RosterCloneRequest | None = None,
) -> RosterPeriodRead:
    """Clone a roster period into a new draft version."""
    target_id = request.parent_period_id if request and request.parent_period_id else period_id
    service = RosterService(db)
    result = service.clone_roster(target_id, request, user_id=current_user.id)
    db.commit()
    return result


@router.post(
    "/{period_id}/repair",
    response_model=RosterRepairResponse,
    summary="Local repair around impacted window",
    description="Re-solve an affected window (dates and employees) with all unaffected cells locked. Shows cell and conflict diff. Ops Manager or Pod Lead.",
)
def repair_roster(
    period_id: uuid.UUID,
    request: RosterRepairRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_pod_lead_or_manager)],
) -> RosterRepairResponse:
    """Execute local repair around impacted window."""
    service = RosterService(db)
    result = service.repair_roster(period_id, request, user_id=current_user.id)
    if request.apply:
        db.commit()
    return result


@router.get(
    "/{period_id}/export",
    summary="Export roster to CSV or XLSX",
    description="Export roster grid, daily operational schedule, coverage summary, or conflicts report in CSV or XLSX format.",
    response_class=Response,
)
def export_roster(
    period_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    format: Annotated[
        str,
        Query(
            description="Export format: 'csv' or 'xlsx'",
            pattern="^(csv|xlsx|CSV|XLSX)$",
        ),
    ] = "csv",
    view: Annotated[
        str,
        Query(
            description="View mode: 'grid' (or 'month'), 'day', 'coverage' (or 'summary'), 'conflicts' (or 'report')"
        ),
    ] = "grid",
    date: Annotated[
        dt.date | None,
        Query(description="Target date for day view (defaults to month start)"),
    ] = None,
) -> Response:
    """Download exported schedule file."""
    service = RosterService(db)
    content, media_type, filename = service.export_roster(
        period_id=period_id, format=format, view=view, date=date
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
