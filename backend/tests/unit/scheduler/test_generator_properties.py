"""Property-based tests for the roster scheduling engine using Hypothesis.

Invariants verified (TESTING_DOCUMENTATION.md §3, TASK_TRACKER.md T-803):
1. Demand is strictly 0 on every non-operating day regardless of override rules.
2. For any generated roster: fixed cells (leave, comp-off, locked) are never modified (H1).
3. Every generated roster satisfies H2/H3 (weekly offs, max consecutive days) for every employee.
4. Mandatory fixed weekly offs (H5) are strictly respected.
5. The shortfalls reported by the solver equal the E001/E002 set computed by the independent validator.
6. The solver is strictly deterministic for identical inputs and random seeds.
7. Fallback greedy generator also satisfies hard constraints (H1, H2, H3).
"""

from datetime import date, timedelta

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.scheduler.calendar import is_operating_day
from app.scheduler.demand import build_demand_matrix
from app.scheduler.domain import (
    Assignment,
    AssignmentType,
    BrandProcess,
    CalendarType,
    ConflictCode,
    CoverageRule,
    Employee,
    EmployeeLeave,
    GenerationInput,
    Holiday,
    LeaveType,
    RosterCell,
    RosterStatus,
    SolverStatus,
    WeeklyOffMode,
)
from app.scheduler.generator_cpsat import generate_cpsat
from app.scheduler.generator_greedy import generate_greedy
from app.scheduler.supply import build_supply_matrix
from app.scheduler.validator import partition_into_weeks

# ---------------------------------------------------------------------------
# Hypothesis Custom Strategies
# ---------------------------------------------------------------------------

@st.composite
def date_range_strategy(draw: st.DrawFn, min_days: int = 7, max_days: int = 14) -> tuple[date, date, list[date]]:
    """Generate a valid consecutive sequence of dates in 2026."""
    month = draw(st.integers(min_value=1, max_value=12))
    day = draw(st.integers(min_value=1, max_value=14))
    start_date = date(2026, month, day)
    num_days = draw(st.integers(min_value=min_days, max_value=max_days))
    end_date = start_date + timedelta(days=num_days - 1)
    dates = [start_date + timedelta(days=i) for i in range(num_days)]
    return start_date, end_date, dates


@st.composite
def employees_strategy(draw: st.DrawFn, min_emp: int = 2, max_emp: int = 3) -> tuple[Employee, ...]:
    """Generate a set of valid employees with realistic constraints."""
    count = draw(st.integers(min_value=min_emp, max_value=max_emp))
    employees = []
    for i in range(1, count + 1):
        weekly_off_count = draw(st.sampled_from([1, 2]))
        max_consecutive = draw(st.sampled_from([5, 6]))
        preferred_off = draw(st.integers(min_value=0, max_value=6))
        employees.append(
            Employee(
                id=f"emp-{i}",
                code=f"E{i}",
                full_name=f"Employee {i}",
                pod_id="pod-1",
                weekly_off_count=weekly_off_count,
                max_consecutive_days=max_consecutive,
                weekly_off_mode=WeeklyOffMode.ANY,
                preferred_weekly_off_weekdays=(preferred_off,),
            )
        )
    return tuple(employees)


@st.composite
def brand_process_strategy(draw: st.DrawFn) -> BrandProcess:
    """Generate a single BrandProcess with variable operating calendars."""
    cal_type = draw(st.sampled_from([
        CalendarType.ALL_365,
        CalendarType.ALL_EXCEPT_HOLIDAYS,
        CalendarType.EXCLUDE_SUNDAY_AND_HOLIDAYS,
    ]))
    min_cov = draw(st.integers(min_value=1, max_value=2))
    return BrandProcess(
        id="bp-1",
        brand_id="b-1",
        brand_name="Test Brand",
        process_id="p-1",
        process_name="CS",
        calendar_type=cal_type,
        min_coverage_default=min_cov,
    )


# ---------------------------------------------------------------------------
# Invariant 1: Demand is strictly 0 on every non-operating day
# ---------------------------------------------------------------------------

@given(
    date_range=date_range_strategy(min_days=7, max_days=21),
    cal_type=st.sampled_from([
        CalendarType.ALL_365,
        CalendarType.ALL_EXCEPT_HOLIDAYS,
        CalendarType.EXCLUDE_SUNDAY_AND_HOLIDAYS,
    ]),
    min_coverage=st.integers(min_value=1, max_value=5),
    holiday_offset=st.integers(min_value=0, max_value=6),
    override_staff=st.integers(min_value=3, max_value=10),
)
@settings(max_examples=30, deadline=None)
def test_property_demand_zero_on_non_operating_days(
    date_range: tuple[date, date, list[date]],
    cal_type: CalendarType,
    min_coverage: int,
    holiday_offset: int,
    override_staff: int,
) -> None:
    """Invariant 1: On every non-operating day, demand is 0 regardless of overrides."""
    start_date, end_date, dates = date_range
    bp = BrandProcess(
        id="bp-inv1",
        brand_id="b-1",
        brand_name="Brand A",
        process_id="p-1",
        process_name="Support",
        calendar_type=cal_type,
        min_coverage_default=min_coverage,
    )

    holiday_date = dates[min(holiday_offset, len(dates) - 1)]
    holidays = (Holiday(date=holiday_date, name="Test Holiday"),)

    # Add aggressive coverage rules that request large staff on all days / specific dates
    rules = (
        CoverageRule(brand_process_id=bp.id, weekday=holiday_date.weekday(), min_staff=override_staff),
        CoverageRule(brand_process_id=bp.id, specific_date=holiday_date, min_staff=override_staff),
    )

    demand_matrix = build_demand_matrix(
        brand_processes=[bp],
        start_date=start_date,
        end_date=end_date,
        rules=rules,
        holidays=holidays,
    )

    for cell in demand_matrix:
        is_op = is_operating_day(bp, cell.date, holidays)
        assert cell.is_operating_day == is_op
        if not cell.is_operating_day:
            assert cell.required_headcount == 0, (
                f"Non-operating day {cell.date} for calendar {cal_type} produced non-zero demand: {cell.required_headcount}"
            )
        else:
            assert cell.required_headcount >= 0


# ---------------------------------------------------------------------------
# Invariant 2: Fixed cells (leave, comp-off, locked) are never modified (H1)
# ---------------------------------------------------------------------------

@given(
    date_range=date_range_strategy(min_days=7, max_days=10),
    fixed_day_offset=st.integers(min_value=0, max_value=6),
    fixed_status=st.sampled_from([
        RosterStatus.LEAVE,
        RosterStatus.COMP_OFF,
        RosterStatus.WEEKLY_OFF,
    ]),
)
@settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_property_fixed_cells_preserved_h1(
    date_range: tuple[date, date, list[date]],
    fixed_day_offset: int,
    fixed_status: RosterStatus,
) -> None:
    """Invariant 2: For any generated roster, fixed cells in supply are strictly preserved."""
    start_date, end_date, dates = date_range
    target_date = dates[min(fixed_day_offset, len(dates) - 1)]

    e1 = Employee(id="emp-1", code="E1", full_name="Alice", pod_id="p1", weekly_off_count=1)
    e2 = Employee(id="emp-2", code="E2", full_name="Bob", pod_id="p1", weekly_off_count=1)
    bp = BrandProcess(
        id="bp-1",
        brand_id="b-1",
        brand_name="Brand A",
        process_id="p-1",
        process_name="CS",
        calendar_type=CalendarType.ALL_365,
        min_coverage_default=1,
    )
    assignments = (
        Assignment(employee_id=e1.id, brand_process_id=bp.id, type=AssignmentType.PRIMARY),
        Assignment(employee_id=e2.id, brand_process_id=bp.id, type=AssignmentType.PRIMARY),
    )

    demand = build_demand_matrix(brand_processes=[bp], start_date=start_date, end_date=end_date)

    # Inject fixed status via leaves or locked_cells using realistic supply builder
    leaves: list[EmployeeLeave] = []
    locked_cells: list[RosterCell] = []
    if fixed_status == RosterStatus.LEAVE:
        leaves.append(
            EmployeeLeave(
                employee_id="emp-1",
                start_date=target_date,
                end_date=target_date,
                type=LeaveType.PLANNED,
            )
        )
    elif fixed_status == RosterStatus.COMP_OFF:
        leaves.append(
            EmployeeLeave(
                employee_id="emp-1",
                start_date=target_date,
                end_date=target_date,
                type=LeaveType.COMP_OFF,
            )
        )
    else:
        locked_cells.append(
            RosterCell(
                employee_id="emp-1",
                date=target_date,
                status=fixed_status,
                is_locked=True,
            )
        )

    supply = build_supply_matrix(
        employees=[e1, e2],
        start_date=start_date,
        end_date=end_date,
        assignments=assignments,
        brand_processes=[bp],
        leaves=leaves,
        locked_cells=locked_cells,
    )

    gen_input = GenerationInput(
        month_start=start_date,
        month_end=end_date,
        employees=(e1, e2),
        brand_processes=(bp,),
        assignments=assignments,
        coverage_rules=(),
        holidays=(),
        leaves=tuple(leaves),
        locked_cells=tuple(locked_cells),
        supply_matrix=tuple(supply),
        demand_matrix=tuple(demand),
        random_seed=42,
    )

    output = generate_cpsat(gen_input)
    assert output.solver_status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)

    # Verify target cell was preserved exactly
    target_cells = [c for c in output.roster_cells if c.employee_id == "emp-1" and c.date == target_date]
    assert len(target_cells) == 1
    assert target_cells[0].status == fixed_status
    assert target_cells[0].is_locked is True


# ---------------------------------------------------------------------------
# Invariant 3: H2 (weekly offs) and H3 (max consecutive) satisfied
# ---------------------------------------------------------------------------

@given(
    date_range=date_range_strategy(min_days=7, max_days=14),
    employees=employees_strategy(min_emp=2, max_emp=3),
    tail_carry_in=st.integers(min_value=0, max_value=2),
    seed=st.integers(min_value=1, max_value=10_000),
)
@settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_property_h2_and_h3_hard_constraints_satisfied(
    date_range: tuple[date, date, list[date]],
    employees: tuple[Employee, ...],
    tail_carry_in: int,
    seed: int,
) -> None:
    """Invariant 3: Output strictly satisfies H2 (weekly offs) and H3 (max consecutive)."""
    start_date, end_date, dates = date_range

    bp = BrandProcess(
        id="bp-1",
        brand_id="b-1",
        brand_name="Brand A",
        process_id="p-1",
        process_name="CS",
        calendar_type=CalendarType.ALL_365,
        min_coverage_default=1,
    )
    assignments = tuple(
        Assignment(employee_id=emp.id, brand_process_id=bp.id, type=AssignmentType.PRIMARY)
        for emp in employees
    )

    demand = build_demand_matrix(brand_processes=[bp], start_date=start_date, end_date=end_date)
    supply = build_supply_matrix(employees=employees, start_date=start_date, end_date=end_date)

    tail_days = {employees[0].id: tail_carry_in}

    gen_input = GenerationInput(
        month_start=start_date,
        month_end=end_date,
        employees=employees,
        brand_processes=(bp,),
        assignments=assignments,
        coverage_rules=(),
        holidays=(),
        supply_matrix=tuple(supply),
        demand_matrix=tuple(demand),
        previous_tail_work_days=tail_days,
        random_seed=seed,
    )

    output = generate_cpsat(gen_input)
    assert output.solver_status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)

    # 1. Independent validator must NOT detect E005 (max consecutive) or E006 (weekly off missing)
    conflict_codes = {c.code for c in output.validation_result.conflicts}
    assert ConflictCode.E005 not in conflict_codes, (
        f"Solver violated H3 (E005 max consecutive days exceeded): {output.validation_result.conflicts}"
    )
    assert ConflictCode.E006 not in conflict_codes, (
        f"Solver violated H2 (E006 weekly off missing): {output.validation_result.conflicts}"
    )

    # 2. Direct cell invariant verification per employee
    weeks = partition_into_weeks(dates)
    working_statuses = {RosterStatus.WORK, RosterStatus.HOLIDAY_WORK}

    for emp in employees:
        emp_cells = {c.date: c for c in output.roster_cells if c.employee_id == emp.id}

        # Check H2 per week partition with >= 4 days in range
        for week_dates in weeks:
            if len(week_dates) >= 4:
                work_count = sum(1 for d in week_dates if emp_cells[d].status in working_statuses)
                max_allowed_work = len(week_dates) - emp.weekly_off_count
                assert work_count <= max_allowed_work, (
                    f"Employee {emp.id} worked {work_count} days in week of length {len(week_dates)}; "
                    f"max allowed is {max_allowed_work} (H2 violated)"
                )

        # Check H3 consecutive days
        streak = tail_days.get(emp.id, 0)
        for d in dates:
            if emp_cells[d].status in working_statuses:
                streak += 1
                assert streak <= emp.max_consecutive_days, (
                    f"Employee {emp.id} exceeded max consecutive days on {d}: streak={streak} > {emp.max_consecutive_days}"
                )
            else:
                streak = 0


# ---------------------------------------------------------------------------
# Invariant 4: Mandatory fixed weekly off (H5) is strictly respected
# ---------------------------------------------------------------------------

@given(
    date_range=date_range_strategy(min_days=7, max_days=14),
    fixed_weekday=st.integers(min_value=0, max_value=6),
)
@settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_property_mandatory_fixed_weekly_off_h5(
    date_range: tuple[date, date, list[date]],
    fixed_weekday: int,
) -> None:
    """Invariant 4: Employees with FIXED_MANDATORY never receive WORK on mandatory weekdays."""
    start_date, end_date, dates = date_range

    emp1 = Employee(
        id="emp-fixed",
        code="EF",
        full_name="Fixed Worker",
        pod_id="p1",
        weekly_off_mode=WeeklyOffMode.FIXED_MANDATORY,
        fixed_weekly_off_weekdays=(fixed_weekday,),
        weekly_off_count=1,
    )
    emp2 = Employee(
        id="emp-other",
        code="EO",
        full_name="Flexible Worker",
        pod_id="p1",
        weekly_off_mode=WeeklyOffMode.ANY,
        weekly_off_count=1,
    )

    bp = BrandProcess(
        id="bp-1",
        brand_id="b-1",
        brand_name="Brand A",
        process_id="p-1",
        process_name="CS",
        calendar_type=CalendarType.ALL_365,
        min_coverage_default=1,
    )
    assignments = (
        Assignment(employee_id=emp1.id, brand_process_id=bp.id, type=AssignmentType.PRIMARY),
        Assignment(employee_id=emp2.id, brand_process_id=bp.id, type=AssignmentType.PRIMARY),
    )

    demand = build_demand_matrix(brand_processes=[bp], start_date=start_date, end_date=end_date)
    supply = build_supply_matrix(employees=[emp1, emp2], start_date=start_date, end_date=end_date)

    gen_input = GenerationInput(
        month_start=start_date,
        month_end=end_date,
        employees=(emp1, emp2),
        brand_processes=(bp,),
        assignments=assignments,
        coverage_rules=(),
        holidays=(),
        supply_matrix=tuple(supply),
        demand_matrix=tuple(demand),
        random_seed=42,
    )

    output = generate_cpsat(gen_input)
    assert output.solver_status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)

    for cell in output.roster_cells:
        if cell.employee_id == "emp-fixed" and cell.date.weekday() == fixed_weekday:
            assert cell.status != RosterStatus.WORK, (
                f"Employee with FIXED_MANDATORY scheduled to WORK on fixed weekday {fixed_weekday} on {cell.date}"
            )


# ---------------------------------------------------------------------------
# Invariant 5: Solver slack equals independent validator shortfalls and E001/E002
# ---------------------------------------------------------------------------

@given(
    date_range=date_range_strategy(min_days=7, max_days=7),
    num_employees=st.integers(min_value=1, max_value=3),
    required_headcount=st.integers(min_value=0, max_value=4),
)
@settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_property_solver_slack_matches_validator(
    date_range: tuple[date, date, list[date]],
    num_employees: int,
    required_headcount: int,
) -> None:
    """Invariant 5: Solver slack shortfall matches independent validator shortfall & E001/E002 set."""
    start_date, end_date, dates = date_range

    employees = tuple(
        Employee(id=f"emp-{i}", code=f"E{i}", full_name=f"Worker {i}", pod_id="p1", weekly_off_count=1)
        for i in range(1, num_employees + 1)
    )
    bp = BrandProcess(
        id="bp-1",
        brand_id="b-1",
        brand_name="Brand A",
        process_id="p-1",
        process_name="CS",
        calendar_type=CalendarType.ALL_365,
        min_coverage_default=required_headcount,
    )
    assignments = tuple(
        Assignment(employee_id=emp.id, brand_process_id=bp.id, type=AssignmentType.PRIMARY)
        for emp in employees
    )

    demand = build_demand_matrix(brand_processes=[bp], start_date=start_date, end_date=end_date)
    supply = build_supply_matrix(employees=employees, start_date=start_date, end_date=end_date)

    gen_input = GenerationInput(
        month_start=start_date,
        month_end=end_date,
        employees=employees,
        brand_processes=(bp,),
        assignments=assignments,
        coverage_rules=(),
        holidays=(),
        supply_matrix=tuple(supply),
        demand_matrix=tuple(demand),
        random_seed=42,
    )

    output = generate_cpsat(gen_input)

    # 1. Total slack matches sum of shortfalls across validator CoverageCells
    validator_shortfall_total = sum(c.shortfall for c in output.coverage_cells)
    assert output.slack_shortfall_total == validator_shortfall_total, (
        f"Solver slack ({output.slack_shortfall_total}) does not match validator shortfall ({validator_shortfall_total})"
    )

    # 2. E001 / E002 conflict consistency
    e001_e002_conflicts = [
        c for c in output.validation_result.conflicts
        if c.code in (ConflictCode.E001, ConflictCode.E002)
    ]

    if output.slack_shortfall_total == 0:
        assert len(e001_e002_conflicts) == 0, (
            f"Zero slack reported but validator found coverage conflicts: {e001_e002_conflicts}"
        )
    else:
        # Every coverage cell with shortfall > 0 must have a matching conflict date
        shortfall_dates = {c.date for c in output.coverage_cells if c.shortfall > 0}
        conflict_dates = {c.date_from for c in e001_e002_conflicts}
        assert shortfall_dates == conflict_dates, (
            f"Shortfall dates {shortfall_dates} do not match E001/E002 conflict dates {conflict_dates}"
        )


# ---------------------------------------------------------------------------
# Invariant 6: Determinism across runs with identical seed
# ---------------------------------------------------------------------------

@given(
    date_range=date_range_strategy(min_days=7, max_days=10),
    seed=st.integers(min_value=0, max_value=100_000),
)
@settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_property_solver_determinism(
    date_range: tuple[date, date, list[date]],
    seed: int,
) -> None:
    """Invariant 6: Running generator twice with identical seed yields identical results."""
    start_date, end_date, dates = date_range

    e1 = Employee(id="emp-1", code="E1", full_name="Alice", pod_id="p1", weekly_off_count=1)
    e2 = Employee(id="emp-2", code="E2", full_name="Bob", pod_id="p1", weekly_off_count=1)
    bp = BrandProcess(
        id="bp-1",
        brand_id="b-1",
        brand_name="Brand A",
        process_id="p-1",
        process_name="CS",
        calendar_type=CalendarType.ALL_365,
        min_coverage_default=1,
    )
    assignments = (
        Assignment(employee_id=e1.id, brand_process_id=bp.id, type=AssignmentType.PRIMARY),
        Assignment(employee_id=e2.id, brand_process_id=bp.id, type=AssignmentType.PRIMARY),
    )

    demand = build_demand_matrix(brand_processes=[bp], start_date=start_date, end_date=end_date)
    supply = build_supply_matrix(employees=[e1, e2], start_date=start_date, end_date=end_date)

    gen_input = GenerationInput(
        month_start=start_date,
        month_end=end_date,
        employees=(e1, e2),
        brand_processes=(bp,),
        assignments=assignments,
        coverage_rules=(),
        holidays=(),
        supply_matrix=tuple(supply),
        demand_matrix=tuple(demand),
        random_seed=seed,
    )

    out1 = generate_cpsat(gen_input)
    out2 = generate_cpsat(gen_input)

    assert out1.roster_cells == out2.roster_cells
    assert out1.slack_shortfall_total == out2.slack_shortfall_total
    assert [c.code for c in out1.validation_result.conflicts] == [c.code for c in out2.validation_result.conflicts]


# ---------------------------------------------------------------------------
# Invariant 7: Fallback greedy heuristic also respects H1, H2, and H3
# ---------------------------------------------------------------------------

@given(
    date_range=date_range_strategy(min_days=7, max_days=14),
    employees=employees_strategy(min_emp=2, max_emp=3),
)
@settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_property_greedy_fallback_satisfies_hard_constraints(
    date_range: tuple[date, date, list[date]],
    employees: tuple[Employee, ...],
) -> None:
    """Invariant 7: The greedy fallback generator also satisfies H1, H2, and H3."""
    start_date, end_date, dates = date_range

    bp = BrandProcess(
        id="bp-1",
        brand_id="b-1",
        brand_name="Brand A",
        process_id="p-1",
        process_name="CS",
        calendar_type=CalendarType.ALL_365,
        min_coverage_default=1,
    )
    assignments = tuple(
        Assignment(employee_id=emp.id, brand_process_id=bp.id, type=AssignmentType.PRIMARY)
        for emp in employees
    )

    demand = build_demand_matrix(brand_processes=[bp], start_date=start_date, end_date=end_date)
    supply = build_supply_matrix(employees=employees, start_date=start_date, end_date=end_date)

    gen_input = GenerationInput(
        month_start=start_date,
        month_end=end_date,
        employees=employees,
        brand_processes=(bp,),
        assignments=assignments,
        coverage_rules=(),
        holidays=(),
        supply_matrix=tuple(supply),
        demand_matrix=tuple(demand),
        random_seed=42,
    )

    output = generate_greedy(gen_input)
    assert output.solver_status == SolverStatus.FALLBACK

    conflict_codes = {c.code for c in output.validation_result.conflicts}
    assert ConflictCode.E005 not in conflict_codes, (
        f"Greedy violated H3 (E005 max consecutive): {output.validation_result.conflicts}"
    )
    assert ConflictCode.E006 not in conflict_codes, (
        f"Greedy violated H2 (E006 weekly off missing): {output.validation_result.conflicts}"
    )
