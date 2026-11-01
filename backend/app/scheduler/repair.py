"""Local roster repair engine.

Re-solves an impacted window (dates and eligible employees) while strictly
locking all unaffected cells outside the window to their current status.
Conforms to SCHEDULING_ENGINE.md Section 10 and REQUIREMENTS.md FR-CH-05.

Non-negotiable architectural rule:
Zero external framework imports (FastAPI, SQLAlchemy, Pydantic, DB).
Operates exclusively on scheduler domain types and standard library.
"""

from __future__ import annotations

import time
from datetime import date

from app.scheduler.domain import (
    GenerationInput,
    RepairInput,
    RepairOutput,
    RosterCell,
    SolverStatus,
)
from app.scheduler.generator_cpsat import generate_cpsat
from app.scheduler.generator_greedy import generate_greedy
from app.scheduler.supply import build_supply_matrix


def repair_roster(repair_input: RepairInput) -> RepairOutput:
    """Execute local repair around specified dates and employees with all other cells locked."""
    start_time = time.perf_counter()
    repair_dates_set: set[date] = set(repair_input.repair_dates)
    repair_emp_set: set[str] | None = (
        set(repair_input.repair_employee_ids) if repair_input.repair_employee_ids else None
    )

    # 1. Identify which cells to lock
    locked_cells: list[RosterCell] = []
    current_lookup: dict[tuple[str, date], RosterCell] = {}

    for cell in repair_input.current_roster_cells:
        current_lookup[(cell.employee_id, cell.date)] = cell
        in_repair_window = (cell.date in repair_dates_set) and (
            repair_emp_set is None or cell.employee_id in repair_emp_set
        )

        if not in_repair_window:
            # Strictly lock cells outside the impacted window to their current assignment
            locked_cells.append(
                RosterCell(
                    employee_id=cell.employee_id,
                    date=cell.date,
                    status=cell.status,
                    is_locked=True,
                    note=cell.note or "Locked outside repair window",
                )
            )
        elif cell.is_locked:
            # Honor explicit manager locks within the repair window
            locked_cells.append(cell)

    # 2. Re-evaluate supply matrix with locked cells applied
    scoped_supply = build_supply_matrix(
        employees=repair_input.gen_input.employees,
        start_date=repair_input.gen_input.month_start,
        end_date=repair_input.gen_input.month_end,
        assignments=repair_input.gen_input.assignments,
        brand_processes=repair_input.gen_input.brand_processes,
        holidays=repair_input.gen_input.holidays,
        leaves=repair_input.gen_input.leaves,
        locked_cells=locked_cells,
    )

    # 3. Assemble scoped GenerationInput
    scoped_gen_input = GenerationInput(
        month_start=repair_input.gen_input.month_start,
        month_end=repair_input.gen_input.month_end,
        employees=repair_input.gen_input.employees,
        brand_processes=repair_input.gen_input.brand_processes,
        assignments=repair_input.gen_input.assignments,
        coverage_rules=repair_input.gen_input.coverage_rules,
        holidays=repair_input.gen_input.holidays,
        leaves=repair_input.gen_input.leaves,
        locked_cells=tuple(locked_cells),
        supply_matrix=tuple(scoped_supply),
        demand_matrix=repair_input.gen_input.demand_matrix,
        random_seed=repair_input.gen_input.random_seed,
        time_limit_seconds=repair_input.gen_input.time_limit_seconds,
        previous_tail_work_days=repair_input.gen_input.previous_tail_work_days,
        initial_compoff_balances=repair_input.gen_input.initial_compoff_balances,
    )

    # 4. Re-solve (CP-SAT with fallback to Greedy heuristic)
    out = generate_greedy(scoped_gen_input) if repair_input.use_fallback else None
    if out is None:
        try:
            out = generate_cpsat(scoped_gen_input)
            if out.solver_status == SolverStatus.FALLBACK:
                out = generate_greedy(scoped_gen_input)
        except Exception:
            out = generate_greedy(scoped_gen_input)

    # 5. Extract diff: identify cells in the repair window that changed status
    repaired_cells: list[RosterCell] = []
    for new_cell in out.roster_cells:
        prev = current_lookup.get((new_cell.employee_id, new_cell.date))
        if prev and prev.status != new_cell.status:
            repaired_cells.append(new_cell)

    elapsed = time.perf_counter() - start_time

    return RepairOutput(
        repaired_cells=tuple(repaired_cells),
        all_roster_cells=out.roster_cells,
        coverage_cells=out.coverage_cells,
        validation_result=out.validation_result,
        solver_status=out.solver_status,
        solve_time_seconds=elapsed,
        changed_cells_count=len(repaired_cells),
    )
