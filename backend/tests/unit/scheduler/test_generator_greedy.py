"""Unit tests for pure-Python deterministic greedy baseline and fallback generator."""

from datetime import date

from app.scheduler.demand import build_demand_matrix
from app.scheduler.domain import (
    Assignment,
    AssignmentType,
    BrandProcess,
    CalendarType,
    ConflictCode,
    Employee,
    EmployeeLeave,
    GenerationInput,
    LeaveType,
    RosterStatus,
    SolverStatus,
    WeeklyOffMode,
)
from app.scheduler.generator_greedy import generate_greedy
from app.scheduler.supply import build_supply_matrix


def test_greedy_module_isolation() -> None:
    """Verify greedy generator has no dependencies on fastapi, sqlalchemy, or app.db."""
    forbidden = ["fastapi", "sqlalchemy", "app.api", "app.db", "app.models"]
    import app.scheduler.generator_greedy

    for global_val in vars(app.scheduler.generator_greedy).values():
        val_mod = getattr(global_val, "__module__", "")
        for f in forbidden:
            assert not val_mod.startswith(f), f"Generator leaks forbidden dependency: {val_mod}"


def test_greedy_standard_feasible_and_deterministic() -> None:
    """Test standard 2-person brand generation for a 7-day period and verify determinism."""
    bp = BrandProcess(
        id="bp-1",
        brand_id="b-1",
        brand_name="GlowCare",
        process_id="p-1",
        process_name="Customer Support",
        calendar_type=CalendarType.ALL_365,
        min_coverage_default=1,
    )
    e1 = Employee(id="emp-1", code="E1", full_name="Aarav", pod_id="p1", weekly_off_count=1)
    e2 = Employee(id="emp-2", code="E2", full_name="Bhavna", pod_id="p1", weekly_off_count=1)

    start = date(2026, 12, 7)  # Monday
    end = date(2026, 12, 13)  # Sunday (7 days total)

    assignments = (
        Assignment(employee_id="emp-1", brand_process_id="bp-1", type=AssignmentType.PRIMARY),
        Assignment(employee_id="emp-2", brand_process_id="bp-1", type=AssignmentType.PRIMARY),
    )

    demand = build_demand_matrix(brand_processes=[bp], start_date=start, end_date=end)
    supply = build_supply_matrix(employees=[e1, e2], start_date=start, end_date=end)

    gen_input = GenerationInput(
        month_start=start,
        month_end=end,
        employees=(e1, e2),
        brand_processes=(bp,),
        assignments=assignments,
        coverage_rules=(),
        holidays=(),
        supply_matrix=tuple(supply),
        demand_matrix=tuple(demand),
        random_seed=42,
    )

    out1 = generate_greedy(gen_input)
    assert out1.solver_status == SolverStatus.FALLBACK
    assert out1.slack_shortfall_total == 0
    assert out1.validation_result.is_valid is True
    assert out1.validation_result.blocking_count == 0

    # Determinism: identical outputs across runs
    out2 = generate_greedy(gen_input)
    assert out1.roster_cells == out2.roster_cells


def test_greedy_never_raises_infeasible_coverage_with_slack() -> None:
    """Test single-resource brand where coverage and weekly off conflict.

    Engine must NOT raise Infeasible; it returns the best roster with explicit slack shortfall.
    """
    bp = BrandProcess(
        id="bp-solo",
        brand_id="b-solo",
        brand_name="SoloBrand",
        process_id="p-1",
        process_name="CS",
        calendar_type=CalendarType.ALL_365,
        min_coverage_default=1,
    )
    emp = Employee(
        id="emp-solo", code="ES", full_name="Solo Operator", pod_id="p1", weekly_off_count=1
    )

    start = date(2026, 12, 7)
    end = date(2026, 12, 13)

    assignments = (
        Assignment(employee_id="emp-solo", brand_process_id="bp-solo", type=AssignmentType.PRIMARY),
    )

    demand = build_demand_matrix(brand_processes=[bp], start_date=start, end_date=end)
    supply = build_supply_matrix(employees=[emp], start_date=start, end_date=end)

    gen_input = GenerationInput(
        month_start=start,
        month_end=end,
        employees=(emp,),
        brand_processes=(bp,),
        assignments=assignments,
        coverage_rules=(),
        holidays=(),
        supply_matrix=tuple(supply),
        demand_matrix=tuple(demand),
        random_seed=42,
    )

    out = generate_greedy(gen_input)
    assert out.solver_status == SolverStatus.FALLBACK
    # Solo employee on 7-day operating brand must receive 1 weekly off, causing 1 shortfall day
    assert out.slack_shortfall_total == 1
    assert out.validation_result.is_valid is False
    assert out.validation_result.blocking_count > 0

    # Check that the gap has E001/E002 and explanation root cause E003 (WEEKLY_OFF_BREAKS_COVERAGE)
    coverage_conflicts = [
        c
        for c in out.validation_result.conflicts
        if c.code in (ConflictCode.E001, ConflictCode.E002)
    ]
    assert len(coverage_conflicts) == 1
    assert ConflictCode.E003 in coverage_conflicts[0].root_causes


def test_greedy_respects_fixed_mandatory_off_weekdays() -> None:
    """Verify H5: fixed mandatory weekly off weekday is strictly honoured."""
    bp = BrandProcess(
        id="bp-1",
        brand_id="b-1",
        brand_name="Brand",
        process_id="p-1",
        process_name="CS",
        calendar_type=CalendarType.ALL_365,
        min_coverage_default=1,
    )
    emp_fri = Employee(
        id="emp-fri",
        code="EF",
        full_name="Friday Off Staff",
        pod_id="p1",
        weekly_off_count=1,
        weekly_off_mode=WeeklyOffMode.FIXED_MANDATORY,
        fixed_weekly_off_weekdays=(4,),  # Friday
    )
    emp_other = Employee(
        id="emp-other",
        code="EO",
        full_name="Other Staff",
        pod_id="p1",
        weekly_off_count=1,
    )

    start = date(2026, 12, 7)  # Monday
    end = date(2026, 12, 20)  # 2 full weeks

    assignments = (
        Assignment(employee_id="emp-fri", brand_process_id="bp-1", type=AssignmentType.PRIMARY),
        Assignment(employee_id="emp-other", brand_process_id="bp-1", type=AssignmentType.PRIMARY),
    )

    demand = build_demand_matrix(brand_processes=[bp], start_date=start, end_date=end)
    supply = build_supply_matrix(employees=[emp_fri, emp_other], start_date=start, end_date=end)

    gen_input = GenerationInput(
        month_start=start,
        month_end=end,
        employees=(emp_fri, emp_other),
        brand_processes=(bp,),
        assignments=assignments,
        coverage_rules=(),
        holidays=(),
        supply_matrix=tuple(supply),
        demand_matrix=tuple(demand),
    )

    out = generate_greedy(gen_input)
    assert out.solver_status == SolverStatus.FALLBACK

    # Check that emp_fri has WEEKLY_OFF on all Fridays (Dec 11 and Dec 18)
    fri_1 = date(2026, 12, 11)
    fri_2 = date(2026, 12, 18)
    for cell in out.roster_cells:
        if cell.employee_id == "emp-fri" and cell.date in (fri_1, fri_2):
            assert cell.status == RosterStatus.WEEKLY_OFF


def test_greedy_consecutive_days_and_tail_carry_in() -> None:
    """Verify H3: consecutive days limit (<= 6) is enforced, respecting carry-in."""
    bp = BrandProcess(
        id="bp-1",
        brand_id="b-1",
        brand_name="Brand",
        process_id="p-1",
        process_name="CS",
        calendar_type=CalendarType.ALL_365,
        min_coverage_default=1,
    )
    emp = Employee(
        id="emp-1",
        code="E1",
        full_name="Staff",
        pod_id="p1",
        weekly_off_count=1,
        max_consecutive_days=6,
    )

    # Dec 1 (Tuesday) to Dec 10 (Thursday)
    start = date(2026, 12, 1)
    end = date(2026, 12, 10)

    assignments = (
        Assignment(employee_id="emp-1", brand_process_id="bp-1", type=AssignmentType.PRIMARY),
    )
    demand = build_demand_matrix(brand_processes=[bp], start_date=start, end_date=end)
    supply = build_supply_matrix(employees=[emp], start_date=start, end_date=end)

    # Carry in 5 work days from November tail
    gen_input = GenerationInput(
        month_start=start,
        month_end=end,
        employees=(emp,),
        brand_processes=(bp,),
        assignments=assignments,
        coverage_rules=(),
        holidays=(),
        supply_matrix=tuple(supply),
        demand_matrix=tuple(demand),
        previous_tail_work_days={"emp-1": 5},
    )

    out = generate_greedy(gen_input)
    assert out.solver_status == SolverStatus.FALLBACK

    # With 5 carry-in days, working Dec 1 brings total to 6, so Dec 2 must be an off
    cells_by_date = {c.date: c for c in out.roster_cells if c.employee_id == "emp-1"}
    assert cells_by_date[date(2026, 12, 2)].status == RosterStatus.WEEKLY_OFF

    # Validate that no E005 conflict exists
    consec_conflicts = [c for c in out.validation_result.conflicts if c.code == ConflictCode.E005]
    assert len(consec_conflicts) == 0


def test_greedy_fixed_cells_immutable() -> None:
    """Verify H1: locked leave and comp-off cells are preserved unchanged."""
    bp = BrandProcess(
        id="bp-1",
        brand_id="b-1",
        brand_name="Brand",
        process_id="p-1",
        process_name="CS",
        calendar_type=CalendarType.ALL_365,
        min_coverage_default=1,
    )
    emp = Employee(id="emp-1", code="E1", full_name="Staff", pod_id="p1", weekly_off_count=1)

    start = date(2026, 12, 7)
    end = date(2026, 12, 13)

    leave_date = date(2026, 12, 9)
    leave = EmployeeLeave(
        employee_id="emp-1",
        start_date=leave_date,
        end_date=leave_date,
        type=LeaveType.PLANNED,
    )

    demand = build_demand_matrix(brand_processes=[bp], start_date=start, end_date=end)
    supply = build_supply_matrix(
        employees=[emp],
        start_date=start,
        end_date=end,
        leaves=[leave],
    )

    gen_input = GenerationInput(
        month_start=start,
        month_end=end,
        employees=(emp,),
        brand_processes=(bp,),
        assignments=(Assignment(employee_id="emp-1", brand_process_id="bp-1"),),
        coverage_rules=(),
        holidays=(),
        leaves=(leave,),
        supply_matrix=tuple(supply),
        demand_matrix=tuple(demand),
    )

    out = generate_greedy(gen_input)
    cell_leave = next(
        c for c in out.roster_cells if c.employee_id == "emp-1" and c.date == leave_date
    )
    assert cell_leave.status == RosterStatus.LEAVE
    assert cell_leave.is_locked is True
