"""Unit tests for the pure-Python independent roster validator (E001–E009, W001, W003)."""

from datetime import date

from app.scheduler.domain import (
    Assignment,
    AssignmentType,
    BrandProcess,
    CalendarType,
    ConflictCode,
    ConflictSeverity,
    DemandCell,
    Employee,
    EmployeeLeave,
    Holiday,
    LeaveType,
    RosterCell,
    RosterStatus,
    WeeklyOffMode,
)
from app.scheduler.validator import (
    partition_into_weeks,
    validate,
    validate_roster,
)


def test_validator_module_isolation() -> None:
    """Verify validator has no dependencies on fastapi, sqlalchemy, or app.db."""
    forbidden = ["fastapi", "sqlalchemy", "app.api", "app.db", "app.models"]
    import app.scheduler.validator

    for global_val in vars(app.scheduler.validator).values():
        val_mod = getattr(global_val, "__module__", "")
        for f in forbidden:
            assert not val_mod.startswith(f), f"Validator leaks forbidden dependency: {val_mod}"


def test_partition_into_weeks_pro_rating() -> None:
    """Test calendar week partitioning and pro-rating logic at month boundaries."""
    # December 2026: Tue Dec 1 to Thu Dec 31
    dec_dates = [date(2026, 12, d) for d in range(1, 32)]
    weeks = partition_into_weeks(dec_dates)

    # 5 weeks in Dec 2026:
    # W1: Dec 1-6 (6 days) >= 4 -> 1 off required
    # W2: Dec 7-13 (7 days) >= 4 -> 1 off required
    # W3: Dec 14-20 (7 days) >= 4 -> 1 off required
    # W4: Dec 21-27 (7 days) >= 4 -> 1 off required
    # W5: Dec 28-31 (4 days) >= 4 -> 1 off required
    assert len(weeks) == 5
    assert len(weeks[0]) == 6
    assert len(weeks[-1]) == 4

    # Short edge week: Nov 28 to Nov 30 (Sat, Sun, Mon - 3 days)
    short_edge = [date(2026, 11, 28), date(2026, 11, 29), date(2026, 11, 30)]
    short_weeks = partition_into_weeks(short_edge)
    assert len(short_weeks) == 2
    # Nov 28-29 (Sat-Sun: 2 days < 4 -> 0 required)
    assert len(short_weeks[0]) == 2
    # Nov 30 (Mon: 1 day < 4 -> 0 required)
    assert len(short_weeks[1]) == 1


def test_e001_and_e002_coverage_conflicts_and_root_causes() -> None:
    """Test E001 (NO_COVERAGE), E002 (UNDER_STAFFED), and root-cause tags E003/E004."""
    bp = BrandProcess(
        id="bp-1",
        brand_id="b-1",
        brand_name="Aurora",
        process_id="p-1",
        process_name="CS",
        calendar_type=CalendarType.ALL_365,
    )
    e1 = Employee(id="emp-1", code="E1", full_name="Riya Shah", pod_id="p1")
    e2 = Employee(id="emp-2", code="E2", full_name="Aarav Sen", pod_id="p1")

    assignments = (
        Assignment(employee_id="emp-1", brand_process_id="bp-1"),
        Assignment(employee_id="emp-2", brand_process_id="bp-1"),
    )

    d1 = date(2026, 12, 1)  # Day 1: Under-staffed (E002), caused by weekly off (E003)
    d2 = date(2026, 12, 2)  # Day 2: No coverage (E001), caused by leave (E004)

    demand_cells = (
        DemandCell(
            brand_process_id="bp-1",
            brand_id="b-1",
            brand_name="Aurora",
            process_id="p-1",
            process_name="CS",
            date=d1,
            is_operating_day=True,
            required_headcount=2,
        ),
        DemandCell(
            brand_process_id="bp-1",
            brand_id="b-1",
            brand_name="Aurora",
            process_id="p-1",
            process_name="CS",
            date=d2,
            is_operating_day=True,
            required_headcount=2,
        ),
    )

    # Day 1: emp-1 works, emp-2 on WEEKLY_OFF -> covered 1/2 (E002, root-cause E003)
    # Day 2: emp-1 on LEAVE, emp-2 on LEAVE -> covered 0/2 (E001, root-cause E004)
    roster_cells = (
        RosterCell(employee_id="emp-1", date=d1, status=RosterStatus.WORK),
        RosterCell(employee_id="emp-2", date=d1, status=RosterStatus.WEEKLY_OFF),
        RosterCell(employee_id="emp-1", date=d2, status=RosterStatus.LEAVE),
        RosterCell(employee_id="emp-2", date=d2, status=RosterStatus.LEAVE),
    )

    result = validate(
        roster_cells=roster_cells,
        demand_cells=demand_cells,
        supply_cells=(),
        employees=(e1, e2),
        brand_processes=(bp,),
        assignments=assignments,
    )

    assert not result.is_valid
    codes = [c.code for c in result.conflicts]
    assert ConflictCode.E002 in codes  # Under-staffed
    assert ConflictCode.E001 in codes  # No coverage

    # Verify root cause tags
    e002_conflict = next(c for c in result.conflicts if c.code == ConflictCode.E002)
    assert ConflictCode.E003.value in e002_conflict.root_causes
    assert "WEEKLY_OFF" in e002_conflict.root_causes

    e001_conflict = next(c for c in result.conflicts if c.code == ConflictCode.E001)
    assert ConflictCode.E004.value in e001_conflict.root_causes
    assert "LEAVE" in e001_conflict.root_causes


def test_e005_max_consecutive_days() -> None:
    """Test E005 when an employee works more than max_consecutive_days."""
    emp = Employee(id="emp-1", code="E1", full_name="Kabir", pod_id="p1", max_consecutive_days=6)
    # 7 consecutive days of WORK
    dates = [date(2026, 12, d) for d in range(1, 8)]
    roster_cells = [
        RosterCell(employee_id="emp-1", date=d, status=RosterStatus.WORK) for d in dates
    ]

    result = validate(
        roster_cells=roster_cells,
        demand_cells=(),
        supply_cells=(),
        employees=(emp,),
        brand_processes=(),
        assignments=(),
    )

    assert any(c.code == ConflictCode.E005 for c in result.conflicts)


def test_e006_weekly_off_missing() -> None:
    """Test E006 when employee does not receive required weekly offs in a week."""
    emp = Employee(id="emp-1", code="E1", full_name="Kabir", pod_id="p1", weekly_off_count=1)
    # 7 days with zero WEEKLY_OFF (all WORK)
    dates = [date(2026, 12, d) for d in range(7, 14)]  # Mon Dec 7 to Sun Dec 13
    roster_cells = [
        RosterCell(employee_id="emp-1", date=d, status=RosterStatus.WORK) for d in dates
    ]

    result = validate(
        roster_cells=roster_cells,
        demand_cells=(),
        supply_cells=(),
        employees=(emp,),
        brand_processes=(),
        assignments=(),
    )

    assert any(c.code == ConflictCode.E006 for c in result.conflicts)


def test_e007_invalid_cell_leave_conflict_and_fake_holiday() -> None:
    """Test E007 for WORK on approved leave day and HOLIDAY_WORK on non-holiday."""
    emp = Employee(id="emp-1", code="E1", full_name="Ananya", pod_id="p1")
    d1 = date(2026, 12, 1)
    d2 = date(2026, 12, 2)

    leaves = (
        EmployeeLeave(
            employee_id="emp-1",
            start_date=d1,
            end_date=d1,
            type=LeaveType.PLANNED,
        ),
    )

    # d1: scheduled to WORK while on leave -> invalid
    # d2: scheduled to HOLIDAY_WORK while d2 is not a holiday -> invalid
    roster_cells = (
        RosterCell(employee_id="emp-1", date=d1, status=RosterStatus.WORK),
        RosterCell(employee_id="emp-1", date=d2, status=RosterStatus.HOLIDAY_WORK),
    )

    result = validate(
        roster_cells=roster_cells,
        demand_cells=(),
        supply_cells=(),
        employees=(emp,),
        brand_processes=(),
        assignments=(),
        holidays=(),  # No holidays
        leaves=leaves,
    )

    e007_conflicts = [c for c in result.conflicts if c.code == ConflictCode.E007]
    assert len(e007_conflicts) == 2


def test_e008_concurrent_process_overload() -> None:
    """Test E008 WARNING when working employee exceeds max_concurrent_processes."""
    emp = Employee(
        id="emp-1",
        code="E1",
        full_name="Vikram",
        pod_id="p1",
        max_concurrent_processes=2,
    )
    bps = [
        BrandProcess(
            id=f"bp-{i}",
            brand_id=f"b-{i}",
            brand_name=f"Brand {i}",
            process_id="p-1",
            process_name="CS",
            calendar_type=CalendarType.ALL_365,
        )
        for i in range(1, 4)
    ]
    assignments = [Assignment(employee_id="emp-1", brand_process_id=f"bp-{i}") for i in range(1, 4)]

    target = date(2026, 12, 1)
    roster_cells = (RosterCell(employee_id="emp-1", date=target, status=RosterStatus.WORK),)

    result = validate(
        roster_cells=roster_cells,
        demand_cells=(),
        supply_cells=(),
        employees=(emp,),
        brand_processes=bps,
        assignments=assignments,
    )

    e008_conflicts = [c for c in result.conflicts if c.code == ConflictCode.E008]
    assert len(e008_conflicts) == 1
    assert e008_conflicts[0].severity == ConflictSeverity.WARNING


def test_e009_compoff_balance() -> None:
    """Test E009 when redeemed comp-offs exceed earned credits."""
    emp = Employee(id="emp-1", code="E1", full_name="Sneha", pod_id="p1")
    target = date(2026, 12, 1)

    # Redeemed COMP_OFF with initial balance of 0 and no earned credits
    roster_cells = (RosterCell(employee_id="emp-1", date=target, status=RosterStatus.COMP_OFF),)

    result = validate(
        roster_cells=roster_cells,
        demand_cells=(),
        supply_cells=(),
        employees=(emp,),
        brand_processes=(),
        assignments=(),
        initial_compoff_balances={"emp-1": 0},
    )

    e009_conflicts = [c for c in result.conflicts if c.code == ConflictCode.E009]
    assert len(e009_conflicts) == 1


def test_w001_and_w003() -> None:
    """Test W001 (preference violated) and W003 (single point of failure)."""
    emp = Employee(
        id="emp-1",
        code="E1",
        full_name="Meera",
        pod_id="p1",
        preferred_weekly_off_weekdays=(1,),  # Preferred Tuesday off
    )
    bp = BrandProcess(
        id="bp-1",
        brand_id="b-1",
        brand_name="Niche Brand",
        process_id="p-1",
        process_name="CS",
        calendar_type=CalendarType.ALL_365,
    )
    assignment = Assignment(
        employee_id="emp-1",
        brand_process_id="bp-1",
        type=AssignmentType.PRIMARY,
    )

    tuesday = date(2026, 12, 1)  # Tuesday
    demand_cell = DemandCell(
        brand_process_id="bp-1",
        brand_id="b-1",
        brand_name="Niche Brand",
        process_id="p-1",
        process_name="CS",
        date=tuesday,
        is_operating_day=True,
        required_headcount=1,
    )
    roster_cell = RosterCell(employee_id="emp-1", date=tuesday, status=RosterStatus.WORK)

    result = validate(
        roster_cells=(roster_cell,),
        demand_cells=(demand_cell,),
        supply_cells=(),
        employees=(emp,),
        brand_processes=(bp,),
        assignments=(assignment,),
    )

    codes = [c.code for c in result.conflicts]
    assert ConflictCode.W001 in codes  # Preference violated (worked on preferred Tue off)
    assert ConflictCode.W003 in codes  # Single point of failure (1 primary, 0 backups)


def test_fixed_mandatory_weekly_off_and_holiday_work() -> None:
    """Test fixed mandatory weekly off violation and valid holiday work with comp-off earning."""
    emp = Employee(
        id="emp-1",
        code="E1",
        full_name="Arjun",
        pod_id="p1",
        weekly_off_mode=WeeklyOffMode.FIXED_MANDATORY,
        fixed_weekly_off_weekdays=(6,),  # Mandatory Sunday off
    )
    holiday = Holiday(date=date(2026, 12, 25), name="Christmas", brand_id=None)

    # Sunday Dec 6: scheduled to WORK when Sunday is mandatory off -> E006 BLOCKING
    sun_cell = RosterCell(employee_id="emp-1", date=date(2026, 12, 6), status=RosterStatus.WORK)
    # Christmas Dec 25 (holiday): scheduled to HOLIDAY_WORK -> Valid
    xmas_cell = RosterCell(
        employee_id="emp-1", date=date(2026, 12, 25), status=RosterStatus.HOLIDAY_WORK
    )

    result = validate(
        roster_cells=(sun_cell, xmas_cell),
        demand_cells=(),
        supply_cells=(),
        employees=(emp,),
        brand_processes=(),
        assignments=(),
        holidays=(holiday,),
    )

    # Sunday violation flagged
    e006_conflicts = [
        c
        for c in result.conflicts
        if c.code == ConflictCode.E006 and "MANDATORY_FIXED_OFF_VIOLATED" in c.root_causes
    ]
    assert len(e006_conflicts) == 1
    # Christmas is a valid holiday, so no E007 for holiday status
    e007_holiday_conflicts = [
        c
        for c in result.conflicts
        if c.code == ConflictCode.E007 and "INVALID_HOLIDAY_STATUS" in c.root_causes
    ]
    assert len(e007_holiday_conflicts) == 0
    """Test a fully valid schedule produces is_valid = True and zero blocking conflicts."""
    emp = Employee(id="emp-1", code="E1", full_name="Rahul", pod_id="p1", weekly_off_count=1)
    bp = BrandProcess(
        id="bp-1",
        brand_id="b-1",
        brand_name="Main Brand",
        process_id="p-1",
        process_name="CS",
        calendar_type=CalendarType.ALL_365,
    )
    assignments = (
        Assignment(employee_id="emp-1", brand_process_id="bp-1", type=AssignmentType.PRIMARY),
        Assignment(employee_id="emp-backup", brand_process_id="bp-1", type=AssignmentType.BACKUP),
    )

    # 1 full week (Mon Dec 7 to Sun Dec 13): 6 WORK, 1 WEEKLY_OFF
    dates = [date(2026, 12, d) for d in range(7, 14)]
    roster_cells = [
        RosterCell(
            employee_id="emp-1",
            date=d,
            status=RosterStatus.WEEKLY_OFF if d.weekday() == 6 else RosterStatus.WORK,
        )
        for d in dates
    ]
    demand_cells = [
        DemandCell(
            brand_process_id="bp-1",
            brand_id="b-1",
            brand_name="Main Brand",
            process_id="p-1",
            process_name="CS",
            date=d,
            is_operating_day=True,
            required_headcount=0 if d.weekday() == 6 else 1,
        )
        for d in dates
    ]

    res, cov_cells = validate_roster(
        roster_cells=roster_cells,
        demand_cells=demand_cells,
        supply_cells=(),
        employees=(emp,),
        brand_processes=(bp,),
        assignments=assignments,
    )

    assert res.is_valid is True
    assert res.blocking_count == 0
    assert len(cov_cells) == 7
