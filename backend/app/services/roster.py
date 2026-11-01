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

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.errors import BusinessValidationError, NotFoundError
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
from app.scheduler.generator_cpsat import generate_cpsat
from app.scheduler.generator_greedy import generate_greedy
from app.scheduler.supply import build_supply_matrix
from app.schemas.roster import (
    RosterConflictRead,
    RosterCoverageCell,
    RosterDayBrandProcessGroup,
    RosterDayEmployeeItem,
    RosterDayViewResponse,
    RosterGenerateRequest,
    RosterGenerateResponse,
    RosterGridCell,
    RosterGridRow,
    RosterGridViewResponse,
    RosterPeriodRead,
    RosterSummary,
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
