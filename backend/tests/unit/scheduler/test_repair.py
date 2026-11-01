"""Unit tests for the pure Python local repair engine (Task T-516)."""

import datetime as dt

from app.scheduler.demand import build_demand_matrix
from app.scheduler.domain import (
    Assignment,
    AssignmentType,
    BrandProcess,
    CalendarType,
    CoverageRule,
    Employee,
    GenerationInput,
    Holiday,
    RepairInput,
    RosterCell,
    RosterStatus,
    SolverStatus,
)
from app.scheduler.repair import repair_roster


def test_repair_roster_locks_unaffected_cells() -> None:
    """Test that local repair strictly locks all cells outside the repair window."""
    start_d = dt.date(2026, 12, 1)
    end_d = dt.date(2026, 12, 7)

    e1 = Employee(id="emp-1", code="E01", full_name="Alpha", pod_id="p1", weekly_off_count=1)
    e2 = Employee(id="emp-2", code="E02", full_name="Beta", pod_id="p1", weekly_off_count=1)
    employees = (e1, e2)

    bp = BrandProcess(
        id="bp-1",
        brand_id="b-1",
        brand_name="Brand A",
        process_id="pr-1",
        process_name="Process 1",
        calendar_type=CalendarType.ALL_365,
        min_coverage_default=1,
    )
    brand_processes = (bp,)

    asg1 = Assignment(
        employee_id="emp-1",
        brand_process_id="bp-1",
        type=AssignmentType.PRIMARY,
    )
    asg2 = Assignment(
        employee_id="emp-2",
        brand_process_id="bp-1",
        type=AssignmentType.PRIMARY,
    )
    assignments = (asg1, asg2)

    coverage_rules: tuple[CoverageRule, ...] = ()
    holidays: tuple[Holiday, ...] = ()

    demand_matrix = tuple(
        build_demand_matrix(
            brand_processes=brand_processes,
            start_date=start_d,
            end_date=end_d,
            holidays=holidays,
            rules=coverage_rules,
        )
    )

    # Initial roster: emp-1 works Dec 1-6, off Dec 7. emp-2 off Dec 1, works Dec 2-7.
    # Suppose both are off on Dec 4 (causing a gap on Dec 4!)
    current_cells: list[RosterCell] = []
    dates = [start_d + dt.timedelta(days=i) for i in range(7)]
    for d in dates:
        # emp-1 off on Dec 4 and Dec 7
        st1 = RosterStatus.WEEKLY_OFF if d == dt.date(2026, 12, 4) else RosterStatus.WORK
        # emp-2 off on Dec 4
        st2 = RosterStatus.WEEKLY_OFF if d == dt.date(2026, 12, 4) else RosterStatus.WORK
        current_cells.append(RosterCell(employee_id="emp-1", date=d, status=st1))
        current_cells.append(RosterCell(employee_id="emp-2", date=d, status=st2))

    gen_input = GenerationInput(
        month_start=start_d,
        month_end=end_d,
        employees=employees,
        brand_processes=brand_processes,
        assignments=assignments,
        coverage_rules=coverage_rules,
        holidays=holidays,
        leaves=(),
        locked_cells=(),
        supply_matrix=(),
        demand_matrix=demand_matrix,
        random_seed=42,
        time_limit_seconds=10.0,
    )

    # Repair only Dec 4 (the gap date)
    repair_input = RepairInput(
        gen_input=gen_input,
        current_roster_cells=tuple(current_cells),
        repair_dates=(dt.date(2026, 12, 4),),
        repair_employee_ids=("emp-1", "emp-2"),
        use_fallback=True,
    )

    repair_out = repair_roster(repair_input)
    assert repair_out.solver_status in (
        SolverStatus.OPTIMAL,
        SolverStatus.FEASIBLE,
        SolverStatus.FALLBACK,
    )

    # Verify all cells outside Dec 4 remained completely identical to current_cells
    repaired_lookup = {(c.employee_id, c.date): c for c in repair_out.all_roster_cells}
    for cell in current_cells:
        if cell.date != dt.date(2026, 12, 4):
            repaired_cell = repaired_lookup[(cell.employee_id, cell.date)]
            assert repaired_cell.status == cell.status, (
                f"Cell for {cell.employee_id} on {cell.date} changed outside repair window!"
            )
