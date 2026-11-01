"""Unit tests for the pure-Python supply matrix builder."""

from datetime import date

import pytest

from app.scheduler.domain import (
    Assignment,
    BrandProcess,
    CalendarType,
    Employee,
    EmployeeLeave,
    Holiday,
    LeaveType,
    RosterCell,
    RosterStatus,
    SupplyAvailability,
)
from app.scheduler.supply import (
    build_supply_cell,
    build_supply_lookup,
    build_supply_matrix,
)


def test_supply_module_isolation() -> None:
    """Verify supply builder has no dependencies on fastapi, sqlalchemy, or app.db."""
    forbidden = ["fastapi", "sqlalchemy", "app.api", "app.db", "app.models"]
    import app.scheduler.supply

    for global_val in vars(app.scheduler.supply).values():
        val_mod = getattr(global_val, "__module__", "")
        for f in forbidden:
            assert not val_mod.startswith(f), f"Supply leaks forbidden dependency: {val_mod}"


def test_supply_default_available() -> None:
    """When no leave, holiday, or lock exists, employee is AVAILABLE."""
    emp = Employee(
        id="emp-1",
        code="EMP-001",
        full_name="Priya Sharma",
        pod_id="pod-a",
    )
    cell = build_supply_cell(employee=emp, target_date=date(2026, 12, 1))
    assert cell.availability == SupplyAvailability.AVAILABLE
    assert cell.is_locked is False
    assert cell.locked_status is None
    assert cell.reason == "Available for scheduling"


def test_supply_locked_cell_precedence() -> None:
    """Manager-locked cell takes precedence over everything else."""
    emp = Employee(
        id="emp-1",
        code="EMP-001",
        full_name="Priya Sharma",
        pod_id="pod-a",
    )
    target = date(2026, 12, 1)
    locked_cell = RosterCell(
        employee_id="emp-1",
        date=target,
        status=RosterStatus.WORK,
        is_locked=True,
        note="Manager manual assignment",
    )
    # Also define a leave on the same day to prove lock takes precedence
    leave = EmployeeLeave(
        employee_id="emp-1",
        start_date=target,
        end_date=target,
        type=LeaveType.SICK,
    )

    cell = build_supply_cell(
        employee=emp,
        target_date=target,
        leaves=(leave,),
        locked_cells=(locked_cell,),
    )
    assert cell.availability == SupplyAvailability.LOCKED
    assert cell.locked_status == RosterStatus.WORK
    assert cell.is_locked is True
    assert "Manager manual assignment" in cell.reason


def test_supply_leave_and_compoff() -> None:
    """Approved leaves and comp-offs set availability and locked status."""
    emp = Employee(
        id="emp-1",
        code="EMP-001",
        full_name="Priya Sharma",
        pod_id="pod-a",
    )

    # 1. Planned vacation leave
    leave_planned = EmployeeLeave(
        employee_id="emp-1",
        start_date=date(2026, 12, 10),
        end_date=date(2026, 12, 12),
        type=LeaveType.PLANNED,
        note="Family vacation",
    )
    cell_leave = build_supply_cell(
        employee=emp,
        target_date=date(2026, 12, 11),
        leaves=(leave_planned,),
    )
    assert cell_leave.availability == SupplyAvailability.LEAVE
    assert cell_leave.locked_status == RosterStatus.LEAVE
    assert cell_leave.is_locked is True
    assert cell_leave.reason == "Family vacation"

    # 2. Comp-off redemption
    compoff = EmployeeLeave(
        employee_id="emp-1",
        start_date=date(2026, 12, 15),
        end_date=date(2026, 12, 15),
        type=LeaveType.COMP_OFF,
        note="Earned holiday comp-off",
    )
    cell_compoff = build_supply_cell(
        employee=emp,
        target_date=date(2026, 12, 15),
        leaves=(compoff,),
    )
    assert cell_compoff.availability == SupplyAvailability.COMP_OFF
    assert cell_compoff.locked_status == RosterStatus.COMP_OFF
    assert cell_compoff.is_locked is True
    assert cell_compoff.reason == "Earned holiday comp-off"


def test_supply_personal_holiday() -> None:
    """Test personal holiday logic per SCHEDULING_ENGINE.md §4."""
    emp = Employee(
        id="emp-1",
        code="EMP-001",
        full_name="Rohan Verma",
        pod_id="pod-a",
    )
    bp_except_holidays = BrandProcess(
        id="bp-1",
        brand_id="b-1",
        brand_name="Brand A",
        process_id="p-1",
        process_name="CS",
        calendar_type=CalendarType.ALL_EXCEPT_HOLIDAYS,
    )
    bp_all_365 = BrandProcess(
        id="bp-2",
        brand_id="b-2",
        brand_name="Brand B",
        process_id="p-2",
        process_name="Live Voice",
        calendar_type=CalendarType.ALL_365,
    )
    holiday = Holiday(date=date(2026, 12, 25), name="Christmas", brand_id=None)

    # Case A: Rohan is ONLY assigned to bp_except_holidays.
    # On Christmas, bp_except_holidays does NOT operate -> Rohan gets personal HOLIDAY_OFF.
    assignments_a = (Assignment(employee_id="emp-1", brand_process_id="bp-1"),)
    cell_a = build_supply_cell(
        employee=emp,
        target_date=date(2026, 12, 25),
        assignments=assignments_a,
        brand_processes=(bp_except_holidays,),
        holidays=(holiday,),
    )
    assert cell_a.availability == SupplyAvailability.HOLIDAY_OFF
    assert cell_a.locked_status == RosterStatus.HOLIDAY_OFF
    assert cell_a.is_locked is True

    # Case B: Rohan is ALSO assigned to bp_all_365.
    # On Christmas, bp_all_365 DOES operate -> Rohan is AVAILABLE to work (and earn comp-off).
    assignments_b = (
        Assignment(employee_id="emp-1", brand_process_id="bp-1"),
        Assignment(employee_id="emp-1", brand_process_id="bp-2"),
    )
    cell_b = build_supply_cell(
        employee=emp,
        target_date=date(2026, 12, 25),
        assignments=assignments_b,
        brand_processes=(bp_except_holidays, bp_all_365),
        holidays=(holiday,),
    )
    assert cell_b.availability == SupplyAvailability.AVAILABLE
    assert cell_b.is_locked is False

    # Case C: Unassigned floater on global holiday -> HOLIDAY_OFF
    cell_c = build_supply_cell(
        employee=emp,
        target_date=date(2026, 12, 25),
        assignments=(),
        brand_processes=(),
        holidays=(holiday,),
    )
    assert cell_c.availability == SupplyAvailability.HOLIDAY_OFF
    assert cell_c.is_locked is True


def test_build_supply_matrix_and_lookup() -> None:
    """Test full matrix generation and fast lookup dict."""
    e1 = Employee(id="emp-1", code="E1", full_name="Alice", pod_id="p1")
    e2 = Employee(id="emp-2", code="E2", full_name="Bob", pod_id="p1")

    start = date(2026, 12, 1)
    end = date(2026, 12, 3)

    matrix = build_supply_matrix(
        employees=(e2, e1),  # Unsorted
        start_date=start,
        end_date=end,
    )

    # 3 days * 2 employees = 6 cells
    assert len(matrix) == 6

    # Verify deterministic sort order: date first, then employee.id
    assert matrix[0].date == start and matrix[0].employee_id == "emp-1"
    assert matrix[1].date == start and matrix[1].employee_id == "emp-2"
    assert matrix[2].date == date(2026, 12, 2) and matrix[2].employee_id == "emp-1"

    # Lookup test
    lookup = build_supply_lookup(matrix)
    assert len(lookup) == 6
    assert lookup[("emp-1", start)].availability == SupplyAvailability.AVAILABLE
    assert lookup[("emp-2", start)].employee_name == "Bob"

    # Inverted date range raises ValueError
    with pytest.raises(ValueError, match="cannot be after end_date"):
        build_supply_matrix(employees=(e1,), start_date=end, end_date=start)
