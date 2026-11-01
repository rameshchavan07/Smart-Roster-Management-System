"""Roster generation, lifecycle, and persistence service.

Conforms to API_DOCUMENTATION.md §4, SCHEDULING_ENGINE.md §§6–8, and AGENTS.md rules.
Pure boundary layer: converts SQLAlchemy ORM models to pure Python scheduler dataclasses,
invokes CP-SAT or fallback greedy generator, and persists versioned results with full audit trail.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import uuid
from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.errors import (
    BusinessValidationError,
    ConflictError,
    NotFoundError,
    RosterBlockedError,
)
from app.models.auth import AuditLog
from app.models.core import (
    Assignment as DbAssignment,
)
from app.models.core import (
    Brand as DbBrand,
)
from app.models.core import (
    BrandProcess as DbBrandProcess,
)
from app.models.core import (
    Employee as DbEmployee,
)
from app.models.roster import (
    ConflictSeverity as DbConflictSeverity,
)
from app.models.roster import (
    EntrySource,
    RosterPeriod,
    RosterPeriodStatus,
)
from app.models.roster import (
    RosterConflict as DbRosterConflict,
)
from app.models.roster import (
    RosterEntry as DbRosterEntry,
)
from app.models.roster import (
    RosterEntryStatus as DbRosterEntryStatus,
)
from app.models.rules import (
    CoverageRule as DbCoverageRule,
)
from app.models.rules import (
    EmployeePreference as DbEmployeePreference,
)
from app.models.rules import (
    Holiday as DbHoliday,
)
from app.models.rules import (
    Leave as DbLeave,
)
from app.models.rules import (
    LeaveStatus as DbLeaveStatus,
)
from app.models.rules import (
    WeeklyOffRule as DbWeeklyOffRule,
)
from app.repositories.roster import (
    RosterConflictRepository,
    RosterEntryRepository,
    RosterPeriodRepository,
)
from app.repositories.rules import CompOffLedgerRepository
from app.scheduler.demand import build_demand_cell, build_demand_matrix
from app.scheduler.domain import (
    Assignment as DomainAssignment,
)
from app.scheduler.domain import (
    AssignmentType as DomainAssignmentType,
)
from app.scheduler.domain import (
    BrandProcess as DomainBrandProcess,
)
from app.scheduler.domain import (
    CalendarType as DomainCalendarType,
)
from app.scheduler.domain import (
    ConflictSeverity as DomainConflictSeverity,
)
from app.scheduler.domain import (
    CoverageRule as DomainCoverageRule,
)
from app.scheduler.domain import (
    Employee as DomainEmployee,
)
from app.scheduler.domain import (
    EmployeeLeave as DomainEmployeeLeave,
)
from app.scheduler.domain import (
    GenerationInput,
    GenerationOutput,
    RepairInput,
    RosterCell,
    RosterStatus,
    SolverStatus,
)
from app.scheduler.domain import (
    Holiday as DomainHoliday,
)
from app.scheduler.domain import (
    LeaveType as DomainLeaveType,
)
from app.scheduler.domain import (
    WeeklyOffMode as DomainWeeklyOffMode,
)
from app.scheduler.explain import enrich_conflicts
from app.scheduler.generator_cpsat import generate_cpsat
from app.scheduler.generator_greedy import generate_greedy
from app.scheduler.repair import repair_roster
from app.scheduler.supply import build_supply_matrix
from app.scheduler.validator import validate_roster
from app.schemas.roster import (
    RosterAcknowledgeRequest,
    RosterCellDiffItem,
    RosterCloneRequest,
    RosterCompareDelta,
    RosterCompareResponse,
    RosterConflictRead,
    RosterCoverageCell,
    RosterDayBrandProcessGroup,
    RosterDayEmployeeItem,
    RosterDayViewResponse,
    RosterEntriesBatchUpdateRequest,
    RosterEntriesLockRequest,
    RosterEntriesLockResponse,
    RosterEntriesUpdateResponse,
    RosterEntryRead,
    RosterGenerateRequest,
    RosterGenerateResponse,
    RosterGridCell,
    RosterGridRow,
    RosterGridViewResponse,
    RosterImpactRequest,
    RosterImpactResponse,
    RosterPeriodRead,
    RosterRepairRequest,
    RosterRepairResponse,
    RosterSuggestionItem,
    RosterSummary,
    RosterVersionMetrics,
    SuggestionNetEffect,
)
from app.services.export import (
    export_conflicts_csv,
    export_conflicts_xlsx,
    export_coverage_csv,
    export_coverage_xlsx,
    export_day_csv,
    export_day_xlsx,
    export_grid_csv,
    export_grid_xlsx,
)


def parse_month_bounds(month_input: str | dt.date) -> tuple[dt.date, dt.date]:
    """Parse a month input ('YYYY-MM' or 'YYYY-MM-DD' or date) into first and last day of month."""
    if isinstance(month_input, dt.date):
        start_date = month_input.replace(day=1)
    elif isinstance(month_input, str):
        cleaned = month_input.strip()
        parts = cleaned.split("-")
        if len(parts) >= 2:
            year = int(parts[0])
            month = int(parts[1])
            start_date = dt.date(year, month, 1)
        else:
            raise BusinessValidationError(
                f"Invalid month format: '{month_input}'. Expected YYYY-MM"
            )
    else:
        raise BusinessValidationError(f"Unsupported month type: {type(month_input)}")

    # Calculate last day of month
    # Day 28 + 4 days reaches next month, replace with day 1, then subtract 1 day
    next_month = (start_date.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    end_date = next_month - dt.timedelta(days=1)
    return start_date, end_date


class RosterService:
    """Service orchestrating roster generation, validation, and lifecycle management."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.period_repo = RosterPeriodRepository(session)
        self.entry_repo = RosterEntryRepository(session)
        self.conflict_repo = RosterConflictRepository(session)
        self.compoff_repo = CompOffLedgerRepository(session)
        self.settings = get_settings()

    def generate_roster(
        self, request: RosterGenerateRequest, actor_id: uuid.UUID | None = None
    ) -> RosterGenerateResponse:
        """Execute CP-SAT solver (with greedy fallback) and persist new roster version."""
        month_start, month_end = parse_month_bounds(request.month)

        # 1. Determine next version number for this month
        latest_version = self.period_repo.get_latest_version(month_start)
        next_version = latest_version + 1

        # 2. Extract options
        opts = request.options
        seed = request.seed if request.seed is not None else (opts.seed if opts else 42)
        time_limit_s = (
            request.time_limit_s
            if request.time_limit_s is not None
            else (opts.time_limit_s if opts else self.settings.SOLVER_TIME_LIMIT_S)
        )
        use_fallback = opts.use_fallback if opts else False

        # 3. Load DB records
        # Employees
        emp_stmt = select(DbEmployee).where(DbEmployee.is_active.is_(True))
        if request.pod_id:
            emp_stmt = emp_stmt.where(DbEmployee.pod_id == request.pod_id)
        db_employees = self.session.scalars(emp_stmt.order_by(DbEmployee.code)).all()

        if not db_employees:
            raise BusinessValidationError("No active employees found to schedule.")

        active_emp_ids = [e.id for e in db_employees]

        # BrandProcesses (active and attached to active brands)
        bp_stmt = (
            select(DbBrandProcess)
            .join(DbBrandProcess.brand)
            .where(DbBrandProcess.is_active.is_(True), DbBrand.is_active.is_(True))
        )
        db_bps = self.session.scalars(bp_stmt.order_by(DbBrandProcess.id)).all()
        if not db_bps:
            raise BusinessValidationError("No active brand-processes found to schedule.")

        active_bp_ids = [bp.id for bp in db_bps]

        # Staffing Assignments
        asgn_stmt = select(DbAssignment).where(
            DbAssignment.employee_id.in_(active_emp_ids),
            DbAssignment.brand_process_id.in_(active_bp_ids),
            (DbAssignment.valid_from.is_(None) | (DbAssignment.valid_from <= month_end)),
            (DbAssignment.valid_to.is_(None) | (DbAssignment.valid_to >= month_start)),
        )
        db_assignments = self.session.scalars(asgn_stmt).all()

        # Coverage Rules
        cr_stmt = select(DbCoverageRule).where(
            DbCoverageRule.is_active.is_(True),
            DbCoverageRule.brand_process_id.in_(active_bp_ids),
        )
        db_coverage_rules = self.session.scalars(cr_stmt).all()

        # Holidays in month
        hol_stmt = select(DbHoliday).where(
            DbHoliday.is_active.is_(True),
            DbHoliday.date >= month_start,
            DbHoliday.date <= month_end,
        )
        db_holidays = self.session.scalars(hol_stmt).all()

        # Approved Leaves overlapping month
        leave_stmt = select(DbLeave).where(
            DbLeave.status == DbLeaveStatus.APPROVED,
            DbLeave.employee_id.in_(active_emp_ids),
            DbLeave.start_date <= month_end,
            DbLeave.end_date >= month_start,
        )
        db_leaves = self.session.scalars(leave_stmt).all()

        # Weekly Off Rules
        wor_stmt = select(DbWeeklyOffRule).where(
            DbWeeklyOffRule.employee_id.in_(active_emp_ids),
        )
        db_wo_rules = self.session.scalars(wor_stmt).all()
        wo_rules_by_emp = {r.employee_id: r for r in db_wo_rules}

        # Employee Preferences
        pref_stmt = select(DbEmployeePreference).where(
            DbEmployeePreference.employee_id.in_(active_emp_ids),
        )
        db_prefs = self.session.scalars(pref_stmt).all()
        prefs_by_emp: dict[uuid.UUID, list[DbEmployeePreference]] = {
            eid: [] for eid in active_emp_ids
        }
        for p in db_prefs:
            prefs_by_emp[p.employee_id].append(p)

        # 4. Check previous month tail carry-in work streaks (H3)
        prev_month_tail: dict[str, int] = {}
        prev_month_start = (month_start - dt.timedelta(days=1)).replace(day=1)
        prev_period = (
            self.period_repo.get_published_period(prev_month_start)
            or self.session.scalars(
                select(RosterPeriod)
                .where(RosterPeriod.month == prev_month_start)
                .order_by(RosterPeriod.version.desc())
            ).first()
        )
        if prev_period:
            prev_entries = self.entry_repo.get_by_period(
                period_id=prev_period.id,
                date_from=month_start - dt.timedelta(days=6),
                date_to=month_start - dt.timedelta(days=1),
            )
            entries_by_emp_date = {(e.employee_id, e.date): e for e in prev_entries}
            for eid in active_emp_ids:
                streak = 0
                for back in range(1, 7):
                    check_d = month_start - dt.timedelta(days=back)
                    entry = entries_by_emp_date.get((eid, check_d))
                    if entry and entry.status in (
                        DbRosterEntryStatus.WORK,
                        DbRosterEntryStatus.HOLIDAY_WORK,
                    ):
                        streak += 1
                    else:
                        break
                if streak > 0:
                    prev_month_tail[str(eid)] = streak

        # 5. Convert ORM records to pure scheduler domain dataclasses
        domain_employees: list[DomainEmployee] = []
        for e in db_employees:
            wo_rule = wo_rules_by_emp.get(e.id)
            wo_mode = (
                DomainWeeklyOffMode(wo_rule.mode.value) if wo_rule else DomainWeeklyOffMode.ANY
            )
            fixed_weekdays = tuple(wo_rule.weekdays) if wo_rule and wo_rule.weekdays else ()

            # Parse preferences
            emp_p_list = prefs_by_emp.get(e.id, [])
            pref_weekdays: list[int] = []
            pref_dates: list[dt.date] = []
            for p in emp_p_list:
                if p.kind.value == "PREFERRED_OFF_WEEKDAY" and "weekday" in p.value:
                    pref_weekdays.append(int(p.value["weekday"]))
                elif p.kind.value == "PREFERRED_OFF_DATE" and "date" in p.value:
                    with contextlib.suppress(Exception):
                        pref_dates.append(dt.date.fromisoformat(str(p.value["date"])))

            domain_employees.append(
                DomainEmployee(
                    id=str(e.id),
                    code=e.code,
                    full_name=e.full_name,
                    pod_id=str(e.pod_id),
                    is_floater=e.is_floater,
                    weekly_off_count=e.weekly_off_count,
                    max_consecutive_days=e.max_consecutive_days,
                    max_concurrent_processes=e.max_concurrent_processes,
                    weekly_off_mode=wo_mode,
                    fixed_weekly_off_weekdays=fixed_weekdays,
                    preferred_weekly_off_weekdays=tuple(pref_weekdays),
                    preferred_off_dates=tuple(pref_dates),
                )
            )

        domain_bps: list[DomainBrandProcess] = [
            DomainBrandProcess(
                id=str(bp.id),
                brand_id=str(bp.brand_id),
                brand_name=bp.brand.name if bp.brand else "",
                process_id=str(bp.process_id),
                process_name=bp.process.name if bp.process else "",
                calendar_type=DomainCalendarType(bp.calendar_type.value),
                min_coverage_default=bp.min_coverage_default,
            )
            for bp in db_bps
        ]

        domain_assignments: list[DomainAssignment] = [
            DomainAssignment(
                employee_id=str(a.employee_id),
                brand_process_id=str(a.brand_process_id),
                type=DomainAssignmentType(a.type.value),
            )
            for a in db_assignments
        ]

        domain_rules: list[DomainCoverageRule] = [
            DomainCoverageRule(
                brand_process_id=str(cr.brand_process_id),
                weekday=cr.weekday,
                specific_date=cr.specific_date,
                min_staff=cr.min_staff,
            )
            for cr in db_coverage_rules
        ]

        domain_holidays: list[DomainHoliday] = [
            DomainHoliday(
                date=h.date,
                name=h.name,
                brand_id=str(h.brand_id) if h.brand_id else None,
            )
            for h in db_holidays
        ]

        domain_leaves: list[DomainEmployeeLeave] = [
            DomainEmployeeLeave(
                employee_id=str(lv.employee_id),
                start_date=lv.start_date,
                end_date=lv.end_date,
                type=DomainLeaveType(lv.type.value),
            )
            for lv in db_leaves
        ]

        # 6. Build Demand and Supply Matrices
        demand_matrix = build_demand_matrix(
            brand_processes=domain_bps,
            start_date=month_start,
            end_date=month_end,
            rules=domain_rules,
            holidays=domain_holidays,
        )

        supply_matrix = build_supply_matrix(
            employees=domain_employees,
            start_date=month_start,
            end_date=month_end,
            assignments=domain_assignments,
            brand_processes=domain_bps,
            holidays=domain_holidays,
            leaves=domain_leaves,
            locked_cells=(),
        )

        # Fetch initial comp-off balances for all employees
        emp_uuids = [e.id for e in db_employees]
        compoff_balances = self.compoff_repo.get_balances_for_employees(emp_uuids)

        # 7. Assemble GenerationInput
        gen_input = GenerationInput(
            month_start=month_start,
            month_end=month_end,
            employees=tuple(domain_employees),
            brand_processes=tuple(domain_bps),
            assignments=tuple(domain_assignments),
            coverage_rules=tuple(domain_rules),
            holidays=tuple(domain_holidays),
            leaves=tuple(domain_leaves),
            locked_cells=(),
            supply_matrix=tuple(supply_matrix),
            demand_matrix=tuple(demand_matrix),
            random_seed=seed,
            time_limit_seconds=float(time_limit_s),
            previous_tail_work_days=prev_month_tail,
            initial_compoff_balances=compoff_balances,
        )

        # 8. Solve (CP-SAT with automatic fallback to Greedy)
        out: GenerationOutput
        if use_fallback:
            out = generate_greedy(gen_input)
        else:
            try:
                out = generate_cpsat(gen_input)
                if out.solver_status == SolverStatus.FALLBACK:
                    out = generate_greedy(gen_input)
            except Exception:
                # Guaranteed fallback if CP-SAT encounters an unexpected environment exception
                out = generate_greedy(gen_input)

        # 9. Persist RosterPeriod, Entries, and Conflicts
        period = RosterPeriod(
            id=uuid.uuid4(),
            month=month_start,
            version=next_version,
            status=RosterPeriodStatus.DRAFT,
            solver_status=out.solver_status.value,
            generation_params={
                "seed": seed,
                "time_limit_s": time_limit_s,
                "solve_time_seconds": round(out.solve_time_seconds, 3),
                "objective_value": round(out.objective_value, 2),
                "pod_id": str(request.pod_id) if request.pod_id else None,
            },
            created_by_id=actor_id,
        )
        self.session.add(period)
        self.session.flush()

        # Bulk create entries
        db_entries: list[DbRosterEntry] = [
            DbRosterEntry(
                id=uuid.uuid4(),
                roster_period_id=period.id,
                employee_id=uuid.UUID(cell.employee_id),
                date=cell.date,
                status=DbRosterEntryStatus(cell.status.value),
                source=EntrySource.LOCKED_FIXED if cell.is_locked else EntrySource.AUTO,
                is_locked=cell.is_locked,
            )
            for cell in out.roster_cells
        ]
        self.entry_repo.bulk_create(db_entries)

        # Bulk create conflicts
        db_conflicts: list[DbRosterConflict] = [
            DbRosterConflict(
                id=uuid.uuid4(),
                roster_period_id=period.id,
                code=c.code.value,
                severity=DbConflictSeverity(c.severity.value),
                brand_process_id=uuid.UUID(c.brand_process_id) if c.brand_process_id else None,
                employee_id=uuid.UUID(c.employee_id) if c.employee_id else None,
                date_from=c.date_from,
                date_to=c.date_to,
                root_causes=list(c.root_causes),
                message=c.message,
                suggestions=[
                    {
                        "type": s.type.value,
                        "action": s.action,
                        "description": s.description,
                        "employee_id": s.employee_id,
                        "brand_process_id": s.brand_process_id,
                        "target_date": s.target_date.isoformat() if s.target_date else None,
                        "source_date": s.source_date.isoformat() if s.source_date else None,
                        "net_impact": s.net_impact,
                        "score": s.score,
                    }
                    for s in c.suggestions
                ],
            )
            for c in out.validation_result.conflicts
        ]
        self.conflict_repo.bulk_create(db_conflicts)

        # Audit log entry
        audit = AuditLog(
            user_id=actor_id,
            action="CREATE_ROSTER",
            entity_type="ROSTER_PERIOD",
            entity_id=str(period.id),
            after={
                "month": month_start.isoformat(),
                "version": next_version,
                "status": period.status.value,
                "solver_status": period.solver_status,
                "entries_count": len(db_entries),
                "conflicts_count": len(db_conflicts),
            },
        )
        self.session.add(audit)
        self.session.flush()

        # Compute summary metrics
        total_req = sum(c.required for c in out.coverage_cells)
        total_covered = sum(c.covered for c in out.coverage_cells)
        coverage_pct = round((total_covered / total_req * 100), 1) if total_req > 0 else 100.0

        summary = RosterSummary(
            blocking=out.validation_result.blocking_count,
            warnings=out.validation_result.warning_count,
            info=out.validation_result.info_count,
            coverage_pct=coverage_pct,
        )

        return RosterGenerateResponse(
            id=period.id,
            month=period.month,
            version=period.version,
            status=period.status,
            solver_status=period.solver_status,
            summary=summary,
            created_at=period.created_at,
        )

    def get_roster_period(self, period_id: uuid.UUID) -> RosterPeriodRead:
        """Fetch metadata for a single roster version."""
        period = self.period_repo.get_by_id(period_id)
        if not period:
            raise NotFoundError(f"Roster period '{period_id}' not found.")

        entries_count = len(period.entries)
        conflicts_count = len(period.conflicts)

        read = RosterPeriodRead.model_validate(period)
        read.entries_count = entries_count
        read.conflicts_count = conflicts_count
        return read

    def list_roster_periods(self, month: dt.date | str | None = None) -> list[RosterPeriodRead]:
        """List all versions created for a specific month (or all periods if month is None)."""
        month_start: dt.date | None = None
        if month is not None:
            month_start, _ = parse_month_bounds(month)
        periods = self.period_repo.list_periods(month_start)
        return [self.get_roster_period(p.id) for p in periods]

    def get_grid_view(
        self,
        period_id: uuid.UUID,
        view: str = "company",
        ref_id: uuid.UUID | None = None,
    ) -> RosterGridViewResponse:
        """Construct the interactive roster matrix for company, pod, brand, process, or employee view."""
        period_read = self.get_roster_period(period_id)
        start_date, end_date = parse_month_bounds(period_read.month)

        stmt = (
            select(DbEmployee)
            .options(
                joinedload(DbEmployee.pod),
                joinedload(DbEmployee.assignments)
                .joinedload(DbAssignment.brand_process)
                .joinedload(DbBrandProcess.brand),
                joinedload(DbEmployee.assignments)
                .joinedload(DbAssignment.brand_process)
                .joinedload(DbBrandProcess.process),
            )
            .where(DbEmployee.is_active.is_(True))
        )

        view_clean = view.lower().strip()
        if view_clean == "pod":
            if ref_id is not None:
                stmt = stmt.where(DbEmployee.pod_id == ref_id)
        elif view_clean == "brand":
            if ref_id is not None:
                stmt = (
                    stmt.join(DbEmployee.assignments)
                    .join(DbAssignment.brand_process)
                    .where(DbBrandProcess.brand_id == ref_id)
                )
        elif view_clean == "process":
            if ref_id is not None:
                stmt = (
                    stmt.join(DbEmployee.assignments)
                    .join(DbAssignment.brand_process)
                    .where(DbBrandProcess.process_id == ref_id)
                )
        elif view_clean == "employee":
            if ref_id is not None:
                stmt = stmt.where(DbEmployee.id == ref_id)
        elif view_clean == "company":
            pass
        else:
            raise BusinessValidationError(
                f"Invalid view mode '{view}'. Expected one of: company, pod, brand, process, employee"
            )

        stmt = stmt.order_by(DbEmployee.code)
        employees = self.session.scalars(stmt).unique().all()
        emp_ids = [e.id for e in employees]

        # Fetch roster entries for these employees and this period
        entries_stmt = select(DbRosterEntry).where(
            DbRosterEntry.roster_period_id == period_id,
            DbRosterEntry.employee_id.in_(emp_ids),
        )
        entries = self.session.scalars(entries_stmt).all() if emp_ids else []
        entry_map = {(e.employee_id, e.date): e for e in entries}

        # Fetch conflicts for this period to badge cells
        conflicts = self.conflict_repo.get_by_period(period_id)
        conflicts_by_emp_date: dict[tuple[uuid.UUID, dt.date], list[str]] = defaultdict(list)
        for c in conflicts:
            if c.employee_id and c.date_from:
                end_d = c.date_to or c.date_from
                curr = c.date_from
                while curr <= end_d:
                    conflicts_by_emp_date[(c.employee_id, curr)].append(c.code)
                    curr += dt.timedelta(days=1)

        # Build Grid Rows
        days_in_month = (end_date - start_date).days + 1
        all_dates = [start_date + dt.timedelta(days=i) for i in range(days_in_month)]

        rows: list[RosterGridRow] = []
        for emp in employees:
            primary_asgns = [
                f"{a.brand_process.brand.code} {a.brand_process.process.code}"
                for a in emp.assignments
                if a.type.value == "PRIMARY"
                and a.brand_process
                and a.brand_process.brand
                and a.brand_process.process
            ]
            cells: dict[str, RosterGridCell] = {}
            for d in all_dates:
                d_str = d.isoformat()
                entry = entry_map.get((emp.id, d))
                cell_conflicts = conflicts_by_emp_date.get((emp.id, d), [])
                if entry:
                    cells[d_str] = RosterGridCell(
                        date=d,
                        status=entry.status,
                        source=entry.source,
                        is_locked=entry.is_locked,
                        note=entry.note,
                        conflicts=cell_conflicts,
                    )
                else:
                    cells[d_str] = RosterGridCell(
                        date=d,
                        status=DbRosterEntryStatus.WEEKLY_OFF,
                        source=EntrySource.AUTO,
                        is_locked=False,
                        note=None,
                        conflicts=cell_conflicts,
                    )

            rows.append(
                RosterGridRow(
                    employee_id=emp.id,
                    employee_name=emp.full_name,
                    employee_code=emp.code,
                    pod_name=emp.pod.name if emp.pod else None,
                    primary_assignments=primary_asgns,
                    cells=cells,
                )
            )

        return RosterGridViewResponse(
            period=period_read,
            view=view_clean,
            start_date=start_date,
            end_date=end_date,
            rows=rows,
        )

    def get_coverage(
        self,
        period_id: uuid.UUID,
        brand_process_id: uuid.UUID | None = None,
        date_from: dt.date | None = None,
        date_to: dt.date | None = None,
    ) -> list[RosterCoverageCell]:
        """Compute required vs actual coverage headcount for brand-processes per date."""
        period_read = self.get_roster_period(period_id)
        month_start, month_end = parse_month_bounds(period_read.month)
        start_d = date_from or month_start
        end_d = date_to or month_end

        # Load brand-processes
        bp_stmt = (
            select(DbBrandProcess)
            .options(
                joinedload(DbBrandProcess.brand),
                joinedload(DbBrandProcess.process),
                joinedload(DbBrandProcess.coverage_rules),
            )
            .where(DbBrandProcess.is_active.is_(True))
        )
        if brand_process_id:
            bp_stmt = bp_stmt.where(DbBrandProcess.id == brand_process_id)
        db_bps = self.session.scalars(bp_stmt).unique().all()
        bp_ids = [bp.id for bp in db_bps]

        if not bp_ids:
            return []

        # Load assignments for these brand-processes
        asgns_stmt = select(DbAssignment).where(
            DbAssignment.brand_process_id.in_(bp_ids),
            (DbAssignment.valid_from.is_(None) | (DbAssignment.valid_from <= end_d)),
            (DbAssignment.valid_to.is_(None) | (DbAssignment.valid_to >= start_d)),
        )
        asgns = self.session.scalars(asgns_stmt).all()
        bp_emp_map: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
        for a in asgns:
            bp_emp_map[a.brand_process_id].add(a.employee_id)

        # Load holidays
        holidays_stmt = select(DbHoliday).where(
            DbHoliday.is_active.is_(True),
            DbHoliday.date >= start_d,
            DbHoliday.date <= end_d,
        )
        db_holidays = self.session.scalars(holidays_stmt).all()
        domain_holidays = [
            DomainHoliday(
                date=h.date,
                name=h.name,
                brand_id=str(h.brand_id) if h.brand_id else None,
            )
            for h in db_holidays
        ]

        # Load roster entries in range
        entries_stmt = select(DbRosterEntry).where(
            DbRosterEntry.roster_period_id == period_id,
            DbRosterEntry.date >= start_d,
            DbRosterEntry.date <= end_d,
        )
        entries = self.session.scalars(entries_stmt).all()
        working_emps_by_date: dict[dt.date, set[uuid.UUID]] = defaultdict(set)
        for e in entries:
            if e.status in (DbRosterEntryStatus.WORK, DbRosterEntryStatus.HOLIDAY_WORK):
                working_emps_by_date[e.date].add(e.employee_id)

        # Compute coverage per date and brand-process
        result: list[RosterCoverageCell] = []
        curr = start_d
        while curr <= end_d:
            for bp in db_bps:
                domain_bp = DomainBrandProcess(
                    id=str(bp.id),
                    brand_id=str(bp.brand_id),
                    brand_name=bp.brand.name if bp.brand else "",
                    process_id=str(bp.process_id),
                    process_name=bp.process.name if bp.process else "",
                    calendar_type=DomainCalendarType(bp.calendar_type.value),
                    min_coverage_default=bp.min_coverage_default,
                )
                domain_rules = [
                    DomainCoverageRule(
                        brand_process_id=str(r.brand_process_id),
                        weekday=r.weekday,
                        specific_date=r.specific_date,
                        min_staff=r.min_staff,
                        reason=r.reason or "",
                    )
                    for r in bp.coverage_rules
                    if r.is_active
                ]
                cell = build_demand_cell(
                    domain_bp, curr, holidays=domain_holidays, rules=domain_rules
                )
                required = cell.required_headcount

                assigned_emps = bp_emp_map.get(bp.id, set())
                actual = len(assigned_emps.intersection(working_emps_by_date.get(curr, set())))
                shortfall = max(0, required - actual)

                result.append(
                    RosterCoverageCell(
                        date=curr,
                        brand_process_id=bp.id,
                        brand_name=bp.brand.name if bp.brand else None,
                        process_name=bp.process.name if bp.process else None,
                        required=required,
                        actual=actual,
                        shortfall=shortfall,
                    )
                )
            curr += dt.timedelta(days=1)

        return result

    def get_day_view(self, period_id: uuid.UUID, target_date: dt.date) -> RosterDayViewResponse:
        """Provide detailed staffing breakdown on a single date grouped by brand-process."""
        self.get_roster_period(period_id)

        # Fetch active brand-processes
        bp_stmt = (
            select(DbBrandProcess)
            .options(
                joinedload(DbBrandProcess.brand),
                joinedload(DbBrandProcess.process),
                joinedload(DbBrandProcess.coverage_rules),
            )
            .where(DbBrandProcess.is_active.is_(True))
            .order_by(DbBrandProcess.id)
        )
        db_bps = self.session.scalars(bp_stmt).unique().all()

        # Fetch assignments for target date
        asgns_stmt = (
            select(DbAssignment)
            .options(joinedload(DbAssignment.employee))
            .where(
                (DbAssignment.valid_from.is_(None) | (DbAssignment.valid_from <= target_date)),
                (DbAssignment.valid_to.is_(None) | (DbAssignment.valid_to >= target_date)),
            )
        )
        asgns = self.session.scalars(asgns_stmt).all()
        bp_asgns_map: dict[uuid.UUID, list[DbAssignment]] = defaultdict(list)
        all_assigned_emp_ids: set[uuid.UUID] = set()
        for a in asgns:
            bp_asgns_map[a.brand_process_id].append(a)
            all_assigned_emp_ids.add(a.employee_id)

        # Fetch entries on target_date
        entries_stmt = (
            select(DbRosterEntry)
            .options(joinedload(DbRosterEntry.employee))
            .where(
                DbRosterEntry.roster_period_id == period_id,
                DbRosterEntry.date == target_date,
            )
        )
        entries = self.session.scalars(entries_stmt).all()
        entry_by_emp: dict[uuid.UUID, DbRosterEntry] = {e.employee_id: e for e in entries}

        # Holidays for demand
        holidays_stmt = select(DbHoliday).where(
            DbHoliday.is_active.is_(True),
            DbHoliday.date == target_date,
        )
        db_holidays = self.session.scalars(holidays_stmt).all()
        domain_holidays = [
            DomainHoliday(
                date=h.date,
                name=h.name,
                brand_id=str(h.brand_id) if h.brand_id else None,
            )
            for h in db_holidays
        ]

        groups: list[RosterDayBrandProcessGroup] = []
        for bp in db_bps:
            domain_bp = DomainBrandProcess(
                id=str(bp.id),
                brand_id=str(bp.brand_id),
                brand_name=bp.brand.name if bp.brand else "",
                process_id=str(bp.process_id),
                process_name=bp.process.name if bp.process else "",
                calendar_type=DomainCalendarType(bp.calendar_type.value),
                min_coverage_default=bp.min_coverage_default,
            )
            domain_rules = [
                DomainCoverageRule(
                    brand_process_id=str(r.brand_process_id),
                    weekday=r.weekday,
                    specific_date=r.specific_date,
                    min_staff=r.min_staff,
                    reason=r.reason or "",
                )
                for r in bp.coverage_rules
                if r.is_active
            ]
            cell = build_demand_cell(
                domain_bp, target_date, holidays=domain_holidays, rules=domain_rules
            )
            required = cell.required_headcount
            is_operating = cell.is_operating_day

            assigned_list = bp_asgns_map.get(bp.id, [])
            working_items: list[RosterDayEmployeeItem] = []
            off_items: list[RosterDayEmployeeItem] = []

            for a in assigned_list:
                emp = a.employee
                if not emp:
                    continue
                ent = entry_by_emp.get(emp.id)
                status_val = ent.status if ent else DbRosterEntryStatus.WEEKLY_OFF
                is_locked = ent.is_locked if ent else False
                note = ent.note if ent else None

                item = RosterDayEmployeeItem(
                    employee_id=emp.id,
                    employee_name=emp.full_name,
                    employee_code=emp.code,
                    assignment_type=a.type.value,
                    status=status_val,
                    is_locked=is_locked,
                    note=note,
                )
                if status_val in (DbRosterEntryStatus.WORK, DbRosterEntryStatus.HOLIDAY_WORK):
                    working_items.append(item)
                else:
                    off_items.append(item)

            actual = len(working_items)
            shortfall = max(0, required - actual)

            groups.append(
                RosterDayBrandProcessGroup(
                    brand_process_id=bp.id,
                    brand_name=bp.brand.name if bp.brand else "",
                    process_name=bp.process.name if bp.process else "",
                    required=required,
                    actual=actual,
                    shortfall=shortfall,
                    is_operating_day=is_operating,
                    working_employees=working_items,
                    off_employees=off_items,
                )
            )

        unassigned_working: list[RosterDayEmployeeItem] = []
        for emp_id, ent in entry_by_emp.items():
            if emp_id not in all_assigned_emp_ids and ent.status in (
                DbRosterEntryStatus.WORK,
                DbRosterEntryStatus.HOLIDAY_WORK,
            ):
                emp = ent.employee
                if emp:
                    unassigned_working.append(
                        RosterDayEmployeeItem(
                            employee_id=emp.id,
                            employee_name=emp.full_name,
                            employee_code=emp.code,
                            assignment_type=None,
                            status=ent.status,
                            is_locked=ent.is_locked,
                            note=ent.note,
                        )
                    )

        return RosterDayViewResponse(
            period_id=period_id,
            date=target_date,
            groups=groups,
            unassigned_working_employees=unassigned_working,
        )

    def get_conflicts(
        self,
        period_id: uuid.UUID,
        severity: str | None = None,
        brand_id: uuid.UUID | None = None,
        target_date: dt.date | None = None,
        employee_id: uuid.UUID | None = None,
    ) -> list[RosterConflictRead]:
        """Fetch conflicts with entity names enriched for table display."""
        self.get_roster_period(period_id)

        conflicts = self.conflict_repo.get_by_period(
            period_id=period_id,
            severity=severity,
            brand_id=brand_id,
            target_date=target_date,
            employee_id=employee_id,
        )

        results: list[RosterConflictRead] = []
        for c in conflicts:
            read = RosterConflictRead.model_validate(c)
            if c.brand_process and c.brand_process.brand:
                read.brand_name = c.brand_process.brand.name
                read.brand_code = c.brand_process.brand.code
            if c.brand_process and c.brand_process.process:
                read.process_name = c.brand_process.process.name
                read.process_code = c.brand_process.process.code
            if c.employee:
                read.employee_name = c.employee.full_name
                read.employee_code = c.employee.code
            results.append(read)

        return results

    def simulate_impact(
        self, period_id: uuid.UUID, request: RosterImpactRequest
    ) -> RosterImpactResponse:
        """Dry-run proposed changes/edits without DB mutation, diffing conflicts into new, resolved, and unchanged."""
        period_read = self.get_roster_period(period_id)
        month_start, month_end = parse_month_bounds(period_read.month)

        # 1. Identify affected dates
        affected_dates: set[dt.date] = set()
        for ed in request.edits:
            affected_dates.add(ed.date)
        for ch in request.changes:
            st = ch.start_date or ch.date
            en = ch.end_date or ch.date or st
            if st and en:
                cur = st
                while cur <= en:
                    affected_dates.add(cur)
                    cur += dt.timedelta(days=1)
            elif ch.date:
                affected_dates.add(ch.date)

        # 2. Fetch baseline DB models
        emp_stmt = select(DbEmployee).where(DbEmployee.is_active.is_(True))
        db_employees = self.session.scalars(emp_stmt.order_by(DbEmployee.code)).all()
        emp_ids = [e.id for e in db_employees]
        emp_name_map = {str(e.id): e.full_name for e in db_employees}

        bp_stmt = (
            select(DbBrandProcess)
            .join(DbBrandProcess.brand)
            .where(DbBrandProcess.is_active.is_(True), DbBrand.is_active.is_(True))
        )
        db_bps = self.session.scalars(bp_stmt.order_by(DbBrandProcess.id)).all()
        bp_ids = [bp.id for bp in db_bps]
        bp_name_map = {str(bp.id): bp.brand.name if bp.brand else "" for bp in db_bps}
        bp_proc_map = {str(bp.id): bp.process.name if bp.process else "" for bp in db_bps}

        asgn_stmt = select(DbAssignment).where(
            DbAssignment.employee_id.in_(emp_ids),
            DbAssignment.brand_process_id.in_(bp_ids),
            (DbAssignment.valid_from.is_(None) | (DbAssignment.valid_from <= month_end)),
            (DbAssignment.valid_to.is_(None) | (DbAssignment.valid_to >= month_start)),
        )
        db_assignments = self.session.scalars(asgn_stmt).all()

        cr_stmt = select(DbCoverageRule).where(
            DbCoverageRule.is_active.is_(True),
            DbCoverageRule.brand_process_id.in_(bp_ids),
        )
        db_coverage_rules = self.session.scalars(cr_stmt).all()

        hol_stmt = select(DbHoliday).where(
            DbHoliday.is_active.is_(True),
            DbHoliday.date >= month_start,
            DbHoliday.date <= month_end,
        )
        db_holidays = self.session.scalars(hol_stmt).all()

        leave_stmt = select(DbLeave).where(
            DbLeave.status == DbLeaveStatus.APPROVED,
            DbLeave.employee_id.in_(emp_ids),
            DbLeave.start_date <= month_end,
            DbLeave.end_date >= month_start,
        )
        db_leaves = self.session.scalars(leave_stmt).all()

        wor_stmt = select(DbWeeklyOffRule).where(
            DbWeeklyOffRule.employee_id.in_(emp_ids),
        )
        db_wo_rules = self.session.scalars(wor_stmt).all()
        wo_rules_by_emp = {r.employee_id: r for r in db_wo_rules}

        pref_stmt = select(DbEmployeePreference).where(
            DbEmployeePreference.employee_id.in_(emp_ids),
        )
        db_prefs = self.session.scalars(pref_stmt).all()
        prefs_by_emp: dict[uuid.UUID, list[DbEmployeePreference]] = {eid: [] for eid in emp_ids}
        for p in db_prefs:
            prefs_by_emp[p.employee_id].append(p)

        # 3. Build domain objects
        domain_employees: list[DomainEmployee] = []
        for e in db_employees:
            wo_rule = wo_rules_by_emp.get(e.id)
            wo_mode = (
                DomainWeeklyOffMode(wo_rule.mode.value) if wo_rule else DomainWeeklyOffMode.ANY
            )
            fixed_weekdays = tuple(wo_rule.weekdays) if wo_rule and wo_rule.weekdays else ()

            emp_p_list = prefs_by_emp.get(e.id, [])
            pref_weekdays: list[int] = []
            pref_dates: list[dt.date] = []
            for p in emp_p_list:
                if p.kind.value == "PREFERRED_OFF_WEEKDAY" and "weekday" in p.value:
                    pref_weekdays.append(int(p.value["weekday"]))
                elif p.kind.value == "PREFERRED_OFF_DATE" and "date" in p.value:
                    with contextlib.suppress(Exception):
                        pref_dates.append(dt.date.fromisoformat(str(p.value["date"])))

            domain_employees.append(
                DomainEmployee(
                    id=str(e.id),
                    code=e.code,
                    full_name=e.full_name,
                    pod_id=str(e.pod_id),
                    is_floater=e.is_floater,
                    weekly_off_count=e.weekly_off_count,
                    max_consecutive_days=e.max_consecutive_days,
                    max_concurrent_processes=e.max_concurrent_processes,
                    weekly_off_mode=wo_mode,
                    fixed_weekly_off_weekdays=fixed_weekdays,
                    preferred_weekly_off_weekdays=tuple(pref_weekdays),
                    preferred_off_dates=tuple(pref_dates),
                )
            )

        domain_bps = [
            DomainBrandProcess(
                id=str(bp.id),
                brand_id=str(bp.brand_id),
                brand_name=bp.brand.name if bp.brand else "",
                process_id=str(bp.process_id),
                process_name=bp.process.name if bp.process else "",
                calendar_type=DomainCalendarType(bp.calendar_type.value),
                min_coverage_default=bp.min_coverage_default,
            )
            for bp in db_bps
        ]

        domain_assignments = [
            DomainAssignment(
                employee_id=str(a.employee_id),
                brand_process_id=str(a.brand_process_id),
                type=DomainAssignmentType(a.type.value),
            )
            for a in db_assignments
        ]

        domain_holidays = [
            DomainHoliday(
                date=h.date,
                name=h.name,
                brand_id=str(h.brand_id) if h.brand_id else None,
            )
            for h in db_holidays
        ]

        domain_rules = [
            DomainCoverageRule(
                brand_process_id=str(cr.brand_process_id),
                weekday=cr.weekday,
                specific_date=cr.specific_date,
                min_staff=cr.min_staff,
                reason=cr.reason or "",
            )
            for cr in db_coverage_rules
        ]

        domain_leaves = [
            DomainEmployeeLeave(
                employee_id=str(lv.employee_id),
                start_date=lv.start_date,
                end_date=lv.end_date,
                type=DomainLeaveType(lv.type.value)
                if hasattr(lv.type, "value")
                else DomainLeaveType.PLANNED,
            )
            for lv in db_leaves
        ]

        # 4. Check previous month tail carry-in work streaks (H3)
        prev_month_tail: dict[str, int] = {}
        prev_month_start = (month_start - dt.timedelta(days=1)).replace(day=1)
        prev_period = (
            self.period_repo.get_published_period(prev_month_start)
            or self.session.scalars(
                select(RosterPeriod)
                .where(RosterPeriod.month == prev_month_start)
                .order_by(RosterPeriod.version.desc())
            ).first()
        )
        if prev_period:
            prev_entries = self.entry_repo.get_by_period(
                period_id=prev_period.id,
                date_from=month_start - dt.timedelta(days=6),
                date_to=month_start - dt.timedelta(days=1),
            )
            entries_by_emp_date = {(e.employee_id, e.date): e for e in prev_entries}
            for eid in emp_ids:
                streak = 0
                for back in range(1, 7):
                    check_d = month_start - dt.timedelta(days=back)
                    entry = entries_by_emp_date.get((eid, check_d))
                    if entry and entry.status in (
                        DbRosterEntryStatus.WORK,
                        DbRosterEntryStatus.HOLIDAY_WORK,
                    ):
                        streak += 1
                    else:
                        break
                prev_month_tail[str(eid)] = streak

        # 5. Load existing persisted roster entries into cell map
        db_entries = self.entry_repo.get_by_period(period_id)
        roster_cells_map: dict[tuple[str, dt.date], RosterCell] = {}
        for e in db_entries:
            roster_cells_map[(str(e.employee_id), e.date)] = RosterCell(
                employee_id=str(e.employee_id),
                date=e.date,
                status=RosterStatus(e.status.value),
                is_locked=e.is_locked,
                note=e.note or "",
            )

        # 6. Apply proposed edits & changes in-memory
        for ed in request.edits:
            emp_k = str(ed.employee_id)
            existing = roster_cells_map.get((emp_k, ed.date))
            note = ed.note if ed.note is not None else (existing.note if existing else "")
            is_locked = (
                ed.is_locked
                if ed.is_locked is not None
                else (existing.is_locked if existing else True)
            )
            roster_cells_map[(emp_k, ed.date)] = RosterCell(
                employee_id=emp_k,
                date=ed.date,
                status=RosterStatus(ed.status.value),
                is_locked=is_locked,
                note=note,
            )

        for ch in request.changes:
            ch_type = ch.type.value if hasattr(ch.type, "value") else str(ch.type)
            if ch_type in ("ADD_LEAVE", "MARK_UNAVAILABLE"):
                if ch.employee_id:
                    emp_k = str(ch.employee_id)
                    st_d = ch.start_date or ch.date
                    en_d = ch.end_date or ch.date or st_d
                    if st_d and en_d:
                        domain_leaves.append(
                            DomainEmployeeLeave(
                                employee_id=emp_k,
                                start_date=st_d,
                                end_date=en_d,
                                type=DomainLeaveType.PLANNED,
                            )
                        )
                        cur = st_d
                        new_status = (
                            RosterStatus.LEAVE
                            if ch_type == "ADD_LEAVE"
                            else (
                                RosterStatus(ch.status.value)
                                if ch.status
                                else RosterStatus.WEEKLY_OFF
                            )
                        )
                        while cur <= en_d:
                            roster_cells_map[(emp_k, cur)] = RosterCell(
                                employee_id=emp_k,
                                date=cur,
                                status=new_status,
                                is_locked=True,
                                note=f"Simulated {ch_type}",
                            )
                            cur += dt.timedelta(days=1)
            elif ch_type == "CELL_EDIT" and ch.employee_id and ch.date and ch.status:
                emp_k = str(ch.employee_id)
                roster_cells_map[(emp_k, ch.date)] = RosterCell(
                    employee_id=emp_k,
                    date=ch.date,
                    status=RosterStatus(ch.status.value),
                    is_locked=True,
                    note="Simulated CELL_EDIT",
                )

        # 7. Rebuild demand and supply matrices
        demand_matrix = build_demand_matrix(
            brand_processes=domain_bps,
            start_date=month_start,
            end_date=month_end,
            rules=domain_rules,
            holidays=domain_holidays,
        )

        supply_matrix = build_supply_matrix(
            employees=domain_employees,
            start_date=month_start,
            end_date=month_end,
            assignments=domain_assignments,
            brand_processes=domain_bps,
            holidays=domain_holidays,
            leaves=domain_leaves,
            locked_cells=(),
        )

        # 8. Re-validate and enrich
        compoff_balances = self.compoff_repo.get_balances_for_employees(emp_ids)
        val_result, _ = validate_roster(
            roster_cells=list(roster_cells_map.values()),
            demand_cells=demand_matrix,
            supply_cells=supply_matrix,
            employees=domain_employees,
            brand_processes=domain_bps,
            assignments=domain_assignments,
            holidays=domain_holidays,
            leaves=domain_leaves,
            initial_compoff_balances=compoff_balances,
            previous_tail_work_days=prev_month_tail,
        )

        enriched_conflicts = enrich_conflicts(
            conflicts=val_result.conflicts,
            employees=domain_employees,
            brand_processes=domain_bps,
            assignments=domain_assignments,
            roster_cells=list(roster_cells_map.values()),
            demand_cells=demand_matrix,
            holidays=domain_holidays,
            leaves=domain_leaves,
        )

        # 9. Compute conflict diff
        existing_conflicts = self.conflict_repo.get_by_period(period_id)
        new_conflicts, resolved_conflicts, unchanged_conflicts = self._diff_conflicts(
            orig_conflicts=existing_conflicts,
            sim_conflicts=enriched_conflicts,
            bp_name_map=bp_name_map,
            bp_proc_map=bp_proc_map,
            emp_name_map=emp_name_map,
        )

        is_feasible = (
            len([c for c in enriched_conflicts if c.severity == DomainConflictSeverity.BLOCKING])
            == 0
        )

        return RosterImpactResponse(
            is_feasible=is_feasible,
            new_conflicts=new_conflicts,
            resolved_conflicts=resolved_conflicts,
            unchanged_conflicts=unchanged_conflicts,
            unchanged=len(unchanged_conflicts),
            net_conflict_change=len(new_conflicts) - len(resolved_conflicts),
            affected_dates=sorted(affected_dates),
        )

    def _diff_conflicts(
        self,
        orig_conflicts: Sequence[DbRosterConflict],
        sim_conflicts: Sequence[Any],
        bp_name_map: dict[str, str],
        bp_proc_map: dict[str, str],
        emp_name_map: dict[str, str],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        def make_sig(
            code: str,
            bp_id: str | None,
            emp_id: str | None,
            d_from: dt.date | None,
            d_to: dt.date | None,
        ) -> tuple:
            return (code, bp_id, emp_id, d_from, d_to)

        orig_map = {
            make_sig(
                c.code,
                str(c.brand_process_id) if c.brand_process_id else None,
                str(c.employee_id) if c.employee_id else None,
                c.date_from,
                c.date_to,
            ): c
            for c in orig_conflicts
        }
        sim_map = {
            make_sig(
                c.code.value if hasattr(c.code, "value") else str(c.code),
                str(c.brand_process_id) if getattr(c, "brand_process_id", None) else None,
                str(c.employee_id) if getattr(c, "employee_id", None) else None,
                getattr(c, "date_from", None) or getattr(c, "date", None),
                getattr(c, "date_to", None) or getattr(c, "date", None),
            ): c
            for c in sim_conflicts
        }

        new_sigs = set(sim_map.keys()) - set(orig_map.keys())
        resolved_sigs = set(orig_map.keys()) - set(sim_map.keys())
        unchanged_sigs = set(sim_map.keys()) & set(orig_map.keys())

        def serialize_domain_conflict(c: Any) -> dict[str, Any]:
            bp_id = str(c.brand_process_id) if getattr(c, "brand_process_id", None) else None
            emp_id = str(c.employee_id) if getattr(c, "employee_id", None) else None
            d_from = getattr(c, "date_from", None) or getattr(c, "date", None)
            d_to = getattr(c, "date_to", None) or getattr(c, "date", None)
            suggestions = []
            if hasattr(c, "suggestions"):
                for s in c.suggestions:
                    kind_val = s.type.value if hasattr(s.type, "value") else str(s.type)
                    suggestions.append(
                        {
                            "kind": kind_val,
                            "type": kind_val,
                            "action": s.action,
                            "description": s.description,
                            "employee_id": s.employee_id,
                            "employee": emp_name_map.get(s.employee_id)
                            if s.employee_id
                            else getattr(s, "employee_name", None),
                            "brand_process_id": s.brand_process_id,
                            "net_effect": {
                                "fixes": getattr(s, "fixes", 1),
                                "opens": getattr(s, "opens", 0),
                            },
                            "net_impact": f"Fixes {getattr(s, 'fixes', 1)} coverage gap, opens {getattr(s, 'opens', 0)}"
                            if getattr(s, "fixes", 0)
                            else getattr(s, "net_impact", ""),
                            "score": getattr(s, "score", 0.0),
                        }
                    )
            code_val = c.code.value if hasattr(c.code, "value") else str(c.code)
            sev_val = c.severity.value if hasattr(c.severity, "value") else str(c.severity)
            root_causes = [
                rc.value if hasattr(rc, "value") else str(rc)
                for rc in getattr(c, "root_causes", ())
            ]
            return {
                "code": code_val,
                "severity": sev_val,
                "brand_process_id": bp_id,
                "brand": bp_name_map.get(bp_id),
                "process": bp_proc_map.get(bp_id),
                "employee_id": emp_id,
                "employee": emp_name_map.get(emp_id),
                "date": d_from.isoformat() if d_from else None,
                "date_from": d_from.isoformat() if d_from else None,
                "date_to": d_to.isoformat() if d_to else None,
                "message": c.message,
                "root_causes": root_causes,
                "suggestions": suggestions,
            }

        def serialize_db_conflict(c: DbRosterConflict) -> dict[str, Any]:
            bp_id = str(c.brand_process_id) if c.brand_process_id else None
            emp_id = str(c.employee_id) if c.employee_id else None
            return {
                "code": c.code,
                "severity": c.severity.value if hasattr(c.severity, "value") else str(c.severity),
                "brand_process_id": bp_id,
                "brand": bp_name_map.get(bp_id),
                "process": bp_proc_map.get(bp_id),
                "employee_id": emp_id,
                "employee": emp_name_map.get(emp_id),
                "date": c.date_from.isoformat() if c.date_from else None,
                "date_from": c.date_from.isoformat() if c.date_from else None,
                "date_to": c.date_to.isoformat() if c.date_to else None,
                "message": c.message,
                "root_causes": list(c.root_causes),
                "suggestions": c.suggestions,
            }

        new_conflicts = [serialize_domain_conflict(sim_map[s]) for s in sorted(new_sigs)]
        resolved_conflicts = [serialize_db_conflict(orig_map[s]) for s in sorted(resolved_sigs)]
        unchanged_conflicts = [
            serialize_domain_conflict(sim_map[s]) for s in sorted(unchanged_sigs)
        ]
        return new_conflicts, resolved_conflicts, unchanged_conflicts

    def update_entries(
        self,
        period_id: uuid.UUID,
        request: RosterEntriesBatchUpdateRequest,
        user_id: uuid.UUID | None = None,
    ) -> RosterEntriesUpdateResponse:
        """Apply validated edits to roster cells, auditing each change and re-validating conflicts."""
        period = self.period_repo.get_by_id(period_id)
        if not period:
            raise NotFoundError(f"Roster period {period_id} not found")

        if period.status == RosterPeriodStatus.ARCHIVED:
            raise BusinessValidationError("Cannot modify an archived roster")

        if period.status == RosterPeriodStatus.PUBLISHED:
            # Editing a published roster creates a new draft version
            highest = self.session.scalars(
                select(RosterPeriod)
                .where(RosterPeriod.month == period.month)
                .order_by(RosterPeriod.version.desc())
            ).first()
            new_version = (highest.version if highest else period.version) + 1
            target_period = RosterPeriod(
                month=period.month,
                version=new_version,
                status=RosterPeriodStatus.DRAFT,
                solver_status=period.solver_status,
                generation_params=dict(period.generation_params),
                parent_period_id=period.id,
                is_stale=False,
                created_by_id=user_id,
            )
            self.session.add(target_period)
            self.session.flush()

            old_entries = self.entry_repo.get_by_period(period.id)
            cloned_entries = [
                DbRosterEntry(
                    roster_period_id=target_period.id,
                    employee_id=e.employee_id,
                    date=e.date,
                    status=e.status,
                    source=e.source,
                    is_locked=e.is_locked,
                    note=e.note,
                )
                for e in old_entries
            ]
            self.entry_repo.bulk_create(cloned_entries)
            self.session.add(
                AuditLog(
                    user_id=user_id,
                    action="ROSTER_CLONE_DRAFT",
                    entity_type="RosterPeriod",
                    entity_id=str(target_period.id),
                    before={"parent_period_id": str(period.id), "parent_version": period.version},
                    after={
                        "new_period_id": str(target_period.id),
                        "version": new_version,
                        "status": "DRAFT",
                    },
                )
            )
            orig_conflicts = list(self.conflict_repo.get_by_period(period.id))
        else:
            target_period = period
            orig_conflicts = list(self.conflict_repo.get_by_period(target_period.id))

        month_start, month_end = parse_month_bounds(target_period.month)
        current_entries = list(self.entry_repo.get_by_period(target_period.id))
        entries_map = {(e.employee_id, e.date): e for e in current_entries}

        updated_entries: list[DbRosterEntry] = []
        affected_dates: set[str] = set()

        for edit in request.entries:
            if not (month_start <= edit.date <= month_end):
                raise BusinessValidationError(
                    f"Date {edit.date} is outside the roster period month ({month_start} to {month_end})"
                )
            db_entry = entries_map.get((edit.employee_id, edit.date))
            if not db_entry:
                raise NotFoundError(
                    f"Roster cell for employee {edit.employee_id} on {edit.date} not found"
                )
            before_snap = {
                "status": db_entry.status.value,
                "source": db_entry.source.value,
                "is_locked": db_entry.is_locked,
                "note": db_entry.note,
            }
            new_status = DbRosterEntryStatus(
                edit.status.value if hasattr(edit.status, "value") else edit.status
            )
            db_entry.status = new_status
            db_entry.source = EntrySource.MANUAL
            if edit.is_locked is not None:
                db_entry.is_locked = edit.is_locked
            note_val = edit.reason or edit.note
            if note_val is not None:
                db_entry.note = note_val

            after_snap = {
                "status": db_entry.status.value,
                "source": db_entry.source.value,
                "is_locked": db_entry.is_locked,
                "note": db_entry.note,
            }
            self.session.add(
                AuditLog(
                    user_id=user_id,
                    action="ROSTER_CELL_EDIT",
                    entity_type="RosterEntry",
                    entity_id=str(db_entry.id),
                    before=before_snap,
                    after=after_snap,
                )
            )
            updated_entries.append(db_entry)
            affected_dates.add(edit.date.isoformat())

        # Build domain inputs for independent re-validation
        db_employees = (
            self.session.scalars(
                select(DbEmployee).options(joinedload(DbEmployee.weekly_off_rules))
            )
            .unique()
            .all()
        )
        emp_ids = [e.id for e in db_employees]
        db_bps = self.session.scalars(
            select(DbBrandProcess)
            .join(DbBrandProcess.brand)
            .join(DbBrandProcess.process)
            .options(
                joinedload(DbBrandProcess.brand),
                joinedload(DbBrandProcess.process),
            )
        ).all()
        bp_ids = [bp.id for bp in db_bps]
        db_assignments = self.session.scalars(
            select(DbAssignment).where(
                DbAssignment.employee_id.in_(emp_ids),
                DbAssignment.brand_process_id.in_(bp_ids),
            )
        ).all()
        db_coverage_rules = self.session.scalars(
            select(DbCoverageRule).where(DbCoverageRule.brand_process_id.in_(bp_ids))
        ).all()
        db_holidays = self.session.scalars(
            select(DbHoliday).where(
                DbHoliday.date >= month_start,
                DbHoliday.date <= month_end,
            )
        ).all()
        db_leaves = self.session.scalars(
            select(DbLeave).where(
                DbLeave.employee_id.in_(emp_ids),
                DbLeave.status == DbLeaveStatus.APPROVED,
                DbLeave.end_date >= month_start,
                DbLeave.start_date <= month_end,
            )
        ).all()

        wo_rules = self.session.scalars(
            select(DbWeeklyOffRule).where(DbWeeklyOffRule.employee_id.in_(emp_ids))
        ).all()
        wo_rules_by_emp = {r.employee_id: r for r in wo_rules}

        prefs = self.session.scalars(
            select(DbEmployeePreference).where(DbEmployeePreference.employee_id.in_(emp_ids))
        ).all()
        prefs_by_emp: dict[uuid.UUID, list[DbEmployeePreference]] = defaultdict(list)
        for p in prefs:
            prefs_by_emp[p.employee_id].append(p)

        domain_employees = []
        for e in db_employees:
            wo_rule = wo_rules_by_emp.get(e.id)
            wo_mode = (
                DomainWeeklyOffMode(wo_rule.mode.value) if wo_rule else DomainWeeklyOffMode.ANY
            )
            fixed_weekdays = tuple(wo_rule.weekdays) if wo_rule and wo_rule.weekdays else ()

            emp_p_list = prefs_by_emp.get(e.id, [])
            pref_weekdays: list[int] = []
            pref_dates: list[dt.date] = []
            for p in emp_p_list:
                if p.kind.value == "PREFERRED_OFF_WEEKDAY" and "weekday" in p.value:
                    pref_weekdays.append(int(p.value["weekday"]))
                elif p.kind.value == "PREFERRED_OFF_DATE" and "date" in p.value:
                    with contextlib.suppress(Exception):
                        pref_dates.append(dt.date.fromisoformat(str(p.value["date"])))

            domain_employees.append(
                DomainEmployee(
                    id=str(e.id),
                    code=e.code,
                    full_name=e.full_name,
                    pod_id=str(e.pod_id),
                    is_floater=e.is_floater,
                    weekly_off_count=e.weekly_off_count,
                    max_consecutive_days=e.max_consecutive_days,
                    max_concurrent_processes=e.max_concurrent_processes,
                    weekly_off_mode=wo_mode,
                    fixed_weekly_off_weekdays=fixed_weekdays,
                    preferred_weekly_off_weekdays=tuple(pref_weekdays),
                    preferred_off_dates=tuple(pref_dates),
                )
            )
        domain_bps = [
            DomainBrandProcess(
                id=str(bp.id),
                brand_id=str(bp.brand_id),
                brand_name=bp.brand.name if bp.brand else "",
                process_id=str(bp.process_id),
                process_name=bp.process.name if bp.process else "",
                calendar_type=DomainCalendarType(bp.calendar_type.value),
                min_coverage_default=bp.min_coverage_default,
            )
            for bp in db_bps
        ]
        domain_assignments = [
            DomainAssignment(
                employee_id=str(a.employee_id),
                brand_process_id=str(a.brand_process_id),
                type=DomainAssignmentType(a.type.value),
            )
            for a in db_assignments
        ]
        domain_rules = [
            DomainCoverageRule(
                brand_process_id=str(cr.brand_process_id),
                weekday=cr.weekday,
                specific_date=cr.specific_date,
                min_staff=cr.min_staff,
                reason=cr.reason or "",
            )
            for cr in db_coverage_rules
        ]
        domain_holidays = [
            DomainHoliday(
                date=h.date,
                name=h.name,
                brand_id=str(h.brand_id) if h.brand_id else None,
            )
            for h in db_holidays
        ]
        domain_leaves = [
            DomainEmployeeLeave(
                employee_id=str(lv.employee_id),
                start_date=lv.start_date,
                end_date=lv.end_date,
                type=DomainLeaveType(lv.type.value)
                if hasattr(lv.type, "value")
                else DomainLeaveType.PLANNED,
            )
            for lv in db_leaves
        ]

        prev_month_tail: dict[str, int] = {}
        prev_month_start = (month_start - dt.timedelta(days=1)).replace(day=1)
        prev_period = (
            self.period_repo.get_published_period(prev_month_start)
            or self.session.scalars(
                select(RosterPeriod)
                .where(RosterPeriod.month == prev_month_start)
                .order_by(RosterPeriod.version.desc())
            ).first()
        )
        if prev_period:
            prev_entries = self.entry_repo.get_by_period(
                period_id=prev_period.id,
                date_from=month_start - dt.timedelta(days=6),
                date_to=month_start - dt.timedelta(days=1),
            )
            entries_by_emp_date = {(e.employee_id, e.date): e for e in prev_entries}
            for eid in emp_ids:
                streak = 0
                for back in range(1, 7):
                    check_d = month_start - dt.timedelta(days=back)
                    entry = entries_by_emp_date.get((eid, check_d))
                    if entry and entry.status in (
                        DbRosterEntryStatus.WORK,
                        DbRosterEntryStatus.HOLIDAY_WORK,
                    ):
                        streak += 1
                    else:
                        break
                prev_month_tail[str(eid)] = streak

        demand_matrix = build_demand_matrix(
            brand_processes=domain_bps,
            start_date=month_start,
            end_date=month_end,
            rules=domain_rules,
            holidays=domain_holidays,
        )
        supply_matrix = build_supply_matrix(
            employees=domain_employees,
            start_date=month_start,
            end_date=month_end,
            assignments=domain_assignments,
            brand_processes=domain_bps,
            holidays=domain_holidays,
            leaves=domain_leaves,
            locked_cells=(),
        )

        domain_cells = [
            RosterCell(
                employee_id=str(e.employee_id),
                date=e.date,
                status=RosterStatus(e.status.value),
                is_locked=e.is_locked,
                note=e.note or "",
            )
            for e in entries_map.values()
        ]

        compoff_balances = self.compoff_repo.get_balances_for_employees(emp_ids)
        val_result, _ = validate_roster(
            roster_cells=domain_cells,
            demand_cells=demand_matrix,
            supply_cells=supply_matrix,
            employees=domain_employees,
            brand_processes=domain_bps,
            assignments=domain_assignments,
            holidays=domain_holidays,
            leaves=domain_leaves,
            initial_compoff_balances=compoff_balances,
            previous_tail_work_days=prev_month_tail,
        )
        enriched_conflicts = enrich_conflicts(
            conflicts=val_result.conflicts,
            employees=domain_employees,
            brand_processes=domain_bps,
            assignments=domain_assignments,
            roster_cells=domain_cells,
            demand_cells=demand_matrix,
            holidays=domain_holidays,
            leaves=domain_leaves,
        )

        self.conflict_repo.delete_by_period(target_period.id)
        emp_name_map = {str(e.id): e.full_name for e in db_employees}
        bp_name_map = {str(bp.id): bp.brand.name for bp in db_bps}
        bp_proc_map = {str(bp.id): bp.process.name for bp in db_bps}

        new_db_conflicts = [
            DbRosterConflict(
                id=uuid.uuid4(),
                roster_period_id=target_period.id,
                code=ec.code.value,
                severity=DbConflictSeverity(ec.severity.value),
                brand_process_id=uuid.UUID(ec.brand_process_id) if ec.brand_process_id else None,
                employee_id=uuid.UUID(ec.employee_id) if ec.employee_id else None,
                date_from=ec.date_from,
                date_to=ec.date_to,
                root_causes=[
                    rc.value if hasattr(rc, "value") else str(rc) for rc in ec.root_causes
                ],
                message=ec.message,
                suggestions=[
                    {
                        "kind": s.type.value,
                        "type": s.type.value,
                        "action": s.action,
                        "description": s.description,
                        "employee_id": s.employee_id,
                        "employee": emp_name_map.get(s.employee_id) if s.employee_id else None,
                        "brand_process_id": s.brand_process_id,
                        "net_effect": {
                            "fixes": getattr(s, "fixes", 1),
                            "opens": getattr(s, "opens", 0),
                        },
                        "net_impact": f"Fixes {getattr(s, 'fixes', 1)} coverage gap, opens {getattr(s, 'opens', 0)}"
                        if getattr(s, "fixes", 0)
                        else getattr(s, "net_impact", ""),
                        "score": getattr(s, "score", 0.0),
                    }
                    for s in ec.suggestions
                ],
            )
            for ec in enriched_conflicts
        ]
        self.conflict_repo.bulk_create(new_db_conflicts)

        target_period.is_stale = False
        self.session.flush()

        new_conflicts, resolved_conflicts, unchanged_conflicts = self._diff_conflicts(
            orig_conflicts=orig_conflicts,
            sim_conflicts=enriched_conflicts,
            bp_name_map=bp_name_map,
            bp_proc_map=bp_proc_map,
            emp_name_map=emp_name_map,
        )

        for c in new_conflicts + resolved_conflicts:
            if c.get("date"):
                affected_dates.add(c["date"])

        self.session.commit()

        return RosterEntriesUpdateResponse(
            roster_period_id=target_period.id,
            version=target_period.version,
            status=target_period.status,
            updated_entries=[RosterEntryRead.model_validate(e) for e in updated_entries],
            new_conflicts=new_conflicts,
            resolved_conflicts=resolved_conflicts,
            unchanged_conflicts=unchanged_conflicts,
            unchanged=len(unchanged_conflicts),
            net_conflict_change=len(new_conflicts) - len(resolved_conflicts),
            affected_dates=sorted(affected_dates),
        )

    def lock_cells(
        self,
        period_id: uuid.UUID,
        request: RosterEntriesLockRequest,
        user_id: uuid.UUID | None = None,
    ) -> RosterEntriesLockResponse:
        """Lock or unlock schedule cells, auditing each change."""
        period = self.period_repo.get_by_id(period_id)
        if not period:
            raise NotFoundError(f"Roster period {period_id} not found")

        if period.status == RosterPeriodStatus.ARCHIVED:
            raise BusinessValidationError("Cannot modify an archived roster")

        if period.status == RosterPeriodStatus.PUBLISHED:
            # Editing a published roster creates a new draft version
            highest = self.session.scalars(
                select(RosterPeriod)
                .where(RosterPeriod.month == period.month)
                .order_by(RosterPeriod.version.desc())
            ).first()
            new_version = (highest.version if highest else period.version) + 1
            target_period = RosterPeriod(
                month=period.month,
                version=new_version,
                status=RosterPeriodStatus.DRAFT,
                solver_status=period.solver_status,
                generation_params=dict(period.generation_params),
                parent_period_id=period.id,
                is_stale=False,
                created_by_id=user_id,
            )
            self.session.add(target_period)
            self.session.flush()

            old_entries = self.entry_repo.get_by_period(period.id)
            cloned_entries = [
                DbRosterEntry(
                    roster_period_id=target_period.id,
                    employee_id=e.employee_id,
                    date=e.date,
                    status=e.status,
                    source=e.source,
                    is_locked=e.is_locked,
                    note=e.note,
                )
                for e in old_entries
            ]
            self.entry_repo.bulk_create(cloned_entries)
            self.session.add(
                AuditLog(
                    user_id=user_id,
                    action="ROSTER_CLONE_DRAFT",
                    entity_type="RosterPeriod",
                    entity_id=str(target_period.id),
                    before={"parent_period_id": str(period.id), "parent_version": period.version},
                    after={
                        "new_period_id": str(target_period.id),
                        "version": new_version,
                        "status": "DRAFT",
                    },
                )
            )
        else:
            target_period = period

        targets: list[tuple[uuid.UUID, dt.date, bool]] = []
        if request.cells:
            for c in request.cells:
                targets.append((c.employee_id, c.date, c.is_locked))
        elif request.employee_ids and request.dates:
            lock_val = True if request.is_locked is None else request.is_locked
            for eid in request.employee_ids:
                for d in request.dates:
                    targets.append((eid, d, lock_val))
        elif request.employee_ids:
            lock_val = True if request.is_locked is None else request.is_locked
            month_start, month_end = parse_month_bounds(target_period.month)
            cur = month_start
            while cur <= month_end:
                for eid in request.employee_ids:
                    targets.append((eid, cur, lock_val))
                cur += dt.timedelta(days=1)
        elif request.dates:
            lock_val = True if request.is_locked is None else request.is_locked
            matched_entries = self.session.scalars(
                select(DbRosterEntry).where(
                    DbRosterEntry.roster_period_id == target_period.id,
                    DbRosterEntry.date.in_(request.dates),
                )
            ).all()
            for me in matched_entries:
                targets.append((me.employee_id, me.date, lock_val))

        entries_map = {
            (e.employee_id, e.date): e for e in self.entry_repo.get_by_period(target_period.id)
        }
        locked_count = 0
        unlocked_count = 0
        updated_entries: list[DbRosterEntry] = []

        for eid, d, is_locked in targets:
            db_entry = entries_map.get((eid, d))
            if not db_entry:
                continue
            if db_entry.is_locked != is_locked:
                before_snap = {"is_locked": db_entry.is_locked, "source": db_entry.source.value}
                db_entry.is_locked = is_locked
                if is_locked:
                    db_entry.source = EntrySource.LOCKED_FIXED
                    locked_count += 1
                else:
                    unlocked_count += 1
                after_snap = {"is_locked": db_entry.is_locked, "source": db_entry.source.value}
                self.session.add(
                    AuditLog(
                        user_id=user_id,
                        action="ROSTER_CELL_LOCK" if is_locked else "ROSTER_CELL_UNLOCK",
                        entity_type="RosterEntry",
                        entity_id=str(db_entry.id),
                        before=before_snap,
                        after=after_snap,
                    )
                )
                updated_entries.append(db_entry)

        self.session.commit()
        return RosterEntriesLockResponse(
            roster_period_id=target_period.id,
            version=target_period.version,
            locked_count=locked_count,
            unlocked_count=unlocked_count,
            updated_entries=[RosterEntryRead.model_validate(e) for e in updated_entries],
        )

    def flag_rosters_stale(
        self,
        dates: Sequence[dt.date],
        user_id: uuid.UUID | None = None,
    ) -> list[uuid.UUID]:
        """Flag any draft or published roster covering any of the dates as stale."""
        affected_period_ids: list[uuid.UUID] = []
        months = {d.replace(day=1) for d in dates}
        for m in months:
            periods = self.session.scalars(
                select(RosterPeriod).where(
                    RosterPeriod.month == m,
                    RosterPeriod.status.in_(
                        [RosterPeriodStatus.DRAFT, RosterPeriodStatus.PUBLISHED]
                    ),
                )
            ).all()
            for p in periods:
                if not p.is_stale:
                    p.is_stale = True
                    self.session.add(
                        AuditLog(
                            user_id=user_id,
                            action="ROSTER_FLAG_STALE",
                            entity_type="RosterPeriod",
                            entity_id=str(p.id),
                            before={"is_stale": False},
                            after={"is_stale": True, "dates": [d.isoformat() for d in dates]},
                        )
                    )
                    affected_period_ids.append(p.id)
        if affected_period_ids:
            self.session.commit()
        return affected_period_ids

    def get_suggestions(
        self,
        period_id: uuid.UUID,
        conflict_id: uuid.UUID | None = None,
        brand_process_id: uuid.UUID | None = None,
        target_date: dt.date | None = None,
        employee_id: uuid.UUID | None = None,
    ) -> list[RosterSuggestionItem]:
        """Fetch ranked, actionable resolution suggestions for roster gaps."""
        period = self.period_repo.get_by_id(period_id)
        if not period:
            raise NotFoundError(f"Roster period {period_id} not found")

        if conflict_id:
            c = self.session.get(DbRosterConflict, conflict_id)
            if not c or c.roster_period_id != period_id:
                raise NotFoundError(
                    f"Conflict {conflict_id} not found in roster period {period_id}"
                )
            target_conflicts = [c]
        else:
            target_conflicts = list(
                self.conflict_repo.get_by_period(
                    period_id=period_id,
                    severity="BLOCKING",
                    brand_process_id=brand_process_id,
                    target_date=target_date,
                    employee_id=employee_id,
                )
            )

        db_employees = self.session.scalars(select(DbEmployee)).all()
        emp_code_map = {str(e.id): e.code for e in db_employees}
        emp_name_map = {str(e.id): e.full_name for e in db_employees}

        db_bps = self.session.scalars(
            select(DbBrandProcess)
            .join(DbBrandProcess.brand)
            .join(DbBrandProcess.process)
            .options(
                joinedload(DbBrandProcess.brand),
                joinedload(DbBrandProcess.process),
            )
        ).all()
        bp_brand_map = {str(bp.id): bp.brand.name for bp in db_bps}
        bp_proc_map = {str(bp.id): bp.process.name for bp in db_bps}

        items: list[RosterSuggestionItem] = []
        seen_keys: set[tuple[str, str | None, str | None, str | None]] = set()

        for c in target_conflicts:
            c_bp_id = str(c.brand_process_id) if c.brand_process_id else None
            c_date = c.date_from

            for s in c.suggestions:
                s_type = s.get("type") or s.get("kind") or "ASSIGN_BACKUP"
                s_emp_id = s.get("employee_id")
                s_bp_id = s.get("brand_process_id") or c_bp_id
                s_target_date = s.get("target_date") or (c_date.isoformat() if c_date else None)
                s_source_date = s.get("source_date")

                dedup_key = (s_type, s_emp_id, s_bp_id, s_target_date)
                if dedup_key in seen_keys:
                    continue
                seen_keys.add(dedup_key)

                emp_uuid = uuid.UUID(s_emp_id) if s_emp_id else None
                bp_uuid = uuid.UUID(s_bp_id) if s_bp_id else None
                target_d = dt.date.fromisoformat(s_target_date) if s_target_date else c_date
                source_d = dt.date.fromisoformat(s_source_date) if s_source_date else None

                brand_name = bp_brand_map.get(s_bp_id) if s_bp_id else None
                proc_name = bp_proc_map.get(s_bp_id) if s_bp_id else None
                emp_name = s.get("employee") or (emp_name_map.get(s_emp_id) if s_emp_id else None)
                emp_code = emp_code_map.get(s_emp_id) if s_emp_id else None

                net_effect_data = s.get("net_effect", {})
                net_effect = SuggestionNetEffect(
                    fixes=net_effect_data.get("fixes", 1),
                    opens=net_effect_data.get("opens", 0),
                )

                apply_payload: dict[str, Any] = {}
                if s_type == "ASSIGN_BACKUP" and emp_uuid and target_d:
                    apply_payload = {
                        "action": "ASSIGN_BACKUP",
                        "employee_id": str(emp_uuid),
                        "brand_process_id": str(bp_uuid) if bp_uuid else None,
                        "date": target_d.isoformat(),
                        "cell_edits": [
                            {
                                "employee_id": str(emp_uuid),
                                "date": target_d.isoformat(),
                                "status": "WORK",
                                "reason": f"Backup coverage for {brand_name or 'brand'} - {proc_name or 'process'}",
                            }
                        ],
                    }
                elif s_type == "SWAP_WEEKLY_OFF" and emp_uuid and target_d and source_d:
                    apply_payload = {
                        "action": "SWAP_WEEKLY_OFF",
                        "employee_id": str(emp_uuid),
                        "brand_process_id": str(bp_uuid) if bp_uuid else None,
                        "entries": [
                            {
                                "employee_id": str(emp_uuid),
                                "date": target_d.isoformat(),
                                "status": "WORK",
                                "reason": f"Weekly off swap to cover {brand_name or 'brand'}",
                            },
                            {
                                "employee_id": str(emp_uuid),
                                "date": source_d.isoformat(),
                                "status": "WEEKLY_OFF",
                                "reason": "Weekly off swap (alternate date)",
                            },
                        ],
                    }
                elif s_type == "SHIFT_LEAVE" and emp_uuid and target_d:
                    apply_payload = {
                        "action": "SHIFT_LEAVE",
                        "employee_id": str(emp_uuid),
                        "brand_process_id": str(bp_uuid) if bp_uuid else None,
                        "date": target_d.isoformat(),
                        "note": "Requires employee consent and leave reschedule",
                    }

                items.append(
                    RosterSuggestionItem(
                        type=s_type,
                        kind=s_type,
                        action=s.get("action", f"Suggestion for {emp_name}"),
                        description=s.get("description", ""),
                        employee_id=emp_uuid,
                        employee_name=emp_name,
                        employee_code=emp_code,
                        brand_process_id=bp_uuid,
                        brand_name=brand_name,
                        process_name=proc_name,
                        target_date=target_d,
                        source_date=source_d,
                        score=float(s.get("score", 0.0)),
                        net_effect=net_effect,
                        net_impact=s.get(
                            "net_impact",
                            f"Fixes {net_effect.fixes} coverage gap, opens {net_effect.opens}",
                        ),
                        apply_payload=apply_payload,
                    )
                )

        items.sort(key=lambda item: item.score, reverse=True)
        return items

    def acknowledge_conflict(
        self,
        period_id: uuid.UUID,
        request: RosterAcknowledgeRequest,
        user_id: uuid.UUID | None = None,
    ) -> RosterConflictRead:
        """Acknowledge a BLOCKING conflict with an ops manager logged reason."""
        period = self.period_repo.get_by_id(period_id)
        if not period:
            raise NotFoundError(f"Roster period '{period_id}' not found.")

        conflict = self.conflict_repo.get_by_id(request.conflict_id)
        if not conflict or conflict.roster_period_id != period_id:
            raise NotFoundError(
                f"Conflict '{request.conflict_id}' not found for roster period '{period_id}'."
            )

        before_state = {
            "is_acknowledged": conflict.is_acknowledged,
            "acknowledged_reason": conflict.acknowledged_reason,
            "acknowledged_by_id": str(conflict.acknowledged_by_id)
            if conflict.acknowledged_by_id
            else None,
        }

        conflict.is_acknowledged = True
        conflict.acknowledged_by_id = user_id
        conflict.acknowledged_reason = request.reason
        self.session.add(conflict)

        self.session.add(
            AuditLog(
                user_id=user_id,
                action="ROSTER_CONFLICT_ACKNOWLEDGE",
                entity_type="RosterConflict",
                entity_id=str(conflict.id),
                before=before_state,
                after={
                    "is_acknowledged": True,
                    "acknowledged_reason": request.reason,
                    "acknowledged_by_id": str(user_id) if user_id else None,
                    "period_id": str(period_id),
                },
            )
        )
        self.session.flush()

        read = RosterConflictRead.model_validate(conflict)
        if conflict.brand_process and conflict.brand_process.brand:
            read.brand_name = conflict.brand_process.brand.name
        if conflict.brand_process and conflict.brand_process.process:
            read.process_name = conflict.brand_process.process.name
            read.process_code = conflict.brand_process.process.code
        if conflict.employee:
            read.employee_name = conflict.employee.full_name
            read.employee_code = conflict.employee.code
        return read

    def publish_roster(
        self,
        period_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> RosterPeriodRead:
        """Publish a draft roster if zero unacknowledged BLOCKING conflicts exist (A-13)."""
        period = self.period_repo.get_by_id(period_id)
        if not period:
            raise NotFoundError(f"Roster period '{period_id}' not found.")

        if period.status == RosterPeriodStatus.PUBLISHED:
            raise ConflictError(f"Roster period '{period_id}' is already published.")
        if period.status == RosterPeriodStatus.ARCHIVED:
            raise BusinessValidationError("Cannot publish an archived roster.")

        # Check for unacknowledged BLOCKING conflicts
        stmt = (
            select(DbRosterConflict)
            .where(
                DbRosterConflict.roster_period_id == period_id,
                DbRosterConflict.severity == DbConflictSeverity.BLOCKING,
                DbRosterConflict.is_acknowledged.is_(False),
            )
            .order_by(DbRosterConflict.date_from, DbRosterConflict.code)
        )
        unack_blocking = self.session.scalars(stmt).all()

        if unack_blocking:
            details = [
                {
                    "conflict_id": str(c.id),
                    "code": c.code,
                    "summary": c.message,
                    "date_from": c.date_from.isoformat(),
                    "date_to": c.date_to.isoformat(),
                }
                for c in unack_blocking
            ]
            raise RosterBlockedError(
                message=f"{len(unack_blocking)} blocking conflicts remain",
                details=details,
            )

        # Archive any previously published roster for the same month
        prev_published = self.session.scalars(
            select(RosterPeriod).where(
                RosterPeriod.month == period.month,
                RosterPeriod.status == RosterPeriodStatus.PUBLISHED,
                RosterPeriod.id != period.id,
            )
        ).all()
        for p in prev_published:
            p.status = RosterPeriodStatus.ARCHIVED
            self.session.add(p)
            self.session.add(
                AuditLog(
                    user_id=user_id,
                    action="ROSTER_ARCHIVE_SUPERSEDED",
                    entity_type="RosterPeriod",
                    entity_id=str(p.id),
                    before={"status": "PUBLISHED"},
                    after={"status": "ARCHIVED", "superseded_by_id": str(period.id)},
                )
            )
        # Flush the ARCHIVED status first to prevent partial unique index collision on (month, status='PUBLISHED')
        if prev_published:
            self.session.flush()

        before_state = {
            "status": period.status.value,
            "is_stale": period.is_stale,
            "published_at": period.published_at.isoformat() if period.published_at else None,
        }

        period.status = RosterPeriodStatus.PUBLISHED
        period.published_at = dt.datetime.now(dt.UTC)
        period.is_stale = False
        self.session.add(period)

        # Accrue comp-off credits for holiday work in this period
        from app.services.compoff import CompOffService

        compoff_svc = CompOffService(self.session)
        compoff_svc.accrue_holiday_work_credits(period.id, actor_id=user_id)

        # Audit log entry
        self.session.add(
            AuditLog(
                user_id=user_id,
                action="ROSTER_PUBLISH",
                entity_type="RosterPeriod",
                entity_id=str(period.id),
                before=before_state,
                after={
                    "status": "PUBLISHED",
                    "published_at": period.published_at.isoformat(),
                    "month": str(period.month),
                    "version": period.version,
                },
            )
        )
        self.session.flush()

        return self.get_roster_period(period.id)

    def clone_roster(
        self,
        period_id: uuid.UUID,
        request: RosterCloneRequest | None = None,
        user_id: uuid.UUID | None = None,
    ) -> RosterPeriodRead:
        """Clone an existing roster period (draft or published) into a new draft version n+1."""
        parent = self.period_repo.get_by_id(period_id)
        if not parent:
            raise NotFoundError(f"Roster period '{period_id}' not found.")

        highest_version = (
            self.session.scalar(
                select(func.max(RosterPeriod.version)).where(RosterPeriod.month == parent.month)
            )
            or parent.version
        )
        next_version = highest_version + 1

        new_period = RosterPeriod(
            id=uuid.uuid4(),
            month=parent.month,
            version=next_version,
            status=RosterPeriodStatus.DRAFT,
            solver_status=parent.solver_status,
            generation_params={
                **(parent.generation_params or {}),
                "cloned_from_id": str(parent.id),
                "cloned_from_version": parent.version,
                "clone_note": request.note if request else None,
            },
            created_by_id=user_id,
            is_stale=False,
        )
        self.session.add(new_period)
        self.session.flush()

        # Clone all entries
        parent_entries = self.entry_repo.get_by_period(parent.id)
        new_entries = [
            DbRosterEntry(
                id=uuid.uuid4(),
                roster_period_id=new_period.id,
                employee_id=e.employee_id,
                date=e.date,
                status=e.status,
                source=e.source,
                is_locked=e.is_locked,
                note=e.note,
            )
            for e in parent_entries
        ]
        self.entry_repo.bulk_create(new_entries)

        # Clone conflicts
        parent_conflicts = self.conflict_repo.get_by_period(parent.id)
        new_conflicts = [
            DbRosterConflict(
                id=uuid.uuid4(),
                roster_period_id=new_period.id,
                code=c.code,
                severity=c.severity,
                brand_process_id=c.brand_process_id,
                employee_id=c.employee_id,
                date_from=c.date_from,
                date_to=c.date_to,
                root_causes=list(c.root_causes or []),
                message=c.message,
                suggestions=list(c.suggestions or []),
                is_acknowledged=c.is_acknowledged,
                acknowledged_by_id=c.acknowledged_by_id,
                acknowledged_reason=c.acknowledged_reason,
            )
            for c in parent_conflicts
        ]
        self.conflict_repo.bulk_create(new_conflicts)

        # Audit log entry
        self.session.add(
            AuditLog(
                user_id=user_id,
                action="ROSTER_CLONE",
                entity_type="RosterPeriod",
                entity_id=str(new_period.id),
                before=None,
                after={
                    "parent_period_id": str(parent.id),
                    "parent_version": parent.version,
                    "new_period_id": str(new_period.id),
                    "version": next_version,
                    "entries_count": len(new_entries),
                    "conflicts_count": len(new_conflicts),
                },
            )
        )
        self.session.flush()

        return self.get_roster_period(new_period.id)

    def repair_roster(
        self,
        period_id: uuid.UUID,
        request: RosterRepairRequest,
        user_id: uuid.UUID | None = None,
    ) -> RosterRepairResponse:
        """Execute local repair around impacted dates/employees with unaffected cells locked."""
        period = self.period_repo.get_by_id(period_id)
        if not period:
            raise NotFoundError(f"Roster period '{period_id}' not found.")

        month_start, month_end = parse_month_bounds(period.month)

        # 1. Determine impacted dates
        impacted_dates: set[dt.date] = set()
        target_conflict: DbRosterConflict | None = None
        if request.conflict_id:
            target_conflict = self.conflict_repo.get_by_id(request.conflict_id)
            if not target_conflict or target_conflict.roster_period_id != period_id:
                raise NotFoundError(
                    f"Conflict '{request.conflict_id}' not found for roster period '{period_id}'."
                )
            cur = target_conflict.date_from
            while cur <= target_conflict.date_to:
                impacted_dates.add(cur)
                cur += dt.timedelta(days=1)
        if request.dates:
            impacted_dates.update(request.dates)
        if request.date_from and request.date_to:
            cur = request.date_from
            while cur <= request.date_to:
                impacted_dates.add(cur)
                cur += dt.timedelta(days=1)

        # If no specific dates given, derive from all active conflicts in this period
        if not impacted_dates:
            for c in period.conflicts:
                cur = c.date_from
                while cur <= c.date_to:
                    impacted_dates.add(cur)
                    cur += dt.timedelta(days=1)

        # Clamp to month bounds
        impacted_dates = {d for d in impacted_dates if month_start <= d <= month_end}
        if not impacted_dates:
            cur = month_start
            while cur <= month_end:
                impacted_dates.add(cur)
                cur += dt.timedelta(days=1)

        # 2. Determine eligible employees
        eligible_emp_ids: set[uuid.UUID] = set()
        if request.employee_ids:
            eligible_emp_ids.update(request.employee_ids)
        if target_conflict:
            if target_conflict.employee_id:
                eligible_emp_ids.add(target_conflict.employee_id)
            if target_conflict.brand_process_id:
                asgn_stmt = select(DbAssignment).where(
                    DbAssignment.brand_process_id == target_conflict.brand_process_id,
                    (DbAssignment.valid_from.is_(None) | (DbAssignment.valid_from <= month_end)),
                    (DbAssignment.valid_to.is_(None) | (DbAssignment.valid_to >= month_start)),
                )
                for a in self.session.scalars(asgn_stmt).all():
                    eligible_emp_ids.add(a.employee_id)
        if request.brand_process_ids:
            asgn_stmt = select(DbAssignment).where(
                DbAssignment.brand_process_id.in_(request.brand_process_ids),
                (DbAssignment.valid_from.is_(None) | (DbAssignment.valid_from <= month_end)),
                (DbAssignment.valid_to.is_(None) | (DbAssignment.valid_to >= month_start)),
            )
            for a in self.session.scalars(asgn_stmt).all():
                eligible_emp_ids.add(a.employee_id)

        # 3. Load baseline domain entities
        db_employees = self.session.scalars(
            select(DbEmployee).where(DbEmployee.is_active.is_(True)).order_by(DbEmployee.code)
        ).all()
        emp_ids = [e.id for e in db_employees]
        emp_name_map = {str(e.id): e.full_name for e in db_employees}

        bp_stmt = select(DbBrandProcess).join(DbBrandProcess.brand).order_by(DbBrand.name)
        db_bps = self.session.scalars(bp_stmt).all()
        bp_name_map = {str(bp.id): bp.brand.name for bp in db_bps if bp.brand}
        bp_proc_map = {
            str(bp.id): (bp.process.name, bp.process.code) for bp in db_bps if bp.process
        }

        wor_stmt = select(DbWeeklyOffRule).where(
            DbWeeklyOffRule.employee_id.in_(emp_ids),
        )
        db_wo_rules = self.session.scalars(wor_stmt).all()
        wo_rules_by_emp = {r.employee_id: r for r in db_wo_rules}

        prefs = self.session.scalars(
            select(DbEmployeePreference).where(DbEmployeePreference.employee_id.in_(emp_ids))
        ).all()
        prefs_by_emp: dict[uuid.UUID, list[DbEmployeePreference]] = {}
        for p in prefs:
            prefs_by_emp.setdefault(p.employee_id, []).append(p)

        domain_employees: list[DomainEmployee] = []
        for e in db_employees:
            wo_rule = wo_rules_by_emp.get(e.id)
            wo_mode = (
                DomainWeeklyOffMode(wo_rule.mode.value) if wo_rule else DomainWeeklyOffMode.ANY
            )
            fixed_weekdays = tuple(wo_rule.weekdays) if wo_rule and wo_rule.weekdays else ()

            emp_p_list = prefs_by_emp.get(e.id, [])
            pref_weekdays: list[int] = []
            pref_dates: list[dt.date] = []
            for p in emp_p_list:
                if p.kind.value == "PREFERRED_OFF_WEEKDAY" and "weekday" in p.value:
                    pref_weekdays.append(int(p.value["weekday"]))
                elif p.kind.value == "PREFERRED_OFF_DATE" and "date" in p.value:
                    with contextlib.suppress(Exception):
                        pref_dates.append(dt.date.fromisoformat(str(p.value["date"])))

            domain_employees.append(
                DomainEmployee(
                    id=str(e.id),
                    code=e.code,
                    full_name=e.full_name,
                    pod_id=str(e.pod_id) if e.pod_id else None,
                    is_floater=e.is_floater,
                    weekly_off_count=e.weekly_off_count,
                    max_consecutive_days=e.max_consecutive_days,
                    max_concurrent_processes=e.max_concurrent_processes,
                    weekly_off_mode=wo_mode,
                    fixed_weekly_off_weekdays=fixed_weekdays,
                    preferred_weekly_off_weekdays=tuple(pref_weekdays),
                    preferred_off_dates=tuple(pref_dates),
                )
            )

        domain_bps: list[DomainBrandProcess] = [
            DomainBrandProcess(
                id=str(bp.id),
                brand_id=str(bp.brand_id),
                brand_name=bp.brand.name if bp.brand else "",
                process_id=str(bp.process_id),
                process_name=bp.process.name if bp.process else "",
                calendar_type=DomainCalendarType(bp.calendar_type.value),
                min_coverage_default=bp.min_coverage_default,
            )
            for bp in db_bps
        ]

        asgn_stmt = select(DbAssignment).where(
            DbAssignment.employee_id.in_(emp_ids),
            DbAssignment.brand_process_id.in_([bp.id for bp in db_bps]),
            (DbAssignment.valid_from.is_(None) | (DbAssignment.valid_from <= month_end)),
            (DbAssignment.valid_to.is_(None) | (DbAssignment.valid_to >= month_start)),
        )
        db_assignments = self.session.scalars(asgn_stmt).all()
        domain_assignments = [
            DomainAssignment(
                employee_id=str(a.employee_id),
                brand_process_id=str(a.brand_process_id),
                type=DomainAssignmentType(a.type.value),
            )
            for a in db_assignments
        ]

        db_rules = self.session.scalars(
            select(DbCoverageRule).where(DbCoverageRule.is_active.is_(True))
        ).all()
        domain_rules = [
            DomainCoverageRule(
                brand_process_id=str(r.brand_process_id),
                weekday=r.weekday,
                specific_date=r.specific_date,
                min_staff=r.min_staff,
                reason=r.reason or "",
            )
            for r in db_rules
        ]

        db_holidays = self.session.scalars(
            select(DbHoliday).where(
                DbHoliday.is_active.is_(True),
                DbHoliday.date >= month_start,
                DbHoliday.date <= month_end,
            )
        ).all()
        domain_holidays = [
            DomainHoliday(
                name=h.name,
                date=h.date,
                brand_id=str(h.brand_id) if h.brand_id else None,
            )
            for h in db_holidays
        ]
        db_leaves = self.session.scalars(
            select(DbLeave).where(
                DbLeave.status == DbLeaveStatus.APPROVED,
                DbLeave.start_date <= month_end,
                DbLeave.end_date >= month_start,
            )
        ).all()
        domain_leaves = [
            DomainEmployeeLeave(
                employee_id=str(lv.employee_id),
                start_date=lv.start_date,
                end_date=lv.end_date,
                type=DomainLeaveType(lv.type.value),
            )
            for lv in db_leaves
        ]

        prev_month_tail: dict[str, int] = {}
        prev_month_start = (month_start - dt.timedelta(days=1)).replace(day=1)
        prev_period = (
            self.period_repo.get_published_period(prev_month_start)
            or self.session.scalars(
                select(RosterPeriod)
                .where(RosterPeriod.month == prev_month_start)
                .order_by(RosterPeriod.version.desc())
            ).first()
        )
        if prev_period:
            prev_entries = self.entry_repo.get_by_period(prev_period.id)
            prev_map: dict[tuple[uuid.UUID, dt.date], DbRosterEntry] = {
                (e.employee_id, e.date): e for e in prev_entries
            }
            prev_end = month_start - dt.timedelta(days=1)
            for eid in emp_ids:
                streak = 0
                for day_offset in range(6):
                    check_d = prev_end - dt.timedelta(days=day_offset)
                    ent = prev_map.get((eid, check_d))
                    if ent and ent.status in (
                        DbRosterEntryStatus.WORK,
                        DbRosterEntryStatus.HOLIDAY_WORK,
                    ):
                        streak += 1
                    else:
                        break
                prev_month_tail[str(eid)] = streak

        compoff_balances = self.compoff_repo.get_balances_for_employees(emp_ids)

        demand_matrix = build_demand_matrix(
            brand_processes=domain_bps,
            start_date=month_start,
            end_date=month_end,
            rules=domain_rules,
            holidays=domain_holidays,
        )

        # 4. Load current roster entries
        db_entries = self.entry_repo.get_by_period(period_id)
        current_cells = [
            RosterCell(
                employee_id=str(e.employee_id),
                date=e.date,
                status=RosterStatus(e.status.value),
                is_locked=e.is_locked,
                note=e.note or "",
            )
            for e in db_entries
        ]

        # 5. Build GenerationInput and RepairInput
        gen_input = GenerationInput(
            month_start=month_start,
            month_end=month_end,
            employees=tuple(domain_employees),
            brand_processes=tuple(domain_bps),
            assignments=tuple(domain_assignments),
            coverage_rules=tuple(domain_rules),
            holidays=tuple(domain_holidays),
            leaves=tuple(domain_leaves),
            locked_cells=(),
            supply_matrix=(),
            demand_matrix=tuple(demand_matrix),
            random_seed=42,
            time_limit_seconds=float(self.settings.SOLVER_TIME_LIMIT_S),
            previous_tail_work_days=prev_month_tail,
            initial_compoff_balances=compoff_balances,
        )

        repair_emp_tuple = tuple(str(eid) for eid in eligible_emp_ids) if eligible_emp_ids else None
        repair_inp = RepairInput(
            gen_input=gen_input,
            current_roster_cells=tuple(current_cells),
            repair_dates=tuple(sorted(impacted_dates)),
            repair_employee_ids=repair_emp_tuple,
            use_fallback=request.use_fallback,
        )

        # 6. Execute repair
        repair_out = repair_roster(repair_inp)

        # 7. Enrich conflicts and calculate diff
        enriched_conflicts = enrich_conflicts(
            conflicts=repair_out.validation_result.conflicts,
            employees=domain_employees,
            brand_processes=domain_bps,
            assignments=domain_assignments,
            roster_cells=list(repair_out.all_roster_cells),
            demand_cells=demand_matrix,
            holidays=domain_holidays,
            leaves=domain_leaves,
        )

        existing_conflicts = self.conflict_repo.get_by_period(period_id)
        new_conflicts, resolved_conflicts, unchanged_conflicts = self._diff_conflicts(
            orig_conflicts=existing_conflicts,
            sim_conflicts=enriched_conflicts,
            bp_name_map=bp_name_map,
            bp_proc_map=bp_proc_map,
            emp_name_map=emp_name_map,
        )

        is_feasible = (
            len([c for c in enriched_conflicts if c.severity == DomainConflictSeverity.BLOCKING])
            == 0
        )
        net_conflict_change = len(new_conflicts) - len(resolved_conflicts)

        # 8. Repaired cells diff
        entry_by_key = {(e.employee_id, e.date): e for e in db_entries}
        repaired_entry_reads: list[RosterEntryRead] = []
        for rc in repair_out.repaired_cells:
            emp_uuid = uuid.UUID(rc.employee_id)
            orig_entry = entry_by_key.get((emp_uuid, rc.date))
            entry_id = orig_entry.id if orig_entry else uuid.uuid4()
            repaired_entry_reads.append(
                RosterEntryRead(
                    id=entry_id,
                    roster_period_id=period_id,
                    employee_id=emp_uuid,
                    date=rc.date,
                    status=DbRosterEntryStatus(rc.status.value),
                    source=EntrySource.AUTO,
                    is_locked=rc.is_locked,
                    note=rc.note or "Repaired via local solver",
                    created_at=orig_entry.created_at if orig_entry else dt.datetime.now(dt.UTC),
                    updated_at=dt.datetime.now(dt.UTC),
                )
            )

        # 9. Apply if requested
        target_period = period
        if request.apply:
            if period.status == RosterPeriodStatus.PUBLISHED:
                parent_read = self.clone_roster(
                    period.id,
                    RosterCloneRequest(note="Cloned via local repair"),
                    user_id=user_id,
                )
                target_period = self.period_repo.get_by_id(parent_read.id) or period

            target_entries = self.entry_repo.get_by_period(target_period.id)
            target_entry_map = {(e.employee_id, e.date): e for e in target_entries}

            for rc in repair_out.repaired_cells:
                emp_uuid = uuid.UUID(rc.employee_id)
                e = target_entry_map.get((emp_uuid, rc.date))
                if e:
                    before_st = e.status.value
                    e.status = DbRosterEntryStatus(rc.status.value)
                    e.note = rc.note or "Repaired via local solver"
                    self.session.add(e)
                    self.session.add(
                        AuditLog(
                            user_id=user_id,
                            action="ROSTER_LOCAL_REPAIR_CELL",
                            entity_type="RosterEntry",
                            entity_id=str(e.id),
                            before={"status": before_st},
                            after={"status": e.status.value, "date": str(e.date)},
                        )
                    )

            self.conflict_repo.delete_by_period(target_period.id)
            db_conflicts: list[DbRosterConflict] = [
                DbRosterConflict(
                    id=uuid.uuid4(),
                    roster_period_id=target_period.id,
                    code=c.code.value if hasattr(c.code, "value") else str(c.code),
                    severity=DbConflictSeverity(
                        c.severity.value if hasattr(c.severity, "value") else str(c.severity)
                    ),
                    brand_process_id=uuid.UUID(c.brand_process_id) if c.brand_process_id else None,
                    employee_id=uuid.UUID(c.employee_id) if c.employee_id else None,
                    date_from=c.date_from,
                    date_to=c.date_to,
                    root_causes=list(c.root_causes),
                    message=c.message,
                    suggestions=[
                        {
                            "type": getattr(s, "type", "").value
                            if hasattr(getattr(s, "type", ""), "value")
                            else str(getattr(s, "type", "")),
                            "action": getattr(s, "action", ""),
                            "description": getattr(s, "description", ""),
                            "employee_id": str(getattr(s, "employee_id", ""))
                            if getattr(s, "employee_id", None)
                            else None,
                            "brand_process_id": str(getattr(s, "brand_process_id", ""))
                            if getattr(s, "brand_process_id", None)
                            else None,
                            "target_date": getattr(s, "target_date", None).isoformat()
                            if getattr(s, "target_date", None)
                            else None,
                            "source_date": getattr(s, "source_date", None).isoformat()
                            if getattr(s, "source_date", None)
                            else None,
                            "net_impact": f"Fixes {getattr(s, 'fixes', 1)} coverage gap, opens {getattr(s, 'opens', 0)}"
                            if getattr(s, "fixes", 0)
                            else getattr(s, "net_impact", ""),
                            "score": getattr(s, "score", 0.0),
                        }
                        for s in c.suggestions
                    ],
                )
                for c in enriched_conflicts
            ]
            self.conflict_repo.bulk_create(db_conflicts)
            target_period.is_stale = False
            self.session.add(target_period)

            self.session.add(
                AuditLog(
                    user_id=user_id,
                    action="ROSTER_LOCAL_REPAIR_APPLY",
                    entity_type="RosterPeriod",
                    entity_id=str(target_period.id),
                    before=None,
                    after={
                        "repaired_cells_count": len(repair_out.repaired_cells),
                        "period_id": str(target_period.id),
                        "version": target_period.version,
                    },
                )
            )
            self.session.flush()

        period_read = self.get_roster_period(target_period.id) if request.apply else None

        return RosterRepairResponse(
            is_feasible=is_feasible,
            repaired_cells_count=len(repair_out.repaired_cells),
            repaired_cells=repaired_entry_reads,
            new_conflicts=new_conflicts,
            resolved_conflicts=resolved_conflicts,
            unchanged_conflicts=unchanged_conflicts,
            net_conflict_change=net_conflict_change,
            solver_status=repair_out.solver_status.value,
            solve_time_seconds=round(repair_out.solve_time_seconds, 3),
            applied=request.apply,
            period=period_read,
        )

    def export_roster(
        self,
        period_id: uuid.UUID,
        format: str = "csv",
        view: str = "grid",
        date: dt.date | None = None,
    ) -> tuple[bytes, str, str]:
        """Export a roster period in CSV or XLSX format for a specified view.

        Returns:
            (data_bytes, media_type, filename)
        """
        period_read = self.get_roster_period(period_id)
        fmt_clean = format.lower().strip()
        if fmt_clean not in ("csv", "xlsx"):
            raise BusinessValidationError(
                f"Invalid export format '{format}'. Supported formats: csv, xlsx"
            )

        view_clean = view.lower().strip()
        month_str = period_read.month.strftime("%Y-%m")

        if view_clean in ("grid", "month"):
            grid_data = self.get_grid_view(period_id=period_id, view="company")
            filename = f"roster_{month_str}_v{period_read.version}_grid.{fmt_clean}"
            if fmt_clean == "csv":
                csv_str = export_grid_csv(grid_data)
                return csv_str.encode("utf-8-sig"), "text/csv; charset=utf-8", filename
            else:
                xlsx_bytes = export_grid_xlsx(grid_data)
                return (
                    xlsx_bytes,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    filename,
                )

        elif view_clean == "day":
            target_date = date or period_read.month
            day_data = self.get_day_view(period_id=period_id, target_date=target_date)
            filename = f"roster_{target_date.isoformat()}_v{period_read.version}_day.{fmt_clean}"
            if fmt_clean == "csv":
                csv_str = export_day_csv(day_data)
                return csv_str.encode("utf-8-sig"), "text/csv; charset=utf-8", filename
            else:
                xlsx_bytes = export_day_xlsx(day_data)
                return (
                    xlsx_bytes,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    filename,
                )

        elif view_clean in ("coverage", "summary"):
            coverage_data = self.get_coverage(period_id=period_id)
            filename = f"roster_{month_str}_v{period_read.version}_coverage.{fmt_clean}"
            if fmt_clean == "csv":
                csv_str = export_coverage_csv(coverage_data)
                return csv_str.encode("utf-8-sig"), "text/csv; charset=utf-8", filename
            else:
                xlsx_bytes = export_coverage_xlsx(coverage_data)
                return (
                    xlsx_bytes,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    filename,
                )

        elif view_clean in ("conflicts", "report"):
            conflicts_data = self.get_conflicts(period_id=period_id)
            filename = f"roster_{month_str}_v{period_read.version}_conflicts.{fmt_clean}"
            if fmt_clean == "csv":
                csv_str = export_conflicts_csv(conflicts_data)
                return csv_str.encode("utf-8-sig"), "text/csv; charset=utf-8", filename
            else:
                xlsx_bytes = export_conflicts_xlsx(conflicts_data)
                return (
                    xlsx_bytes,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    filename,
                )

        else:
            raise BusinessValidationError(
                f"Invalid export view '{view}'. Supported views: grid, day, coverage, conflicts"
            )

    def compare_rosters(
        self,
        period_id_a: uuid.UUID,
        period_id_b: uuid.UUID,
    ) -> RosterCompareResponse:
        """Compare two roster periods side-by-side.

        Evaluates differences in conflicts, coverage percentage, weekend-off fairness spread,
        and cell-by-cell schedule changes between Version A and Version B.
        """
        period_a = self.get_roster_period(period_id_a)
        period_b = self.get_roster_period(period_id_b)

        if period_a.month != period_b.month:
            raise BusinessValidationError(
                f"Cannot compare rosters from different months: {period_a.month} vs {period_b.month}"
            )

        # 1. Compute metrics for each version
        def compute_metrics(period_read: RosterPeriodRead) -> RosterVersionMetrics:
            pid = period_read.id
            cov_cells = self.get_coverage(period_id=pid)
            total_req = sum(c.required for c in cov_cells)
            total_cov = sum(min(c.required, c.actual) for c in cov_cells)
            coverage_pct = round((total_cov / total_req * 100.0), 1) if total_req > 0 else 100.0
            total_shortfall = sum(c.shortfall for c in cov_cells)
            shortfall_slots_count = sum(1 for c in cov_cells if c.shortfall > 0)

            conflicts = self.conflict_repo.get_by_period(pid)
            blocking = sum(1 for c in conflicts if c.severity == DbConflictSeverity.BLOCKING)
            warnings = sum(1 for c in conflicts if c.severity == DbConflictSeverity.WARNING)
            info = sum(1 for c in conflicts if c.severity == DbConflictSeverity.INFO)

            entries = self.entry_repo.get_by_period(pid)
            emp_ids = {e.employee_id for e in entries}
            weekend_offs: dict[str, int] = {str(eid): 0 for eid in emp_ids}
            for e in entries:
                if e.date.weekday() in (5, 6) and e.status == DbRosterEntryStatus.WEEKLY_OFF:
                    weekend_offs[str(e.employee_id)] += 1

            if weekend_offs:
                min_w = min(weekend_offs.values())
                max_w = max(weekend_offs.values())
                spread = max_w - min_w
            else:
                min_w = max_w = spread = 0

            return RosterVersionMetrics(
                period_id=pid,
                version=period_read.version,
                status=period_read.status,
                month=period_read.month,
                blocking_conflicts=blocking,
                warning_conflicts=warnings,
                info_conflicts=info,
                total_conflicts=len(conflicts),
                coverage_pct=coverage_pct,
                total_shortfall=total_shortfall,
                shortfall_slots_count=shortfall_slots_count,
                fairness_spread=spread,
                min_weekend_offs=min_w,
                max_weekend_offs=max_w,
                weekend_offs_by_employee=weekend_offs,
            )

        metrics_a = compute_metrics(period_a)
        metrics_b = compute_metrics(period_b)

        # 2. Compute deltas (B - A)
        delta = RosterCompareDelta(
            blocking_delta=metrics_b.blocking_conflicts - metrics_a.blocking_conflicts,
            warnings_delta=metrics_b.warning_conflicts - metrics_a.warning_conflicts,
            coverage_pct_delta=round(metrics_b.coverage_pct - metrics_a.coverage_pct, 1),
            fairness_spread_delta=metrics_b.fairness_spread - metrics_a.fairness_spread,
            total_cells_changed=0,  # updated below
        )

        # 3. Cell diffs
        db_employees = self.session.scalars(select(DbEmployee)).all()
        emp_map = {e.id: (e.code, e.full_name) for e in db_employees}

        entries_a = {(e.employee_id, e.date): e for e in self.entry_repo.get_by_period(period_id_a)}
        entries_b = {(e.employee_id, e.date): e for e in self.entry_repo.get_by_period(period_id_b)}
        all_cell_keys = set(entries_a.keys()) | set(entries_b.keys())

        cell_diffs: list[RosterCellDiffItem] = []
        for emp_id, d in sorted(all_cell_keys, key=lambda k: (k[1], k[0])):
            ent_a = entries_a.get((emp_id, d))
            ent_b = entries_b.get((emp_id, d))
            st_a = ent_a.status if ent_a else None
            st_b = ent_b.status if ent_b else None
            if st_a != st_b:
                code, name = emp_map.get(emp_id, ("", ""))
                cell_diffs.append(
                    RosterCellDiffItem(
                        employee_id=emp_id,
                        employee_code=code,
                        employee_name=name,
                        date=d,
                        status_a=st_a,
                        status_b=st_b,
                    )
                )

        delta.total_cells_changed = len(cell_diffs)

        # 4. Conflict diff
        conflicts_a = self.conflict_repo.get_by_period(period_id_a)
        conflicts_b = self.conflict_repo.get_by_period(period_id_b)

        bp_stmt = select(DbBrandProcess).join(DbBrandProcess.brand).order_by(DbBrand.name)
        db_bps = self.session.scalars(bp_stmt).all()
        bp_name_map = {str(bp.id): bp.brand.name for bp in db_bps if bp.brand}
        bp_proc_map = {
            str(bp.id): (bp.process.name, bp.process.code) for bp in db_bps if bp.process
        }
        emp_name_map = {str(e.id): e.full_name for e in db_employees}

        def serialize_db_conflict(c: DbRosterConflict) -> dict[str, Any]:
            bp_id = str(c.brand_process_id) if c.brand_process_id else None
            emp_id = str(c.employee_id) if c.employee_id else None
            return {
                "id": str(c.id),
                "roster_period_id": str(c.roster_period_id),
                "code": c.code,
                "severity": c.severity.value,
                "brand_process_id": bp_id,
                "brand_name": bp_name_map.get(bp_id),
                "process_name": bp_proc_map.get(bp_id, ("", ""))[0],
                "employee_id": emp_id,
                "employee_name": emp_name_map.get(emp_id),
                "date_from": c.date_from.isoformat() if c.date_from else None,
                "date_to": c.date_to.isoformat() if c.date_to else None,
                "root_causes": list(c.root_causes or []),
                "message": c.message,
                "is_acknowledged": c.is_acknowledged,
                "acknowledged_reason": c.acknowledged_reason,
            }

        def make_sig(c: DbRosterConflict) -> tuple[Any, ...]:
            return (
                c.code,
                str(c.brand_process_id) if c.brand_process_id else None,
                str(c.employee_id) if c.employee_id else None,
                c.date_from,
                c.date_to,
            )

        map_a = {make_sig(c): c for c in conflicts_a}
        map_b = {make_sig(c): c for c in conflicts_b}

        resolved_in_b = [serialize_db_conflict(c) for sig, c in map_a.items() if sig not in map_b]
        new_in_b = [serialize_db_conflict(c) for sig, c in map_b.items() if sig not in map_a]
        common = [serialize_db_conflict(c) for sig, c in map_b.items() if sig in map_a]

        return RosterCompareResponse(
            period_a=period_a,
            period_b=period_b,
            metrics_a=metrics_a,
            metrics_b=metrics_b,
            delta=delta,
            conflict_diff={
                "new_in_b": new_in_b,
                "resolved_in_b": resolved_in_b,
                "common": common,
            },
            cell_diffs=cell_diffs,
        )
