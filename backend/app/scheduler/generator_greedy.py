"""Pure-Python deterministic greedy baseline and fallback roster generator.

Conforms to SCHEDULING_ENGINE.md §6 and AGENTS.md architectural rules:
- Zero imports from api, db, models, fastapi, sqlalchemy, or external solvers.
- Operates strictly on scheduler domain dataclasses.
- Assigns weekly offs to days with most slack in each employee's assigned brand-processes.
- Strictly respects hard constraints H1–H5 (fixed cells, weekly offs, consecutive days,
  cell validity, fixed mandatory weekdays).
- Runs local repair to mitigate coverage shortfalls.
- Runs independent validation (validator.py) and explanation enrichment (explain.py).
- Reports solver_status = SolverStatus.FALLBACK.
"""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import date, timedelta

from app.scheduler.calendar import has_applicable_holiday, is_operating_day
from app.scheduler.domain import (
    Assignment,
    AssignmentType,
    Employee,
    GenerationInput,
    GenerationOutput,
    RosterCell,
    RosterStatus,
    SolverStatus,
    ValidationResult,
    WeeklyOffMode,
)
from app.scheduler.explain import enrich_conflicts
from app.scheduler.validator import partition_into_weeks, validate_roster


def generate_greedy(gen_input: GenerationInput) -> GenerationOutput:
    """Generate monthly roster using a deterministic greedy heuristic with local repair."""
    start_time = time.perf_counter()

    month_start = gen_input.month_start
    month_end = gen_input.month_end

    if month_start > month_end:
        raise ValueError(f"month_start ({month_start}) cannot be after month_end ({month_end})")

    # 1. Build ordered dates
    all_dates: list[date] = []
    curr = month_start
    one_day = timedelta(days=1)
    while curr <= month_end:
        all_dates.append(curr)
        curr += one_day

    # 2. Stable sorting of inputs
    sorted_employees = sorted(gen_input.employees, key=lambda e: e.id)
    sorted_bps = sorted(gen_input.brand_processes, key=lambda bp: bp.id)
    bp_lookup = {bp.id: bp for bp in sorted_bps}

    demand_lookup = {(c.brand_process_id, c.date): c for c in gen_input.demand_matrix}
    supply_lookup = {(c.employee_id, c.date): c for c in gen_input.supply_matrix}

    # Map brand_process_id -> assigned employees
    bp_assignments: dict[str, list[Assignment]] = defaultdict(list)
    emp_assignments: dict[str, list[Assignment]] = defaultdict(list)
    for a in gen_input.assignments:
        bp_assignments[a.brand_process_id].append(a)
        emp_assignments[a.employee_id].append(a)

    # 3. Initialize grid status tracking
    # cell_status: (employee_id, date) -> RosterStatus
    cell_status: dict[tuple[str, date], RosterStatus] = {}
    is_fixed_cell: dict[tuple[str, date], bool] = {}

    for emp in sorted_employees:
        for d in all_dates:
            supply_cell = supply_lookup.get((emp.id, d))
            if supply_cell and supply_cell.is_locked and supply_cell.locked_status:
                cell_status[(emp.id, d)] = supply_cell.locked_status
                is_fixed_cell[(emp.id, d)] = True
            else:
                is_fixed_cell[(emp.id, d)] = False

    weeks = partition_into_weeks(all_dates)

    # 4. Mandatory Off Weekdays (H5)
    for emp in sorted_employees:
        if emp.weekly_off_mode == WeeklyOffMode.FIXED_MANDATORY and emp.fixed_weekly_off_weekdays:
            for d in all_dates:
                if not is_fixed_cell[(emp.id, d)] and d.weekday() in emp.fixed_weekly_off_weekdays:
                    cell_status[(emp.id, d)] = RosterStatus.WEEKLY_OFF

    # 5. Greedy Weekly Off Assignment (H2, H4)
    # Assign weekly offs to days with most slack in each employee's assigned brand-processes
    for emp in sorted_employees:
        asgns = emp_assignments.get(emp.id, [])

        for week_dates in weeks:
            week_len = len(week_dates)
            if week_len < 4:
                # Pro-rating: Partial edge week with < 4 days gets 0 required weekly offs
                continue

            required_offs = emp.weekly_off_count

            # Count existing weekly offs in this week
            current_offs = sum(
                1 for d in week_dates if cell_status.get((emp.id, d)) == RosterStatus.WEEKLY_OFF
            )
            needed_offs = max(0, required_offs - current_offs)
            if needed_offs == 0:
                continue

            # Candidate days for placing weekly offs (non-fixed, currently unassigned or work)
            candidate_days = [
                d
                for d in week_dates
                if not is_fixed_cell[(emp.id, d)]
                and cell_status.get((emp.id, d)) != RosterStatus.WEEKLY_OFF
            ]

            # Score each candidate day: higher score = better day for employee to take off
            def score_candidate_off_day(
                cand_date: date,
                target_emp: Employee = emp,
                target_asgns: list[Assignment] = asgns,
            ) -> tuple[float, int, int]:
                total_slack = 0.0

                for a in target_asgns:
                    bp = bp_lookup.get(a.brand_process_id)
                    if not bp:
                        continue

                    demand_c = demand_lookup.get((bp.id, cand_date))
                    req = demand_c.required_headcount if demand_c else 0

                    if req == 0:
                        # Non-operating or zero-demand day -> optimal day for off
                        total_slack += 100.0
                    else:
                        # Count other assigned colleagues available to work on this day
                        other_assigned = [
                            other_a.employee_id
                            for other_a in bp_assignments.get(bp.id, [])
                            if other_a.employee_id != target_emp.id
                        ]
                        other_available = sum(
                            1
                            for other_id in other_assigned
                            if cell_status.get((other_id, cand_date)) != RosterStatus.WEEKLY_OFF
                            and not (
                                is_fixed_cell.get((other_id, cand_date), False)
                                and cell_status.get((other_id, cand_date))
                                not in (RosterStatus.WORK, RosterStatus.HOLIDAY_WORK)
                            )
                        )
                        slack = other_available - req
                        multiplier = 2.0 if a.type == AssignmentType.PRIMARY else 1.0
                        total_slack += slack * multiplier

                # Soft preferences: preference bonus
                pref_bonus = 0
                if (
                    cand_date.weekday() in target_emp.preferred_weekly_off_weekdays
                    or cand_date in target_emp.preferred_off_dates
                ):
                    pref_bonus += 10

                # Sunday preference for weekend off balance
                if cand_date.weekday() == 6:
                    pref_bonus += 2

                # Stable integer date key for deterministic tie-break
                date_key = cand_date.toordinal()
                return (total_slack + pref_bonus, pref_bonus, date_key)

            # Sort candidate days descending by score
            scored_candidates = sorted(candidate_days, key=score_candidate_off_day, reverse=True)

            for d in scored_candidates[:needed_offs]:
                cell_status[(emp.id, d)] = RosterStatus.WEEKLY_OFF

    # 6. Fill all remaining non-fixed cells with WORK (or HOLIDAY_WORK)
    for emp in sorted_employees:
        asgns = emp_assignments.get(emp.id, [])
        for d in all_dates:
            if (emp.id, d) not in cell_status:
                # Check if date is a holiday and any assigned brand process operates
                is_holiday = has_applicable_holiday(
                    gen_input.holidays, brand_id="", target_date=d
                ) or any(h.date == d for h in gen_input.holidays)

                any_operating = any(
                    is_operating_day(bp_lookup[a.brand_process_id], d, gen_input.holidays)
                    for a in asgns
                    if a.brand_process_id in bp_lookup
                )

                if is_holiday and any_operating:
                    cell_status[(emp.id, d)] = RosterStatus.HOLIDAY_WORK
                else:
                    cell_status[(emp.id, d)] = RosterStatus.WORK

    # 7. Consecutive Days Enforcement & Repair (H3)
    tail_days = gen_input.previous_tail_work_days
    for emp in sorted_employees:
        max_consec = emp.max_consecutive_days
        consec_streak = tail_days.get(emp.id, 0)

        for d in all_dates:
            st = cell_status[(emp.id, d)]
            if st in (RosterStatus.WORK, RosterStatus.HOLIDAY_WORK):
                consec_streak += 1
                if consec_streak > max_consec and not is_fixed_cell[(emp.id, d)]:
                    cell_status[(emp.id, d)] = RosterStatus.WEEKLY_OFF
                    consec_streak = 0
            else:
                consec_streak = 0

    # 8. Local Coverage Repair Pass
    # If a brand-process has a gap on date d, see if an assigned employee off on d
    # can swap their weekly off to a surplus day in the same week
    for bp in sorted_bps:
        assigned_emps = [a.employee_id for a in bp_assignments.get(bp.id, [])]
        if not assigned_emps:
            continue

        for week_dates in weeks:
            for d in week_dates:
                demand_c = demand_lookup.get((bp.id, d))
                req = demand_c.required_headcount if demand_c else 0
                if req <= 0:
                    continue

                # Current working headcount
                working_count = sum(
                    1
                    for eid in assigned_emps
                    if cell_status.get((eid, d)) in (RosterStatus.WORK, RosterStatus.HOLIDAY_WORK)
                )

                if working_count < req:
                    # Shortfall on date d! Find an assigned employee who has WEEKLY_OFF on d
                    for eid in assigned_emps:
                        emp_obj = next((e for e in sorted_employees if e.id == eid), None)
                        if not emp_obj:
                            continue

                        if cell_status.get(
                            (eid, d)
                        ) == RosterStatus.WEEKLY_OFF and not is_fixed_cell.get((eid, d), False):
                            # Cannot swap if d is a mandatory fixed off day for this employee
                            if (
                                emp_obj.weekly_off_mode == WeeklyOffMode.FIXED_MANDATORY
                                and d.weekday() in emp_obj.fixed_weekly_off_weekdays
                            ):
                                continue

                            # Look for an alternate day in the same week that has surplus coverage
                            for alt_d in week_dates:
                                if alt_d == d:
                                    continue
                                if is_fixed_cell.get((eid, alt_d), False):
                                    continue
                                if cell_status.get((eid, alt_d)) not in (
                                    RosterStatus.WORK,
                                    RosterStatus.HOLIDAY_WORK,
                                ):
                                    continue

                                # Check if swapping working day to alt_d preserves coverage on alt_d
                                alt_demand_c = demand_lookup.get((bp.id, alt_d))
                                alt_req = alt_demand_c.required_headcount if alt_demand_c else 0
                                alt_working_count = sum(
                                    1
                                    for other_id in assigned_emps
                                    if cell_status.get((other_id, alt_d))
                                    in (RosterStatus.WORK, RosterStatus.HOLIDAY_WORK)
                                )

                                if alt_working_count > alt_req:
                                    # Safe swap! Perform swap
                                    cell_status[(eid, d)] = RosterStatus.WORK
                                    cell_status[(eid, alt_d)] = RosterStatus.WEEKLY_OFF
                                    working_count += 1
                                    break

                        if working_count >= req:
                            break

    # 9. Build final RosterCell tuples
    roster_cells: list[RosterCell] = []
    for emp in sorted_employees:
        for d in all_dates:
            st = cell_status[(emp.id, d)]
            is_locked = is_fixed_cell[(emp.id, d)]
            roster_cells.append(
                RosterCell(
                    employee_id=emp.id,
                    date=d,
                    status=st,
                    is_locked=is_locked,
                )
            )

    solve_time = time.perf_counter() - start_time

    # 10. Independent Validation
    validation_result, coverage_cells = validate_roster(
        roster_cells=roster_cells,
        demand_cells=gen_input.demand_matrix,
        supply_cells=gen_input.supply_matrix,
        employees=gen_input.employees,
        brand_processes=gen_input.brand_processes,
        assignments=gen_input.assignments,
        holidays=gen_input.holidays,
        leaves=gen_input.leaves,
        previous_tail_work_days=gen_input.previous_tail_work_days,
    )

    # 11. Enrich conflicts with plain English explanations and actionable suggestions
    enriched_conflicts = enrich_conflicts(
        conflicts=validation_result.conflicts,
        employees=gen_input.employees,
        brand_processes=gen_input.brand_processes,
        assignments=gen_input.assignments,
        roster_cells=roster_cells,
        demand_cells=gen_input.demand_matrix,
        holidays=gen_input.holidays,
        leaves=gen_input.leaves,
    )

    enriched_validation_result = ValidationResult.from_conflicts(tuple(enriched_conflicts))

    # Calculate slack shortfall total
    slack_total = sum(c.shortfall for c in coverage_cells)

    return GenerationOutput(
        roster_cells=tuple(roster_cells),
        coverage_cells=tuple(coverage_cells),
        validation_result=enriched_validation_result,
        solver_status=SolverStatus.FALLBACK,
        solve_time_seconds=solve_time,
        objective_value=float(slack_total * 100_000),
        slack_shortfall_total=slack_total,
    )
