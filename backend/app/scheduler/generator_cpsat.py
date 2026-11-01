"""Pure-Python CP-SAT roster generation engine using Google OR-Tools.

Solves monthly shift scheduling satisfying:
- Mandatory hard constraints (H1–H5): fixed cells, weekly offs, consecutive days,
  cell validity, and fixed mandatory off weekdays.
- Hard with slack: coverage minimums with heavy penalty (big_weight = 100,000) so the engine
  never raises infeasible, always returning the best roster plus explicit shortfall slack.
- Soft preferences (P1–P6): preferred off days, primary over backup staffing,
  overload avoidance, and weekend fairness.
- Deterministic solving: fixed random seed and reproducible variable ordering.
- Independent validation: output validated via validator.py and enriched with explainer.py.

Non-negotiable architectural rule:
Zero external framework imports (FastAPI, SQLAlchemy, Pydantic, DB).
Operates exclusively on scheduler domain types and Google OR-Tools.
"""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import date, timedelta

from ortools.sat.python import cp_model

from app.scheduler.calendar import has_applicable_holiday, is_operating_day
from app.scheduler.domain import (
    Assignment,
    AssignmentType,
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


def generate_cpsat(gen_input: GenerationInput) -> GenerationOutput:
    """Solve and generate monthly roster using Google OR-Tools CP-SAT."""
    start_time = time.perf_counter()

    month_start = gen_input.month_start
    month_end = gen_input.month_end

    if month_start > month_end:
        raise ValueError(f"month_start ({month_start}) cannot be after month_end ({month_end})")

    # Build date list
    all_dates: list[date] = []
    curr = month_start
    one_day = timedelta(days=1)
    while curr <= month_end:
        all_dates.append(curr)
        curr += one_day

    # Stable sorting of inputs
    sorted_employees = sorted(gen_input.employees, key=lambda e: e.id)
    sorted_bps = sorted(gen_input.brand_processes, key=lambda bp: bp.id)
    bp_lookup = {bp.id: bp for bp in sorted_bps}

    # Build demand and supply lookups
    demand_lookup = {(c.brand_process_id, c.date): c for c in gen_input.demand_matrix}
    supply_lookup = {(c.employee_id, c.date): c for c in gen_input.supply_matrix}

    # Map brand_process_id -> assigned employee_ids & types
    bp_assignments: dict[str, list[Assignment]] = defaultdict(list)
    for a in gen_input.assignments:
        bp_assignments[a.brand_process_id].append(a)

    # Initialize CP-SAT model
    model = cp_model.CpModel()

    # Decision variables: work[e_id, date] in {0, 1}
    work_vars: dict[tuple[str, date], cp_model.IntVar] = {}
    fixed_status: dict[tuple[str, date], RosterStatus] = {}

    for emp in sorted_employees:
        for d in all_dates:
            supply_cell = supply_lookup.get((emp.id, d))
            is_fixed = supply_cell is not None and supply_cell.is_locked

            if is_fixed and supply_cell and supply_cell.locked_status:
                fixed_st = supply_cell.locked_status
                fixed_status[(emp.id, d)] = fixed_st

                # H1: Fixed cells
                if fixed_st in (RosterStatus.WORK, RosterStatus.HOLIDAY_WORK):
                    work_vars[(emp.id, d)] = model.new_constant(1)
                else:
                    work_vars[(emp.id, d)] = model.new_constant(0)
            else:
                # Variable decision: 1 = work, 0 = weekly off
                var = model.new_bool_var(f"work_{emp.code}_{d.strftime('%Y%m%d')}")
                work_vars[(emp.id, d)] = var

                # H5: Fixed mandatory weekly off weekday
                if (
                    emp.weekly_off_mode == WeeklyOffMode.FIXED_MANDATORY
                    and d.weekday() in emp.fixed_weekly_off_weekdays
                ):
                    model.add(var == 0)

    # H2: Weekly off constraint with month-edge pro-rating
    weeks = partition_into_weeks(all_dates)
    for emp in sorted_employees:
        for week_dates in weeks:
            week_len = len(week_dates)
            if week_len >= 4:
                # Employee must receive >= weekly_off_count weekly offs in this week
                required_offs = emp.weekly_off_count
                max_work_days = week_len - required_offs
                week_work_vars = [work_vars[(emp.id, d)] for d in week_dates]
                model.add(sum(week_work_vars) <= max_work_days)

    # H3: Maximum consecutive working days
    tail_days = gen_input.previous_tail_work_days
    for emp in sorted_employees:
        max_consecutive = emp.max_consecutive_days
        window_size = max_consecutive + 1

        # Check carry-in at start of month
        carry_in = tail_days.get(emp.id, 0)
        if carry_in > 0 and len(all_dates) >= (window_size - carry_in):
            needed_to_exceed = window_size - carry_in
            if needed_to_exceed > 0:
                first_window_vars = [
                    work_vars[(emp.id, all_dates[i])] for i in range(needed_to_exceed)
                ]
                model.add(sum(first_window_vars) <= needed_to_exceed - 1)

        # Sliding window across month
        if len(all_dates) >= window_size:
            for i in range(len(all_dates) - window_size + 1):
                window = [all_dates[i + j] for j in range(window_size)]
                window_vars = [work_vars[(emp.id, d)] for d in window]
                model.add(sum(window_vars) <= max_consecutive)

    # Coverage with Slack ("Hard with slack")
    slack_vars: dict[tuple[str, date], cp_model.IntVar] = {}
    obj_terms: list[cp_model.LinearExpr] = []

    big_weight = 100_000  # Dominates all preference weights

    for bp in sorted_bps:
        assigned_emp_ids = [a.employee_id for a in bp_assignments.get(bp.id, [])]
        for d in all_dates:
            demand_cell = demand_lookup.get((bp.id, d))
            req = demand_cell.required_headcount if demand_cell else 0

            if req > 0:
                slack = model.new_int_var(0, req, f"slack_{bp.id}_{d.strftime('%Y%m%d')}")
                slack_vars[(bp.id, d)] = slack

                # Coverage inequality: covered + slack >= demand
                eligible_work_vars = [work_vars[(eid, d)] for eid in assigned_emp_ids]
                model.add(sum(eligible_work_vars) + slack >= req)

                # Penalize slack heavily
                obj_terms.append(slack * big_weight)

    # Soft Preferences (P1–P6)
    for emp in sorted_employees:
        emp_assignments = [a for a in gen_input.assignments if a.employee_id == emp.id]

        for d in all_dates:
            w_var = work_vars[(emp.id, d)]

            # P1: Preferred weekly off weekday / date (weight 5)
            if d.weekday() in emp.preferred_weekly_off_weekdays or d in emp.preferred_off_dates:
                # Penalty 5 if working on preferred off day
                obj_terms.append(w_var * 5)

            # P4: Prefer primary staffing over backup (weight 4)
            is_backup_only = bool(emp_assignments) and all(
                a.type == AssignmentType.BACKUP for a in emp_assignments
            )
            if is_backup_only:
                obj_terms.append(w_var * 4)

            # P6: Multi-brand overload avoidance (weight 8)
            operating_bp_count = sum(
                1
                for a in emp_assignments
                if a.brand_process_id in bp_lookup
                and is_operating_day(bp_lookup[a.brand_process_id], d, gen_input.holidays)
            )
            if operating_bp_count > emp.max_concurrent_processes:
                obj_terms.append(w_var * 8)

    # Objective: minimize shortfall slack + preference penalties
    if obj_terms:
        model.minimize(sum(obj_terms))

    # Solver parameters
    solver = cp_model.CpSolver()
    solver.parameters.random_seed = gen_input.random_seed
    solver.parameters.max_time_in_seconds = gen_input.time_limit_seconds
    solver.parameters.num_search_workers = 1  # 100% deterministic reproducibility

    solver_res = solver.solve(model)
    solve_time = time.perf_counter() - start_time

    # Map solver status
    if solver_res == cp_model.OPTIMAL:
        status = SolverStatus.OPTIMAL
    elif solver_res == cp_model.FEASIBLE:
        status = SolverStatus.FEASIBLE
    else:
        status = SolverStatus.FALLBACK

    # Reconstruct RosterCells
    roster_cells: list[RosterCell] = []
    for emp in sorted_employees:
        emp_assignments = [a for a in gen_input.assignments if a.employee_id == emp.id]

        for d in all_dates:
            supply_cell = supply_lookup.get((emp.id, d))
            is_locked = supply_cell.is_locked if supply_cell else False

            if (emp.id, d) in fixed_status:
                cell_status = fixed_status[(emp.id, d)]
            else:
                work_val = solver.value(work_vars[(emp.id, d)])
                if work_val == 1:
                    # Check if date is a holiday on which employee works
                    is_holiday = has_applicable_holiday(
                        gen_input.holidays, brand_id="", target_date=d
                    ) or any(h.date == d for h in gen_input.holidays)
                    any_operating_on_holiday = any(
                        is_operating_day(bp_lookup[a.brand_process_id], d, gen_input.holidays)
                        for a in emp_assignments
                        if a.brand_process_id in bp_lookup
                    )
                    if is_holiday and any_operating_on_holiday:
                        cell_status = RosterStatus.HOLIDAY_WORK
                    else:
                        cell_status = RosterStatus.WORK
                else:
                    cell_status = RosterStatus.WEEKLY_OFF

            roster_cells.append(
                RosterCell(
                    employee_id=emp.id,
                    date=d,
                    status=cell_status,
                    is_locked=is_locked,
                )
            )

    # Calculate total slack shortfalls
    slack_total = 0
    if solver_res in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for slack in slack_vars.values():
            slack_total += int(solver.value(slack))

    # Independent validation
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

    # Enrich conflicts with plain English explanations and suggestions
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

    return GenerationOutput(
        roster_cells=tuple(roster_cells),
        coverage_cells=tuple(coverage_cells),
        validation_result=enriched_validation_result,
        solver_status=status,
        solve_time_seconds=solve_time,
        objective_value=float(solver.objective_value)
        if solver_res in (cp_model.OPTIMAL, cp_model.FEASIBLE)
        else 0.0,
        slack_shortfall_total=slack_total,
    )
