"""Pure-Python root-cause explainer and suggestion ranker for the scheduling engine.

Enriches raw validation conflicts with:
1. Template-based, deterministic plain English explanations per SCHEDULING_ENGINE.md §8.
2. Ranked actionable suggestions per SCHEDULING_ENGINE.md §9:
   - Backup / Floater assignment (ranked by: assigned BACKUP > same pod > floater > other pod)
   - Weekly-off swap recommendations within the same week
   - Leave / comp-off shift proposals

Non-negotiable architectural rule:
Zero external framework imports (FastAPI, SQLAlchemy, Pydantic, DB).
Operates exclusively on scheduler domain types and standard library.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from app.scheduler.domain import (
    Assignment,
    AssignmentType,
    BrandProcess,
    Conflict,
    ConflictCode,
    DemandCell,
    Employee,
    EmployeeLeave,
    Holiday,
    RosterCell,
    RosterStatus,
    Suggestion,
    SuggestionType,
)
from app.scheduler.validator import partition_into_weeks


def get_weekday_abbr(d: date) -> str:
    """Return 3-letter weekday abbreviation (e.g. Mon, Tue)."""
    return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][d.weekday()]


def format_coverage_gap_message(
    conflict: Conflict,
    bp: BrandProcess,
    target_date: date,
    demand_cell: DemandCell | None,
    roster_lookup: dict[tuple[str, date], RosterCell],
    assigned_employees: list[Employee],
    leaves: Sequence[EmployeeLeave],
    available_backups: list[tuple[Employee, str]],
) -> str:
    """Generate plain-language explanation for E001/E002 coverage shortfalls per §8."""
    required = demand_cell.required_headcount if demand_cell else 1
    weekday_str = get_weekday_abbr(target_date)
    date_str = f"{target_date.strftime('%d %b')} ({weekday_str})"

    severity_label = "no coverage" if conflict.code == ConflictCode.E001 else "under-staffing"

    # Identify reasons for non-working assigned employees
    assigned_off_reasons: list[str] = []
    for emp in assigned_employees:
        cell = roster_lookup.get((emp.id, target_date))
        status = cell.status if cell else None

        if status == RosterStatus.WEEKLY_OFF:
            assigned_off_reasons.append(f"{emp.full_name} is on weekly off")
        elif status == RosterStatus.HOLIDAY_OFF:
            assigned_off_reasons.append(f"{emp.full_name} is on personal holiday")
        elif status in (RosterStatus.LEAVE, RosterStatus.COMP_OFF):
            # Find leave details if available
            leave_desc = "approved leave"
            for leave in leaves:
                if leave.employee_id == emp.id and leave.covers(target_date):
                    if leave.start_date != leave.end_date:
                        leave_desc = f"approved {leave.type.value.lower()} leave ({leave.start_date.strftime('%d %b')}–{leave.end_date.strftime('%d %b')})"
                    else:
                        leave_desc = f"approved {leave.type.value.lower()} leave"
                    break
            assigned_off_reasons.append(f"{emp.full_name} is on {leave_desc}")

    off_str = ""
    if len(assigned_employees) == 1 and assigned_off_reasons:
        off_str = f" Its only assigned employee {assigned_off_reasons[0]}."
    elif assigned_off_reasons:
        off_str = f" Assigned staff off: {'; '.join(assigned_off_reasons)}."

    # Backups available snippet
    backups_str = ""
    if available_backups:
        backup_items = [f"{emp.full_name} ({desc})" for emp, desc in available_backups[:3]]
        backups_str = f" Backups available that day: {', '.join(backup_items)}."

    return (
        f"Brand {bp.brand_name} — {bp.process_name} has {severity_label} on {date_str}. "
        f"Required: {required}.{off_str}{backups_str}"
    )


def rank_backup_candidates(
    bp: BrandProcess,
    target_date: date,
    employees: Sequence[Employee],
    assignments: Sequence[Assignment],
    roster_lookup: dict[tuple[str, date], RosterCell],
    holidays: Sequence[Holiday],
) -> list[tuple[Employee, float, str]]:
    """Rank available backup candidates for a brand-process on a target date.

    Returns tuples of (Employee, score, description_label) sorted descending by score.
    Criteria per SCHEDULING_ENGINE.md §9:
    1. Assigned as BACKUP to bp (+100)
    2. Same pod as bp (+50)
    3. Dedicated floater (+30)
    4. Other pod (+10)
    Bonus: Working on target date (+20), Available without lock (+10)
    Overload prevention: Disqualify if concurrent active processes > limit.
    """
    assigned_primary_ids = {
        a.employee_id
        for a in assignments
        if a.brand_process_id == bp.id and a.type == AssignmentType.PRIMARY
    }
    assigned_backup_ids = {
        a.employee_id
        for a in assignments
        if a.brand_process_id == bp.id and a.type == AssignmentType.BACKUP
    }

    # Map employee_id -> count of active operating processes on target_date
    emp_active_processes: dict[str, int] = {}
    for a in assignments:
        emp_cell = roster_lookup.get((a.employee_id, target_date))
        if emp_cell and emp_cell.status in (RosterStatus.WORK, RosterStatus.HOLIDAY_WORK):
            emp_active_processes[a.employee_id] = emp_active_processes.get(a.employee_id, 0) + 1

    candidates: list[tuple[Employee, float, str]] = []

    for emp in employees:
        # Exclude primary staff who are already assigned to this brand-process
        if emp.id in assigned_primary_ids:
            continue

        cell = roster_lookup.get((emp.id, target_date))
        if not cell:
            continue

        # Employee cannot be used if on LEAVE or COMP_OFF
        if cell.status in (RosterStatus.LEAVE, RosterStatus.COMP_OFF):
            continue

        # Check overload capacity
        current_active = emp_active_processes.get(emp.id, 0)
        if current_active >= emp.max_concurrent_processes:
            continue

        score = 0.0
        role_labels: list[str] = []

        if emp.id in assigned_backup_ids:
            score += 100.0
            role_labels.append("configured backup")
        elif bp.pod_id and emp.pod_id == bp.pod_id:
            score += 50.0
            role_labels.append("same pod")
        elif emp.is_floater:
            score += 30.0
            role_labels.append("floater")
        else:
            score += 10.0
            role_labels.append("other pod")

        # Scheduling status bonus
        if cell.status in (RosterStatus.WORK, RosterStatus.HOLIDAY_WORK):
            score += 20.0
            role_labels.append("working")
        elif cell.status == RosterStatus.WEEKLY_OFF:
            score += 5.0
            role_labels.append("on weekly off")
        else:
            score += 10.0
            role_labels.append("available")

        desc = ", ".join(role_labels)
        candidates.append((emp, score, desc))

    candidates.sort(key=lambda c: c[1], reverse=True)
    return candidates


def generate_weekly_off_swap_suggestions(
    bp: BrandProcess,
    target_date: date,
    assigned_employees: Sequence[Employee],
    roster_lookup: dict[tuple[str, date], RosterCell],
    demand_lookup: dict[tuple[str, date], DemandCell],
    all_dates: Sequence[date],
) -> list[Suggestion]:
    """Generate weekly-off swap suggestions if an assigned employee is off on target_date."""
    suggestions: list[Suggestion] = []
    weeks = partition_into_weeks(all_dates)

    # Find which week target_date belongs to
    target_week: list[date] = []
    for w in weeks:
        if target_date in w:
            target_week = w
            break

    if not target_week:
        return suggestions

    for emp in assigned_employees:
        cell = roster_lookup.get((emp.id, target_date))
        if not cell or cell.status != RosterStatus.WEEKLY_OFF:
            continue

        # Look for another day in target_week where emp is working and demand is low or surplus exists
        for alt_d in target_week:
            if alt_d == target_date:
                continue

            alt_cell = roster_lookup.get((emp.id, alt_d))
            if not alt_cell or alt_cell.status not in (
                RosterStatus.WORK,
                RosterStatus.HOLIDAY_WORK,
            ):
                continue

            alt_demand = demand_lookup.get((bp.id, alt_d))
            alt_req = alt_demand.required_headcount if alt_demand else 0

            # If alternative day has 0 demand or surplus, it's a prime swap candidate
            if alt_req <= 1:
                alt_str = alt_d.strftime("%a %d %b")
                suggestions.append(
                    Suggestion(
                        type=SuggestionType.SWAP_WEEKLY_OFF,
                        action=f"Swap weekly off for {emp.full_name} to {alt_str}",
                        description=(
                            f"Move {emp.full_name}'s weekly off from {target_date.strftime('%a %d %b')} "
                            f"to {alt_str} to restore coverage for {bp.brand_name}."
                        ),
                        employee_id=emp.id,
                        brand_process_id=bp.id,
                        target_date=target_date,
                        source_date=alt_d,
                        net_impact="Fixes 1 coverage gap, maintains weekly-off requirement",
                        score=45.0,
                    )
                )

    return suggestions


def explain_conflict(
    conflict: Conflict,
    employees: Sequence[Employee],
    brand_processes: Sequence[BrandProcess],
    assignments: Sequence[Assignment],
    roster_cells: Sequence[RosterCell],
    demand_cells: Sequence[DemandCell] = (),
    holidays: Sequence[Holiday] = (),
    leaves: Sequence[EmployeeLeave] = (),
) -> Conflict:
    """Enrich a single Conflict with structured explanation and ranked suggestions."""
    # Fast lookups
    roster_lookup = {(c.employee_id, c.date): c for c in roster_cells}
    demand_lookup = {(c.brand_process_id, c.date): c for c in demand_cells}
    employees_lookup = {e.id: e for e in employees}
    bp_lookup = {bp.id: bp for bp in brand_processes}
    all_dates = sorted({c.date for c in roster_cells} | {c.date for c in demand_cells})

    # Only E001/E002 coverage shortfalls need backup/swap suggestions
    if conflict.code not in (ConflictCode.E001, ConflictCode.E002) or not conflict.brand_process_id:
        return conflict

    bp = bp_lookup.get(conflict.brand_process_id)
    if not bp or not conflict.date_from:
        return conflict

    target_date = conflict.date_from
    demand_cell = demand_lookup.get((bp.id, target_date))

    # Assigned employees for this brand process
    assigned_emp_ids = [a.employee_id for a in assignments if a.brand_process_id == bp.id]
    assigned_employees = [
        employees_lookup[eid] for eid in assigned_emp_ids if eid in employees_lookup
    ]

    # 1. Rank backup candidates
    ranked_backups = rank_backup_candidates(
        bp=bp,
        target_date=target_date,
        employees=employees,
        assignments=assignments,
        roster_lookup=roster_lookup,
        holidays=holidays,
    )

    available_backups_for_msg = [(emp, desc) for emp, _, desc in ranked_backups]

    # 2. Build plain-language explanation
    explanation_msg = format_coverage_gap_message(
        conflict=conflict,
        bp=bp,
        target_date=target_date,
        demand_cell=demand_cell,
        roster_lookup=roster_lookup,
        assigned_employees=assigned_employees,
        leaves=leaves,
        available_backups=available_backups_for_msg,
    )

    # 3. Build ranked suggestions list
    suggestions: list[Suggestion] = []

    # Backup / Floater suggestions (top 3)
    for emp, score, desc in ranked_backups[:3]:
        suggestions.append(
            Suggestion(
                type=SuggestionType.ASSIGN_BACKUP,
                action=f"Assign {emp.full_name} ({desc.split(',')[0].strip()})",
                description=(
                    f"Assign {emp.full_name} to {bp.brand_name} - {bp.process_name} on "
                    f"{target_date.strftime('%a %d %b')}. Candidate status: {desc}."
                ),
                employee_id=emp.id,
                brand_process_id=bp.id,
                target_date=target_date,
                net_impact="Fixes 1 coverage gap, opens 0",
                score=score,
            )
        )

    # Weekly off swap suggestions
    swap_suggestions = generate_weekly_off_swap_suggestions(
        bp=bp,
        target_date=target_date,
        assigned_employees=assigned_employees,
        roster_lookup=roster_lookup,
        demand_lookup=demand_lookup,
        all_dates=all_dates,
    )
    suggestions.extend(swap_suggestions)

    # Leave shift proposal if root cause is leave
    if "LEAVE" in conflict.root_causes:
        for emp in assigned_employees:
            cell = roster_lookup.get((emp.id, target_date))
            if cell and cell.status in (RosterStatus.LEAVE, RosterStatus.COMP_OFF):
                suggestions.append(
                    Suggestion(
                        type=SuggestionType.SHIFT_LEAVE,
                        action=f"Request leave reschedule for {emp.full_name}",
                        description=(
                            f"Propose shifting {emp.full_name}'s approved leave on "
                            f"{target_date.strftime('%a %d %b')} with employee consent."
                        ),
                        employee_id=emp.id,
                        brand_process_id=bp.id,
                        target_date=target_date,
                        net_impact="Requires employee consent and manager re-approval",
                        score=15.0,
                    )
                )

    # Sort all suggestions descending by score
    suggestions.sort(key=lambda s: s.score, reverse=True)

    return Conflict(
        code=conflict.code,
        severity=conflict.severity,
        brand_process_id=conflict.brand_process_id,
        employee_id=conflict.employee_id,
        date_from=conflict.date_from,
        date_to=conflict.date_to,
        root_causes=conflict.root_causes,
        message=explanation_msg,
        suggestions=tuple(suggestions),
    )


def enrich_conflicts(
    conflicts: Sequence[Conflict],
    employees: Sequence[Employee],
    brand_processes: Sequence[BrandProcess],
    assignments: Sequence[Assignment],
    roster_cells: Sequence[RosterCell],
    demand_cells: Sequence[DemandCell] = (),
    holidays: Sequence[Holiday] = (),
    leaves: Sequence[EmployeeLeave] = (),
) -> list[Conflict]:
    """Enrich an entire sequence of conflicts with explanations and suggestions."""
    return [
        explain_conflict(
            conflict=c,
            employees=employees,
            brand_processes=brand_processes,
            assignments=assignments,
            roster_cells=roster_cells,
            demand_cells=demand_cells,
            holidays=holidays,
            leaves=leaves,
        )
        for c in conflicts
    ]
