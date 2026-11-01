"""Pure-Python supply availability matrix builder for the scheduling engine.

Evaluates per employee-date availability prior to solver optimization.
Classification rules per SCHEDULING_ENGINE.md Section 4:
1. LOCKED: Manager-locked cell overrides all other availability states.
2. LEAVE / COMP_OFF: Approved employee leave or comp-off redemption window.
3. HOLIDAY_OFF: Personal holiday (a holiday on which NONE of employee's assigned
   brand-processes operate). If any assigned brand-process operates, employee is AVAILABLE.
4. AVAILABLE: Employee is available to be rostered by the solver.

Non-negotiable architectural rule:
Zero external framework imports (FastAPI, SQLAlchemy, Pydantic, DB).
Operates exclusively on scheduler domain types and standard library.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta

from app.scheduler.calendar import has_applicable_holiday, is_operating_day
from app.scheduler.domain import (
    Assignment,
    BrandProcess,
    Employee,
    EmployeeLeave,
    Holiday,
    LeaveType,
    RosterCell,
    RosterStatus,
    SupplyAvailability,
    SupplyCell,
)


def build_supply_cell(
    employee: Employee,
    target_date: date,
    assignments: Sequence[Assignment] = (),
    brand_processes: Sequence[BrandProcess] = (),
    holidays: Sequence[Holiday] = (),
    leaves: Sequence[EmployeeLeave] = (),
    locked_cells: Sequence[RosterCell] = (),
) -> SupplyCell:
    """Build a SupplyCell for an employee on target_date following availability precedence."""
    # Precedence 1: Explicit manager locked cell
    for cell in locked_cells:
        if cell.employee_id == employee.id and cell.date == target_date and cell.is_locked:
            reason = cell.note if cell.note else f"Locked to {cell.status.value} by manager"
            return SupplyCell(
                employee_id=employee.id,
                employee_code=employee.code,
                employee_name=employee.full_name,
                date=target_date,
                availability=SupplyAvailability.LOCKED,
                locked_status=cell.status,
                is_locked=True,
                reason=reason,
            )

    # Precedence 2: Approved leave or comp-off redemption
    for leave in leaves:
        if leave.employee_id == employee.id and leave.covers(target_date):
            if leave.type == LeaveType.COMP_OFF:
                return SupplyCell(
                    employee_id=employee.id,
                    employee_code=employee.code,
                    employee_name=employee.full_name,
                    date=target_date,
                    availability=SupplyAvailability.COMP_OFF,
                    locked_status=RosterStatus.COMP_OFF,
                    is_locked=True,
                    reason=leave.note if leave.note else "Approved comp-off redemption",
                )
            return SupplyCell(
                employee_id=employee.id,
                employee_code=employee.code,
                employee_name=employee.full_name,
                date=target_date,
                availability=SupplyAvailability.LEAVE,
                locked_status=RosterStatus.LEAVE,
                is_locked=True,
                reason=leave.note if leave.note else f"Approved {leave.type.value} leave",
            )

    # Precedence 3: Personal holiday
    # Per SCHEDULING_ENGINE.md: personal holiday = a public holiday on which
    # NONE of their assigned brand-processes operate.
    assigned_bp_ids = {a.brand_process_id for a in assignments if a.employee_id == employee.id}
    assigned_bps = [bp for bp in brand_processes if bp.id in assigned_bp_ids]

    if not assigned_bps:
        # Floater or unassigned employee: check if global holiday falls on this date
        if has_applicable_holiday(holidays, brand_id="", target_date=target_date):
            return SupplyCell(
                employee_id=employee.id,
                employee_code=employee.code,
                employee_name=employee.full_name,
                date=target_date,
                availability=SupplyAvailability.HOLIDAY_OFF,
                locked_status=RosterStatus.HOLIDAY_OFF,
                is_locked=True,
                reason="Global holiday for unassigned staff",
            )
    else:
        # Check if an applicable holiday affects any assigned brand
        has_holiday = any(
            has_applicable_holiday(holidays, bp.brand_id, target_date) for bp in assigned_bps
        )
        if has_holiday:
            operating_bps = [
                bp for bp in assigned_bps if is_operating_day(bp, target_date, holidays)
            ]
            if not operating_bps:
                return SupplyCell(
                    employee_id=employee.id,
                    employee_code=employee.code,
                    employee_name=employee.full_name,
                    date=target_date,
                    availability=SupplyAvailability.HOLIDAY_OFF,
                    locked_status=RosterStatus.HOLIDAY_OFF,
                    is_locked=True,
                    reason="Personal holiday: none of assigned brand-processes operate",
                )

    # Precedence 4: Available for scheduling
    return SupplyCell(
        employee_id=employee.id,
        employee_code=employee.code,
        employee_name=employee.full_name,
        date=target_date,
        availability=SupplyAvailability.AVAILABLE,
        locked_status=None,
        is_locked=False,
        reason="Available for scheduling",
    )


def build_supply_matrix(
    employees: Sequence[Employee],
    start_date: date,
    end_date: date,
    assignments: Sequence[Assignment] = (),
    brand_processes: Sequence[BrandProcess] = (),
    holidays: Sequence[Holiday] = (),
    leaves: Sequence[EmployeeLeave] = (),
    locked_cells: Sequence[RosterCell] = (),
) -> list[SupplyCell]:
    """Generate the complete supply matrix for all employees across the date range.

    Deterministically sorted by date, then employee id.
    """
    if start_date > end_date:
        raise ValueError(f"start_date ({start_date}) cannot be after end_date ({end_date})")

    sorted_employees = sorted(employees, key=lambda e: e.id)
    matrix: list[SupplyCell] = []
    current = start_date
    one_day = timedelta(days=1)

    while current <= end_date:
        for emp in sorted_employees:
            cell = build_supply_cell(
                employee=emp,
                target_date=current,
                assignments=assignments,
                brand_processes=brand_processes,
                holidays=holidays,
                leaves=leaves,
                locked_cells=locked_cells,
            )
            matrix.append(cell)
        current += one_day

    return matrix


def build_supply_lookup(
    supply_cells: Sequence[SupplyCell],
) -> dict[tuple[str, date], SupplyCell]:
    """Index a list of SupplyCells by (employee_id, date) for constant-time lookup."""
    return {(cell.employee_id, cell.date): cell for cell in supply_cells}
