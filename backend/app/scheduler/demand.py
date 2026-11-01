"""Pure-Python demand matrix builder for the scheduling engine.

Evaluates required staffing headcount for each brand-process across a date range.
Precedence per SCHEDULING_ENGINE.md Section 3:
1. Non-operating days (per calendar resolver) -> demand is 0.
2. Specific date override (CoverageRule with specific_date) -> highest precedence.
3. Weekday override (CoverageRule with weekday) -> next precedence.
4. Default minimum (BrandProcess.min_coverage_default) -> fallback.

Non-negotiable architectural rule:
Zero external framework imports (FastAPI, SQLAlchemy, Pydantic, DB).
Operates exclusively on scheduler domain types and standard library.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta

from app.scheduler.calendar import is_operating_day
from app.scheduler.domain import BrandProcess, CoverageRule, DemandCell, Holiday


def build_demand_cell(
    brand_process: BrandProcess,
    target_date: date,
    holidays: Sequence[Holiday] = (),
    rules: Sequence[CoverageRule] = (),
) -> DemandCell:
    """Build a single DemandCell for a brand-process on target_date following precedence rules."""
    operating = is_operating_day(brand_process, target_date, holidays)

    if not operating:
        return DemandCell(
            brand_process_id=brand_process.id,
            brand_id=brand_process.brand_id,
            brand_name=brand_process.brand_name,
            process_id=brand_process.process_id,
            process_name=brand_process.process_name,
            date=target_date,
            is_operating_day=False,
            required_headcount=0,
            reason="non-operating day",
        )

    # Filter rules for this brand-process
    bp_rules = [r for r in rules if r.brand_process_id == brand_process.id]

    # Precedence 1: Specific date override
    date_overrides = [r for r in bp_rules if r.specific_date == target_date]
    if date_overrides:
        # If multiple, deterministic sort by min_staff descending
        chosen = max(date_overrides, key=lambda r: r.min_staff)
        reason = chosen.reason if chosen.reason else "date override"
        return DemandCell(
            brand_process_id=brand_process.id,
            brand_id=brand_process.brand_id,
            brand_name=brand_process.brand_name,
            process_id=brand_process.process_id,
            process_name=brand_process.process_name,
            date=target_date,
            is_operating_day=True,
            required_headcount=max(0, chosen.min_staff),
            reason=reason,
        )

    # Precedence 2: Weekday override
    target_weekday = target_date.weekday()
    weekday_overrides = [r for r in bp_rules if r.weekday == target_weekday]
    if weekday_overrides:
        chosen = max(weekday_overrides, key=lambda r: r.min_staff)
        reason = chosen.reason if chosen.reason else "weekday override"
        return DemandCell(
            brand_process_id=brand_process.id,
            brand_id=brand_process.brand_id,
            brand_name=brand_process.brand_name,
            process_id=brand_process.process_id,
            process_name=brand_process.process_name,
            date=target_date,
            is_operating_day=True,
            required_headcount=max(0, chosen.min_staff),
            reason=reason,
        )

    # Precedence 3: Default minimum
    return DemandCell(
        brand_process_id=brand_process.id,
        brand_id=brand_process.brand_id,
        brand_name=brand_process.brand_name,
        process_id=brand_process.process_id,
        process_name=brand_process.process_name,
        date=target_date,
        is_operating_day=True,
        required_headcount=max(0, brand_process.min_coverage_default),
        reason="default minimum",
    )


def build_demand_matrix(
    brand_processes: Sequence[BrandProcess],
    start_date: date,
    end_date: date,
    holidays: Sequence[Holiday] = (),
    rules: Sequence[CoverageRule] = (),
) -> list[DemandCell]:
    """Generate the complete demand matrix across all brand-processes and dates.

    Output is deterministically sorted by date, then brand_process_id.
    """
    if start_date > end_date:
        raise ValueError(f"start_date ({start_date}) cannot be after end_date ({end_date})")

    # Stable ordering of brand processes by id
    sorted_bps = sorted(brand_processes, key=lambda bp: bp.id)

    matrix: list[DemandCell] = []
    current = start_date
    one_day = timedelta(days=1)

    while current <= end_date:
        for bp in sorted_bps:
            cell = build_demand_cell(bp, current, holidays, rules)
            matrix.append(cell)
        current += one_day

    return matrix


def build_demand_lookup(
    demand_cells: Sequence[DemandCell],
) -> dict[tuple[str, date], DemandCell]:
    """Index a list of DemandCells by (brand_process_id, date) for constant-time lookup."""
    return {(cell.brand_process_id, cell.date): cell for cell in demand_cells}

