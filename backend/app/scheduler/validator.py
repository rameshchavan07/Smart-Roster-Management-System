"""Pure-Python independent roster validator for the scheduling engine.

Evaluates generated, edited, and imported rosters against all mandatory
constraints (H1–H5) and quality checks per SCHEDULING_ENGINE.md Section 7.

Conflict Catalogue:
- E001 (NO_COVERAGE): Required operating day, zero available employees assigned (BLOCKING)
- E002 (UNDER_STAFFED): Coverage < demand but > 0 (BLOCKING)
- E003 (WEEKLY_OFF_BREAKS_COVERAGE): Root-cause tag on E001/E002
- E004 (LEAVE_BREAKS_COVERAGE): Root-cause tag on E001/E002
- E005 (MAX_CONSECUTIVE_EXCEEDED): Run of consecutive WORK days > limit (BLOCKING)
- E006 (WEEKLY_OFF_MISSING): Fewer weekly offs than required in a week (BLOCKING)
- E007 (INVALID_CELL): WORK on leave/comp-off day, or invalid status (BLOCKING)
- E008 (OVERLOAD): Scheduled across > max_concurrent_processes (WARNING)
- E009 (COMPOFF_BALANCE): Redeemed comp-off exceeds earned balance (BLOCKING)
- W001 (PREFERENCE_VIOLATED): Preferred off day not honoured (WARNING)
- W003 (SINGLE_POINT_OF_FAILURE): Single eligible employee without backup (INFO/WARNING)

Non-negotiable architectural rule:
Zero external framework imports (FastAPI, SQLAlchemy, Pydantic, DB).
Operates exclusively on scheduler domain types and standard library.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import date

from app.scheduler.calendar import has_applicable_holiday, is_operating_day
from app.scheduler.domain import (
    Assignment,
    AssignmentType,
    BrandProcess,
    Conflict,
    ConflictCode,
    ConflictSeverity,
    CoverageCell,
    DemandCell,
    Employee,
    EmployeeLeave,
    Holiday,
    LeaveType,
    RosterCell,
    RosterStatus,
    SupplyCell,
    ValidationResult,
    WeeklyOffMode,
)


def partition_into_weeks(dates: Sequence[date]) -> list[list[date]]:
    """Partition unique sorted dates into Monday-to-Sunday chunks within the month."""
    sorted_dates = sorted(set(dates))
    if not sorted_dates:
        return []

    weeks: list[list[date]] = []
    current_week: list[date] = []

    for d in sorted_dates:
        current_week.append(d)
        if d.weekday() == 6:  # Sunday terminates week
            weeks.append(current_week)
            current_week = []

    if current_week:
        weeks.append(current_week)

    return weeks


def validate_coverage(
    roster_lookup: dict[tuple[str, date], RosterCell],
    demand_lookup: dict[tuple[str, date], DemandCell],
    brand_processes: Sequence[BrandProcess],
    assignments: Sequence[Assignment],
    dates: Sequence[date],
    employees_lookup: dict[str, Employee],
) -> tuple[list[Conflict], list[CoverageCell]]:
    """Validate staffing headcount against demand (E001, E002, root causes E003, E004)."""
    conflicts: list[Conflict] = []
    coverage_cells: list[CoverageCell] = []

    # Map brand_process_id -> list of assigned employee_ids
    bp_assigned: dict[str, list[str]] = defaultdict(list)
    for a in assignments:
        bp_assigned[a.brand_process_id].append(a.employee_id)

    sorted_bps = sorted(brand_processes, key=lambda bp: bp.id)
    sorted_dates = sorted(set(dates))

    for target_date in sorted_dates:
        for bp in sorted_bps:
            demand_cell = demand_lookup.get((bp.id, target_date))
            required = demand_cell.required_headcount if demand_cell else 0

            assigned_emps = bp_assigned.get(bp.id, [])
            working_emps: list[str] = []
            off_details: list[tuple[str, str, str]] = []  # (emp_id, emp_name, status_str)

            for emp_id in assigned_emps:
                cell = roster_lookup.get((emp_id, target_date))
                emp = employees_lookup.get(emp_id)
                emp_name = emp.full_name if emp else emp_id

                if cell and cell.status in (RosterStatus.WORK, RosterStatus.HOLIDAY_WORK):
                    working_emps.append(emp_id)
                elif cell:
                    off_details.append((emp_id, emp_name, cell.status.value))

            covered = len(working_emps)
            shortfall = max(0, required - covered)

            cov_cell = CoverageCell(
                brand_process_id=bp.id,
                date=target_date,
                required=required,
                covered=covered,
                shortfall=shortfall,
                assigned_employee_ids=tuple(working_emps),
            )
            coverage_cells.append(cov_cell)

            if shortfall > 0:
                # Identify root causes from off assigned employees
                root_causes: list[str] = []
                for _, _, status_str in off_details:
                    if status_str == RosterStatus.WEEKLY_OFF.value:
                        if ConflictCode.E003.value not in root_causes:
                            root_causes.append(ConflictCode.E003.value)
                            root_causes.append("WEEKLY_OFF")
                    elif status_str in (RosterStatus.LEAVE.value, RosterStatus.COMP_OFF.value):
                        if ConflictCode.E004.value not in root_causes:
                            root_causes.append(ConflictCode.E004.value)
                            root_causes.append("LEAVE")
                    elif (
                        status_str == RosterStatus.HOLIDAY_OFF.value
                        and "HOLIDAY_OFF" not in root_causes
                    ):
                        root_causes.append("HOLIDAY_OFF")

                code = ConflictCode.E001 if covered == 0 else ConflictCode.E002
                off_summary = ", ".join(f"{name} ({st})" for _, name, st in off_details)
                off_msg = f" Assigned off: {off_summary}." if off_summary else ""

                message = (
                    f"Staffing shortfall for {bp.brand_name} - {bp.process_name} on {target_date}: "
                    f"required {required}, covered {covered} (shortfall: {shortfall}).{off_msg}"
                )

                conflicts.append(
                    Conflict(
                        code=code,
                        severity=ConflictSeverity.BLOCKING,
                        brand_process_id=bp.id,
                        date_from=target_date,
                        date_to=target_date,
                        root_causes=tuple(root_causes),
                        message=message,
                    )
                )

    return conflicts, coverage_cells


def validate_weekly_offs(
    roster_lookup: dict[tuple[str, date], RosterCell],
    dates: Sequence[date],
    employee: Employee,
) -> list[Conflict]:
    """Validate mandatory weekly off counts with month-edge pro-rating (E006)."""
    conflicts: list[Conflict] = []
    weeks = partition_into_weeks(dates)

    for week_dates in weeks:
        week_len = len(week_dates)
        # Pro-rating rule Q3: partial week >= 4 days receives full weekly_off_count; < 4 days receives 0
        required_offs = employee.weekly_off_count if week_len >= 4 else 0

        actual_offs = 0
        for d in week_dates:
            cell = roster_lookup.get((employee.id, d))
            if cell and cell.status == RosterStatus.WEEKLY_OFF:
                actual_offs += 1

        if actual_offs < required_offs:
            deficit = required_offs - actual_offs
            start_d = week_dates[0]
            end_d = week_dates[-1]
            message = (
                f"Employee {employee.full_name} ({employee.code}) has fewer weekly offs than entitled "
                f"in week {start_d} to {end_d}: required {required_offs}, got {actual_offs} (deficit: {deficit})."
            )
            conflicts.append(
                Conflict(
                    code=ConflictCode.E006,
                    severity=ConflictSeverity.BLOCKING,
                    employee_id=employee.id,
                    date_from=start_d,
                    date_to=end_d,
                    root_causes=("WEEKLY_OFF_DEFICIT",),
                    message=message,
                )
            )

    return conflicts


def validate_consecutive_days(
    roster_lookup: dict[tuple[str, date], RosterCell],
    dates: Sequence[date],
    employee: Employee,
    carry_in_days: int = 0,
) -> list[Conflict]:
    """Validate maximum consecutive working days (E005)."""
    conflicts: list[Conflict] = []
    sorted_dates = sorted(set(dates))

    current_streak = carry_in_days
    streak_start: date | None = sorted_dates[0] if sorted_dates and carry_in_days > 0 else None
    flagged_for_streak = False

    for d in sorted_dates:
        cell = roster_lookup.get((employee.id, d))
        is_work = cell is not None and cell.status in (RosterStatus.WORK, RosterStatus.HOLIDAY_WORK)

        if is_work:
            if current_streak == 0:
                streak_start = d
                flagged_for_streak = False
            current_streak += 1

            if current_streak > employee.max_consecutive_days and not flagged_for_streak:
                assert streak_start is not None
                message = (
                    f"Employee {employee.full_name} ({employee.code}) exceeded maximum consecutive "
                    f"working days ({employee.max_consecutive_days}): current run is {current_streak} days "
                    f"from {streak_start} to {d}."
                )
                conflicts.append(
                    Conflict(
                        code=ConflictCode.E005,
                        severity=ConflictSeverity.BLOCKING,
                        employee_id=employee.id,
                        date_from=streak_start,
                        date_to=d,
                        root_causes=("MAX_CONSECUTIVE_EXCEEDED",),
                        message=message,
                    )
                )
                flagged_for_streak = True
        else:
            current_streak = 0
            streak_start = None
            flagged_for_streak = False

    return conflicts


def validate_cell_validity(
    roster_lookup: dict[tuple[str, date], RosterCell],
    dates: Sequence[date],
    employee: Employee,
    holidays: Sequence[Holiday],
    leaves: Sequence[EmployeeLeave] = (),
    supply_lookup: dict[tuple[str, date], SupplyCell] | None = None,
) -> list[Conflict]:
    """Validate cell status legality against leave, comp-off, holidays, and locks (E007)."""
    conflicts: list[Conflict] = []
    sorted_dates = sorted(set(dates))

    for d in sorted_dates:
        cell = roster_lookup.get((employee.id, d))
        if not cell:
            continue

        status = cell.status

        # 1. Check against approved leaves
        for leave in leaves:
            if leave.employee_id == employee.id and leave.covers(d):
                expected_status = (
                    RosterStatus.COMP_OFF
                    if leave.type == LeaveType.COMP_OFF
                    else RosterStatus.LEAVE
                )
                if status != expected_status:
                    message = (
                        f"Employee {employee.full_name} is scheduled as {status.value} on {d}, "
                        f"which conflicts with approved {leave.type.value} leave ({expected_status.value})."
                    )
                    conflicts.append(
                        Conflict(
                            code=ConflictCode.E007,
                            severity=ConflictSeverity.BLOCKING,
                            employee_id=employee.id,
                            date_from=d,
                            date_to=d,
                            root_causes=("LEAVE_CONFLICT",),
                            message=message,
                        )
                    )

        # 2. Check HOLIDAY_WORK / HOLIDAY_OFF validity
        is_holiday = has_applicable_holiday(holidays, brand_id="", target_date=d) or any(
            h.date == d for h in holidays
        )

        if status in (RosterStatus.HOLIDAY_WORK, RosterStatus.HOLIDAY_OFF) and not is_holiday:
            message = (
                f"Employee {employee.full_name} has status {status.value} on {d}, "
                f"but this date is not a recognized public holiday."
            )
            conflicts.append(
                Conflict(
                    code=ConflictCode.E007,
                    severity=ConflictSeverity.BLOCKING,
                    employee_id=employee.id,
                    date_from=d,
                    date_to=d,
                    root_causes=("INVALID_HOLIDAY_STATUS",),
                    message=message,
                )
            )

        # 3. Check manager locked cells
        if supply_lookup:
            supply_cell = supply_lookup.get((employee.id, d))
            if (
                supply_cell
                and supply_cell.is_locked
                and supply_cell.locked_status
                and supply_cell.locked_status != status
            ):
                message = (
                    f"Employee {employee.full_name} is scheduled as {status.value} on {d}, "
                    f"overriding locked status {supply_cell.locked_status.value}."
                )
                conflicts.append(
                    Conflict(
                        code=ConflictCode.E007,
                        severity=ConflictSeverity.BLOCKING,
                        employee_id=employee.id,
                        date_from=d,
                        date_to=d,
                        root_causes=("LOCKED_CELL_OVERRIDDEN",),
                        message=message,
                    )
                )

    return conflicts


def validate_overload(
    roster_lookup: dict[tuple[str, date], RosterCell],
    dates: Sequence[date],
    employee: Employee,
    assignments: Sequence[Assignment],
    brand_processes_lookup: dict[str, BrandProcess],
    holidays: Sequence[Holiday],
) -> list[Conflict]:
    """Validate multi-brand concurrent process overload threshold (E008 WARNING)."""
    conflicts: list[Conflict] = []
    emp_assignments = [a for a in assignments if a.employee_id == employee.id]
    if len(emp_assignments) <= employee.max_concurrent_processes:
        return conflicts

    sorted_dates = sorted(set(dates))

    for d in sorted_dates:
        cell = roster_lookup.get((employee.id, d))
        if not cell or cell.status not in (RosterStatus.WORK, RosterStatus.HOLIDAY_WORK):
            continue

        active_bps: list[str] = []
        for a in emp_assignments:
            bp = brand_processes_lookup.get(a.brand_process_id)
            if bp and is_operating_day(bp, d, holidays):
                active_bps.append(bp.brand_name)

        if len(active_bps) > employee.max_concurrent_processes:
            message = (
                f"Employee {employee.full_name} ({employee.code}) is scheduled to cover {len(active_bps)} "
                f"active operating brand-processes ({', '.join(active_bps)}) on {d}, "
                f"exceeding threshold of {employee.max_concurrent_processes}."
            )
            conflicts.append(
                Conflict(
                    code=ConflictCode.E008,
                    severity=ConflictSeverity.WARNING,
                    employee_id=employee.id,
                    date_from=d,
                    date_to=d,
                    root_causes=("CONCURRENT_PROCESS_OVERLOAD",),
                    message=message,
                )
            )

    return conflicts


def validate_compoff_balance(
    roster_lookup: dict[tuple[str, date], RosterCell],
    dates: Sequence[date],
    employee: Employee,
    initial_balance: int = 0,
) -> list[Conflict]:
    """Validate comp-off redemption balance (E009)."""
    conflicts: list[Conflict] = []
    balance = initial_balance
    sorted_dates = sorted(set(dates))

    for d in sorted_dates:
        cell = roster_lookup.get((employee.id, d))
        if not cell:
            continue

        if cell.status == RosterStatus.HOLIDAY_WORK:
            balance += 1
        elif cell.status == RosterStatus.COMP_OFF:
            balance -= 1
            if balance < 0:
                message = (
                    f"Employee {employee.full_name} redeemed a comp-off on {d} "
                    f"with negative balance ({balance}). Initial balance was {initial_balance}."
                )
                conflicts.append(
                    Conflict(
                        code=ConflictCode.E009,
                        severity=ConflictSeverity.BLOCKING,
                        employee_id=employee.id,
                        date_from=d,
                        date_to=d,
                        root_causes=("INSUFFICIENT_COMPOFF_BALANCE",),
                        message=message,
                    )
                )

    return conflicts


def validate_preferences(
    roster_lookup: dict[tuple[str, date], RosterCell],
    dates: Sequence[date],
    employee: Employee,
) -> list[Conflict]:
    """Validate employee preferred off weekdays and dates (W001)."""
    conflicts: list[Conflict] = []
    sorted_dates = sorted(set(dates))

    for d in sorted_dates:
        cell = roster_lookup.get((employee.id, d))
        if not cell or cell.status not in (RosterStatus.WORK, RosterStatus.HOLIDAY_WORK):
            continue

        # Preferred off weekday
        if d.weekday() in employee.preferred_weekly_off_weekdays:
            weekday_name = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][d.weekday()]
            message = (
                f"Employee {employee.full_name} preferred {weekday_name} off, "
                f"but is scheduled to work on {d}."
            )
            conflicts.append(
                Conflict(
                    code=ConflictCode.W001,
                    severity=ConflictSeverity.WARNING,
                    employee_id=employee.id,
                    date_from=d,
                    date_to=d,
                    root_causes=("PREFERRED_WEEKDAY_OFF_HONOURED",),
                    message=message,
                )
            )

        # Preferred off date
        if d in employee.preferred_off_dates:
            message = (
                f"Employee {employee.full_name} requested preferred off on date {d}, "
                f"but is scheduled to work."
            )
            conflicts.append(
                Conflict(
                    code=ConflictCode.W001,
                    severity=ConflictSeverity.WARNING,
                    employee_id=employee.id,
                    date_from=d,
                    date_to=d,
                    root_causes=("PREFERRED_DATE_OFF_NOT_HONOURED",),
                    message=message,
                )
            )

        # Fixed mandatory weekly off weekday violation
        if (
            employee.weekly_off_mode == WeeklyOffMode.FIXED_MANDATORY
            and d.weekday() in employee.fixed_weekly_off_weekdays
        ):
            weekday_name = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][d.weekday()]
            message = (
                f"Employee {employee.full_name} has mandatory fixed weekly off on {weekday_name}, "
                f"but is scheduled to work on {d}."
            )
            conflicts.append(
                Conflict(
                    code=ConflictCode.E006,
                    severity=ConflictSeverity.BLOCKING,
                    employee_id=employee.id,
                    date_from=d,
                    date_to=d,
                    root_causes=("MANDATORY_FIXED_OFF_VIOLATED",),
                    message=message,
                )
            )

    return conflicts


def validate_single_point_of_failure(
    brand_processes: Sequence[BrandProcess],
    assignments: Sequence[Assignment],
    demand_lookup: dict[tuple[str, date], DemandCell],
    dates: Sequence[date],
) -> list[Conflict]:
    """Identify brand-processes with exactly one eligible primary staff and no backup (W003)."""
    conflicts: list[Conflict] = []
    bp_primary: dict[str, list[str]] = defaultdict(list)
    bp_backup: dict[str, list[str]] = defaultdict(list)

    for a in assignments:
        if a.type == AssignmentType.PRIMARY:
            bp_primary[a.brand_process_id].append(a.employee_id)
        elif a.type == AssignmentType.BACKUP:
            bp_backup[a.brand_process_id].append(a.employee_id)

    sorted_bps = sorted(brand_processes, key=lambda bp: bp.id)

    for bp in sorted_bps:
        # Check if brand process has any active demand in the period
        has_demand = any(
            (demand_lookup.get((bp.id, d)) and demand_lookup[(bp.id, d)].required_headcount > 0)
            for d in dates
        )
        if not has_demand:
            continue

        primaries = bp_primary.get(bp.id, [])
        backups = bp_backup.get(bp.id, [])

        if len(primaries) == 1 and len(backups) == 0:
            message = (
                f"Brand-process {bp.brand_name} - {bp.process_name} operates with a Single Point of Failure: "
                f"exactly 1 primary employee ({primaries[0]}) assigned and 0 backups configured."
            )
            conflicts.append(
                Conflict(
                    code=ConflictCode.W003,
                    severity=ConflictSeverity.INFO,
                    brand_process_id=bp.id,
                    employee_id=primaries[0],
                    root_causes=("SINGLE_POINT_OF_FAILURE",),
                    message=message,
                )
            )

    return conflicts


def validate_weekend_fairness(
    roster_lookup: dict[tuple[str, date], RosterCell],
    dates: Sequence[date],
    employees: Sequence[Employee],
    threshold: int = 2,
) -> list[Conflict]:
    """Check if weekend-off spread across employees in the same pod exceeds threshold (W002)."""
    conflicts: list[Conflict] = []
    pod_emps: dict[str, list[Employee]] = defaultdict(list)
    for emp in employees:
        if emp.pod_id:
            pod_emps[emp.pod_id].append(emp)

    weekend_dates = [d for d in dates if d.weekday() in (5, 6)]  # Saturday=5, Sunday=6
    if not weekend_dates:
        return conflicts

    off_statuses = {RosterStatus.WEEKLY_OFF, RosterStatus.COMP_OFF, RosterStatus.HOLIDAY_OFF}

    for pod_id, emps in sorted(pod_emps.items(), key=lambda x: x[0]):
        if len(emps) < 2:
            continue
        weekend_off_counts: dict[str, int] = {}
        for emp in emps:
            count = 0
            for d in weekend_dates:
                cell = roster_lookup.get((emp.id, d))
                if cell and cell.status in off_statuses:
                    count += 1
            weekend_off_counts[emp.id] = count

        counts = list(weekend_off_counts.values())
        spread = max(counts) - min(counts)
        if spread > threshold:
            min_emp_id = min(weekend_off_counts, key=lambda k: weekend_off_counts[k])
            message = (
                f"Weekend-off distribution imbalance in pod {pod_id}: spread of {spread} weekend offs "
                f"(max {max(counts)} vs min {min(counts)}) exceeds fairness threshold of {threshold}."
            )
            conflicts.append(
                Conflict(
                    code=ConflictCode.W002,
                    severity=ConflictSeverity.INFO,
                    employee_id=min_emp_id,
                    root_causes=("WEEKEND_FAIRNESS_IMBALANCE",),
                    message=message,
                )
            )

    return conflicts


def validate_roster(
    roster_cells: Sequence[RosterCell],
    demand_cells: Sequence[DemandCell],
    supply_cells: Sequence[SupplyCell],
    employees: Sequence[Employee],
    brand_processes: Sequence[BrandProcess],
    assignments: Sequence[Assignment],
    holidays: Sequence[Holiday] = (),
    leaves: Sequence[EmployeeLeave] = (),
    initial_compoff_balances: dict[str, int] | None = None,
    previous_tail_work_days: dict[str, int] | None = None,
    is_stale: bool = False,
) -> tuple[ValidationResult, list[CoverageCell]]:
    """Comprehensive independent validator function returning ValidationResult and CoverageCells."""
    # Build lookups
    roster_lookup = {(c.employee_id, c.date): c for c in roster_cells}
    demand_lookup = {(c.brand_process_id, c.date): c for c in demand_cells}
    supply_lookup = {(c.employee_id, c.date): c for c in supply_cells}
    employees_lookup = {e.id: e for e in employees}
    bp_lookup = {bp.id: bp for bp in brand_processes}

    all_dates = sorted(
        {c.date for c in roster_cells}
        | {c.date for c in demand_cells}
        | {c.date for c in supply_cells}
    )

    all_conflicts: list[Conflict] = []

    # 1. Coverage validation (E001, E002, E003, E004)
    cov_conflicts, coverage_cells = validate_coverage(
        roster_lookup=roster_lookup,
        demand_lookup=demand_lookup,
        brand_processes=brand_processes,
        assignments=assignments,
        dates=all_dates,
        employees_lookup=employees_lookup,
    )
    all_conflicts.extend(cov_conflicts)

    # 2. Per-employee validations
    compoff_balances = initial_compoff_balances or {}
    tail_days = previous_tail_work_days or {}

    for emp in sorted(employees, key=lambda e: e.id):
        # E006: Weekly off count & pro-rating
        all_conflicts.extend(validate_weekly_offs(roster_lookup, all_dates, emp))

        # E005: Max consecutive working days
        carry_in = tail_days.get(emp.id, 0)
        all_conflicts.extend(validate_consecutive_days(roster_lookup, all_dates, emp, carry_in))

        # E007: Cell validity against leaves, holidays, locks
        all_conflicts.extend(
            validate_cell_validity(
                roster_lookup=roster_lookup,
                dates=all_dates,
                employee=emp,
                holidays=holidays,
                leaves=leaves,
                supply_lookup=supply_lookup,
            )
        )

        # E008: Multi-brand concurrent process overload
        all_conflicts.extend(
            validate_overload(
                roster_lookup=roster_lookup,
                dates=all_dates,
                employee=emp,
                assignments=assignments,
                brand_processes_lookup=bp_lookup,
                holidays=holidays,
            )
        )

        # E009: Comp-off balance
        init_bal = compoff_balances.get(emp.id, 0)
        all_conflicts.extend(validate_compoff_balance(roster_lookup, all_dates, emp, init_bal))

        # W001: Preference violations & fixed off checks
        all_conflicts.extend(validate_preferences(roster_lookup, all_dates, emp))

    # 3. System-wide / brand checks (W003)
    all_conflicts.extend(
        validate_single_point_of_failure(
            brand_processes=brand_processes,
            assignments=assignments,
            demand_lookup=demand_lookup,
            dates=all_dates,
        )
    )

    # 4. Pod-level weekend fairness checks (W002)
    all_conflicts.extend(validate_weekend_fairness(roster_lookup, all_dates, employees))

    # 5. Stale roster check (W004)
    if is_stale:
        all_conflicts.append(
            Conflict(
                code=ConflictCode.W004,
                severity=ConflictSeverity.WARNING,
                root_causes=("INPUTS_CHANGED_AFTER_GENERATION",),
                message="Roster inputs have changed since this roster was generated. Re-generate or review conflicts.",
            )
        )

    validation_result = ValidationResult.from_conflicts(tuple(all_conflicts))
    return validation_result, coverage_cells


def validate(
    roster_cells: Sequence[RosterCell],
    demand_cells: Sequence[DemandCell],
    supply_cells: Sequence[SupplyCell],
    employees: Sequence[Employee],
    brand_processes: Sequence[BrandProcess],
    assignments: Sequence[Assignment],
    holidays: Sequence[Holiday] = (),
    leaves: Sequence[EmployeeLeave] = (),
    initial_compoff_balances: dict[str, int] | None = None,
    previous_tail_work_days: dict[str, int] | None = None,
    is_stale: bool = False,
) -> ValidationResult:
    """Convenience wrapper returning ValidationResult per SCHEDULING_ENGINE.md §7."""
    res, _ = validate_roster(
        roster_cells=roster_cells,
        demand_cells=demand_cells,
        supply_cells=supply_cells,
        employees=employees,
        brand_processes=brand_processes,
        assignments=assignments,
        holidays=holidays,
        leaves=leaves,
        initial_compoff_balances=initial_compoff_balances,
        previous_tail_work_days=previous_tail_work_days,
        is_stale=is_stale,
    )
    return res
