"""Unit tests for pure-Python CP-SAT roster generator using Google OR-Tools."""

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
from app.scheduler.generator_cpsat import generate_cpsat
from app.scheduler.supply import build_supply_matrix


def test_generator_module_isolation() -> None:
    """Verify CP-SAT generator has no dependencies on fastapi, sqlalchemy, or app.db."""
    forbidden = ["fastapi", "sqlalchemy", "app.api", "app.db", "app.models"]
    import app.scheduler.generator_cpsat

    for global_val in vars(app.scheduler.generator_cpsat).values():
        val_mod = getattr(global_val, "__module__", "")
        for f in forbidden:
            assert not val_mod.startswith(f), f"Generator leaks forbidden dependency: {val_mod}"


def test_cpsat_solver_feasible_and_deterministic() -> None:
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

    out1 = generate_cpsat(gen_input)
    assert out1.solver_status == SolverStatus.OPTIMAL
    assert out1.slack_shortfall_total == 0
    assert out1.validation_result.is_valid is True
    assert out1.validation_result.blocking_count == 0

    # Test determinism: second run with same seed must yield exact same assignments
    out2 = generate_cpsat(gen_input)
    assert out1.roster_cells == out2.roster_cells


def test_cpsat_never_raises_infeasible_coverage_with_slack() -> None:
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

    start = date(2026, 12, 7)  # Mon
    end = date(2026, 12, 13)  # Sun (7 days)

    assignments = (Assignment(employee_id="emp-solo", brand_process_id="bp-solo"),)
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

    out = generate_cpsat(gen_input)
    # Status is optimal because slack accommodates the gap
    assert out.solver_status == SolverStatus.OPTIMAL
    # Exactly 1 day of shortfall due to mandatory weekly off (H2)
    assert out.slack_shortfall_total == 1

    # Independent validator catches the shortfall
    assert not out.validation_result.is_valid
    assert out.validation_result.blocking_count == 1
    conflict = out.validation_result.conflicts[0]
    assert conflict.code == ConflictCode.E001  # No coverage on weekly off day
    assert ConflictCode.E003.value in conflict.root_causes


def test_cpsat_respects_approved_leaves_and_fixed_cells() -> None:
    """Verify solver treats approved leaves as fixed non-working cells (H1, H4)."""
    bp = BrandProcess(
        id="bp-1",
        brand_id="b-1",
        brand_name="Brand A",
        process_id="p-1",
        process_name="CS",
        calendar_type=CalendarType.ALL_365,
        min_coverage_default=1,
    )
    e1 = Employee(id="emp-1", code="E1", full_name="Alice", pod_id="p1")
    e2 = Employee(id="emp-2", code="E2", full_name="Bob", pod_id="p1")

    start = date(2026, 12, 7)  # Mon
    end = date(2026, 12, 13)  # Sun

    leave_date = date(2026, 12, 9)  # Wed
    leaves = (
        EmployeeLeave(
            employee_id="emp-1",
            start_date=leave_date,
            end_date=leave_date,
            type=LeaveType.PLANNED,
        ),
    )

    assignments = (
        Assignment(employee_id="emp-1", brand_process_id="bp-1"),
        Assignment(employee_id="emp-2", brand_process_id="bp-1"),
    )

    demand = build_demand_matrix(brand_processes=[bp], start_date=start, end_date=end)
    supply = build_supply_matrix(
        employees=[e1, e2],
        start_date=start,
        end_date=end,
        leaves=leaves,
    )

    gen_input = GenerationInput(
        month_start=start,
        month_end=end,
        employees=(e1, e2),
        brand_processes=(bp,),
        assignments=assignments,
        coverage_rules=(),
        holidays=(),
        leaves=leaves,
        supply_matrix=tuple(supply),
        demand_matrix=tuple(demand),
        random_seed=42,
    )

    out = generate_cpsat(gen_input)
    assert out.solver_status == SolverStatus.OPTIMAL

    # Find emp-1 cell on leave_date
    e1_leave_cell = next(
        c for c in out.roster_cells if c.employee_id == "emp-1" and c.date == leave_date
    )
    assert e1_leave_cell.status == RosterStatus.LEAVE

    # Bob should be working to cover Alice on leave_date
    e2_cell = next(c for c in out.roster_cells if c.employee_id == "emp-2" and c.date == leave_date)
    assert e2_cell.status == RosterStatus.WORK


def test_cpsat_fixed_mandatory_weekly_off() -> None:
    """Verify FIXED_MANDATORY weekly off constraint (H5) is enforced."""
    bp = BrandProcess(
        id="bp-1",
        brand_id="b-1",
        brand_name="Brand A",
        process_id="p-1",
        process_name="CS",
        calendar_type=CalendarType.ALL_365,
        min_coverage_default=1,
    )
    e1 = Employee(
        id="emp-1",
        code="E1",
        full_name="Sunday Off",
        pod_id="p1",
        weekly_off_mode=WeeklyOffMode.FIXED_MANDATORY,
        fixed_weekly_off_weekdays=(6,),  # Mandatory Sunday off
    )
    e2 = Employee(id="emp-2", code="E2", full_name="Flexible", pod_id="p1")

    start = date(2026, 12, 7)  # Mon
    end = date(2026, 12, 13)  # Sun

    assignments = (
        Assignment(employee_id="emp-1", brand_process_id="bp-1"),
        Assignment(employee_id="emp-2", brand_process_id="bp-1"),
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

    out = generate_cpsat(gen_input)
    assert out.solver_status == SolverStatus.OPTIMAL

    sunday = date(2026, 12, 13)
    e1_sun_cell = next(c for c in out.roster_cells if c.employee_id == "emp-1" and c.date == sunday)
    assert e1_sun_cell.status == RosterStatus.WEEKLY_OFF
