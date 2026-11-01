"""Roster export service supporting CSV and XLSX formats across multiple views.

Conforms to API_DOCUMENTATION.md §4, TECH_STACK.md, and AGENTS.md rules:
- Format: CSV (stdlib csv) and XLSX (openpyxl)
- Views: grid (month), day, coverage (summary), conflicts
- Status codes: letter codes (W, WO, PH, HW, L, CO)
"""

from __future__ import annotations

import csv
import datetime as dt
import io
from typing import Any

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.models.roster import RosterEntryStatus
from app.schemas.roster import (
    RosterConflictRead,
    RosterCoverageCell,
    RosterDayViewResponse,
    RosterGridViewResponse,
)

# Standard letter codes matching AGENTS.md §5
STATUS_LETTER_CODES: dict[str, str] = {
    RosterEntryStatus.WORK.value: "W",
    RosterEntryStatus.WEEKLY_OFF.value: "WO",
    RosterEntryStatus.HOLIDAY_OFF.value: "PH",
    RosterEntryStatus.HOLIDAY_WORK.value: "HW",
    RosterEntryStatus.LEAVE.value: "L",
    RosterEntryStatus.COMP_OFF.value: "CO",
}

HEADER_FILL = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
HEADER_FONT = Font(bold=True, color="0F172A", size=10)
DATA_FONT = Font(size=10)
CENTER_ALIGN = Alignment(horizontal="center", vertical="center")
LEFT_ALIGN = Alignment(horizontal="left", vertical="center")


def _status_code(status: RosterEntryStatus | str | None) -> str:
    if not status:
        return ""
    val = status.value if hasattr(status, "value") else str(status)
    return STATUS_LETTER_CODES.get(val, val)


# -----------------------------------------------------------------------------
# 1. Monthly Grid View Export
# -----------------------------------------------------------------------------


def export_grid_csv(grid: RosterGridViewResponse) -> str:
    """Generate CSV string for monthly roster grid."""
    out = io.StringIO()
    writer = csv.writer(out)

    dates: list[dt.date] = []
    curr = grid.start_date
    while curr <= grid.end_date:
        dates.append(curr)
        curr += dt.timedelta(days=1)

    # Header
    header = ["Employee Code", "Employee Name", "Pod", "Primary Assignments"]
    header.extend(d.strftime("%Y-%m-%d (%a)") for d in dates)
    header.extend(
        [
            "Total Work (W)",
            "Weekly Off (WO)",
            "Holiday Work (HW)",
            "Holiday Off (PH)",
            "Leave (L)",
            "Comp Off (CO)",
        ]
    )
    writer.writerow(header)

    # Rows
    for row in grid.rows:
        w_cnt = wo_cnt = hw_cnt = ph_cnt = l_cnt = co_cnt = 0
        date_cols: list[str] = []
        for d in dates:
            cell = row.cells.get(d.isoformat())
            code = _status_code(cell.status) if cell else "WO"
            date_cols.append(code)
            if code == "W":
                w_cnt += 1
            elif code == "WO":
                wo_cnt += 1
            elif code == "HW":
                hw_cnt += 1
            elif code == "PH":
                ph_cnt += 1
            elif code == "L":
                l_cnt += 1
            elif code == "CO":
                co_cnt += 1

        writer.writerow(
            [
                row.employee_code,
                row.employee_name,
                row.pod_name or "",
                ", ".join(row.primary_assignments),
                *date_cols,
                w_cnt,
                wo_cnt,
                hw_cnt,
                ph_cnt,
                l_cnt,
                co_cnt,
            ]
        )

    return out.getvalue()


def export_grid_xlsx(grid: RosterGridViewResponse) -> bytes:
    """Generate styled XLSX bytes for monthly roster grid."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Monthly Roster"

    dates: list[dt.date] = []
    curr = grid.start_date
    while curr <= grid.end_date:
        dates.append(curr)
        curr += dt.timedelta(days=1)

    header = ["Employee Code", "Employee Name", "Pod", "Primary Assignments"]
    header.extend(d.strftime("%d %b (%a)") for d in dates)
    header.extend(["Work (W)", "Off (WO)", "HW", "PH", "Leave (L)", "Comp Off (CO)"])
    ws.append(header)

    for col_idx in range(1, len(header) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = CENTER_ALIGN if col_idx > 4 else LEFT_ALIGN

    for row_idx, row in enumerate(grid.rows, start=2):
        w_cnt = wo_cnt = hw_cnt = ph_cnt = l_cnt = co_cnt = 0
        date_cols: list[str] = []
        for d in dates:
            cell = row.cells.get(d.isoformat())
            code = _status_code(cell.status) if cell else "WO"
            date_cols.append(code)
            if code == "W":
                w_cnt += 1
            elif code == "WO":
                wo_cnt += 1
            elif code == "HW":
                hw_cnt += 1
            elif code == "PH":
                ph_cnt += 1
            elif code == "L":
                l_cnt += 1
            elif code == "CO":
                co_cnt += 1

        row_vals: list[Any] = [
            row.employee_code,
            row.employee_name,
            row.pod_name or "",
            ", ".join(row.primary_assignments),
            *date_cols,
            w_cnt,
            wo_cnt,
            hw_cnt,
            ph_cnt,
            l_cnt,
            co_cnt,
        ]
        ws.append(row_vals)

        for col_idx in range(1, len(row_vals) + 1):
            c = ws.cell(row=row_idx, column=col_idx)
            c.font = DATA_FONT
            if col_idx > 4:
                c.alignment = CENTER_ALIGN

    ws.freeze_panes = "E2"
    for col in ws.columns:
        max_len = max(len(str(c.value or "")) for c in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 7)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# -----------------------------------------------------------------------------
# 2. Single Day View Export
# -----------------------------------------------------------------------------


def export_day_csv(day: RosterDayViewResponse) -> str:
    """Generate CSV string for single-day operational staffing breakdown."""
    out = io.StringIO()
    writer = csv.writer(out)

    writer.writerow(
        [
            "Date",
            "Brand",
            "Process",
            "Calendar Operating",
            "Required Staff",
            "Actual Staff",
            "Shortfall",
            "Employee Code",
            "Employee Name",
            "Assignment Type",
            "Status",
            "Is Locked",
        ]
    )

    for grp in day.groups:
        brand_name = grp.brand_name
        proc_name = grp.process_name
        req = grp.required
        act = grp.actual
        shortfall = grp.shortfall
        is_op = "Yes" if grp.is_operating_day else "No"

        if grp.working_employees:
            for emp in grp.working_employees:
                writer.writerow(
                    [
                        day.date.isoformat(),
                        brand_name,
                        proc_name,
                        is_op,
                        req,
                        act,
                        shortfall,
                        emp.employee_code,
                        emp.employee_name,
                        emp.assignment_type or "",
                        _status_code(emp.status),
                        "Yes" if emp.is_locked else "No",
                    ]
                )
        else:
            writer.writerow(
                [
                    day.date.isoformat(),
                    brand_name,
                    proc_name,
                    is_op,
                    req,
                    act,
                    shortfall,
                    "",
                    "(No staff scheduled)",
                    "",
                    "",
                    "",
                ]
            )

    # Unassigned working employees
    for emp in day.unassigned_working_employees:
        writer.writerow(
            [
                day.date.isoformat(),
                "(Unassigned)",
                "(Unassigned)",
                "N/A",
                0,
                1,
                0,
                emp.employee_code,
                emp.employee_name,
                emp.assignment_type or "",
                _status_code(emp.status),
                "Yes" if emp.is_locked else "No",
            ]
        )

    return out.getvalue()


def export_day_xlsx(day: RosterDayViewResponse) -> bytes:
    """Generate XLSX bytes for single-day operational staffing breakdown."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Day {day.date.isoformat()}"

    headers = [
        "Date",
        "Brand",
        "Process",
        "Calendar Operating",
        "Required Staff",
        "Actual Staff",
        "Shortfall",
        "Employee Code",
        "Employee Name",
        "Assignment Type",
        "Status",
        "Is Locked",
    ]
    ws.append(headers)

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = CENTER_ALIGN if col_idx in (1, 4, 5, 6, 7, 11, 12) else LEFT_ALIGN

    row_cursor = 2
    for grp in day.groups:
        brand_name = grp.brand_name
        proc_name = grp.process_name
        req = grp.required
        act = grp.actual
        shortfall = grp.shortfall
        is_op = "Yes" if grp.is_operating_day else "No"

        if grp.working_employees:
            for emp in grp.working_employees:
                ws.append(
                    [
                        day.date.isoformat(),
                        brand_name,
                        proc_name,
                        is_op,
                        req,
                        act,
                        shortfall,
                        emp.employee_code,
                        emp.employee_name,
                        emp.assignment_type or "",
                        _status_code(emp.status),
                        "Yes" if emp.is_locked else "No",
                    ]
                )
                row_cursor += 1
        else:
            ws.append(
                [
                    day.date.isoformat(),
                    brand_name,
                    proc_name,
                    is_op,
                    req,
                    act,
                    shortfall,
                    "",
                    "(No staff scheduled)",
                    "",
                    "",
                    "",
                ]
            )
            row_cursor += 1

    for emp in day.unassigned_working_employees:
        ws.append(
            [
                day.date.isoformat(),
                "(Unassigned)",
                "(Unassigned)",
                "N/A",
                0,
                1,
                0,
                emp.employee_code,
                emp.employee_name,
                emp.assignment_type or "",
                _status_code(emp.status),
                "Yes" if emp.is_locked else "No",
            ]
        )
        row_cursor += 1

    ws.freeze_panes = "A2"
    for col in ws.columns:
        max_len = max(len(str(c.value or "")) for c in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 10)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

    ws.freeze_panes = "A2"
    for col in ws.columns:
        max_len = max(len(str(c.value or "")) for c in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 10)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# -----------------------------------------------------------------------------
# 3. Coverage Summary Export
# -----------------------------------------------------------------------------


def export_coverage_csv(cells: list[RosterCoverageCell]) -> str:
    """Generate CSV string for brand-process monthly coverage summary."""
    out = io.StringIO()
    writer = csv.writer(out)

    writer.writerow(
        [
            "Date",
            "Brand",
            "Process",
            "Required Headcount",
            "Actual Headcount",
            "Shortfall",
            "Coverage Status",
        ]
    )

    for cell in sorted(cells, key=lambda c: (c.date, c.brand_name or "", c.process_name or "")):
        status = "GAP" if cell.shortfall > 0 else "MET"
        writer.writerow(
            [
                cell.date.isoformat(),
                cell.brand_name or "",
                cell.process_name or "",
                cell.required,
                cell.actual,
                cell.shortfall,
                status,
            ]
        )

    return out.getvalue()


def export_coverage_xlsx(cells: list[RosterCoverageCell]) -> bytes:
    """Generate XLSX bytes for brand-process monthly coverage summary."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Coverage Summary"

    headers = [
        "Date",
        "Brand",
        "Process",
        "Required Headcount",
        "Actual Headcount",
        "Shortfall",
        "Coverage Status",
    ]
    ws.append(headers)

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = CENTER_ALIGN if col_idx in (1, 4, 5, 6, 7) else LEFT_ALIGN

    sorted_cells = sorted(cells, key=lambda c: (c.date, c.brand_name or "", c.process_name or ""))
    for cell in sorted_cells:
        status = "GAP" if cell.shortfall > 0 else "MET"
        ws.append(
            [
                cell.date.isoformat(),
                cell.brand_name or "",
                cell.process_name or "",
                cell.required,
                cell.actual,
                cell.shortfall,
                status,
            ]
        )

    ws.freeze_panes = "A2"
    for col in ws.columns:
        max_len = max(len(str(c.value or "")) for c in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# -----------------------------------------------------------------------------
# 4. Conflicts Report Export
# -----------------------------------------------------------------------------


def export_conflicts_csv(conflicts: list[RosterConflictRead]) -> str:
    """Generate CSV string for roster conflicts and notifications report."""
    out = io.StringIO()
    writer = csv.writer(out)

    writer.writerow(
        [
            "Code",
            "Severity",
            "Date From",
            "Date To",
            "Brand / Process ID",
            "Employee ID",
            "Root Causes",
            "Message",
            "Acknowledged",
            "Acknowledged Reason",
        ]
    )

    for c in sorted(
        conflicts, key=lambda x: (x.severity.value, x.code, x.date_from or dt.date.min)
    ):
        writer.writerow(
            [
                c.code,
                c.severity.value,
                c.date_from.isoformat() if c.date_from else "",
                c.date_to.isoformat() if c.date_to else "",
                str(c.brand_process_id) if c.brand_process_id else "",
                str(c.employee_id) if c.employee_id else "",
                ", ".join(c.root_causes),
                c.message,
                "Yes" if c.is_acknowledged else "No",
                c.acknowledged_reason or "",
            ]
        )

    return out.getvalue()


def export_conflicts_xlsx(conflicts: list[RosterConflictRead]) -> bytes:
    """Generate XLSX bytes for roster conflicts and notifications report."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Conflicts Report"

    headers = [
        "Code",
        "Severity",
        "Date From",
        "Date To",
        "Brand / Process ID",
        "Employee ID",
        "Root Causes",
        "Message",
        "Acknowledged",
        "Acknowledged Reason",
    ]
    ws.append(headers)

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = CENTER_ALIGN if col_idx in (1, 2, 3, 4, 9) else LEFT_ALIGN

    sorted_conflicts = sorted(
        conflicts, key=lambda x: (x.severity.value, x.code, x.date_from or dt.date.min)
    )
    for c in sorted_conflicts:
        ws.append(
            [
                c.code,
                c.severity.value,
                c.date_from.isoformat() if c.date_from else "",
                c.date_to.isoformat() if c.date_to else "",
                str(c.brand_process_id) if c.brand_process_id else "",
                str(c.employee_id) if c.employee_id else "",
                ", ".join(c.root_causes),
                c.message,
                "Yes" if c.is_acknowledged else "No",
                c.acknowledged_reason or "",
            ]
        )

    ws.freeze_panes = "A2"
    for col in ws.columns:
        max_len = max(len(str(c.value or "")) for c in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
