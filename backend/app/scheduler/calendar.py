"""Pure-Python operating calendar resolver.

Resolves active operating days for each brand-process based on:
1. CalendarType (ALL_365, ALL_EXCEPT_HOLIDAYS, EXCLUDE_SUNDAY_AND_HOLIDAYS)
2. Holiday applicability (global holidays vs brand-scoped holidays)
3. Date range iteration

Non-negotiable architectural rule:
Zero external framework imports (FastAPI, SQLAlchemy, Pydantic, DB).
Operates exclusively on scheduler domain types and Python standard library.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta

from app.scheduler.domain import BrandProcess, CalendarType, Holiday


def is_holiday_applicable(holiday: Holiday, brand_id: str) -> bool:
    """Check if a holiday applies to a specific brand.

    A holiday applies if it is global (brand_id is None) or matches the brand.
    """
    return holiday.brand_id is None or holiday.brand_id == brand_id


def get_applicable_holidays(
    holidays: Sequence[Holiday],
    brand_id: str,
    target_date: date | None = None,
) -> list[Holiday]:
    """Retrieve all holidays applicable to a brand, optionally filtered by date."""
    applicable: list[Holiday] = []
    for h in holidays:
        if is_holiday_applicable(h, brand_id) and (target_date is None or h.date == target_date):
            applicable.append(h)
    return applicable


def has_applicable_holiday(
    holidays: Sequence[Holiday],
    brand_id: str,
    target_date: date,
) -> bool:
    """Fast check whether any holiday applies to the brand on the target date."""
    return any(h.date == target_date and is_holiday_applicable(h, brand_id) for h in holidays)


def is_operating_day(
    brand_process: BrandProcess,
    target_date: date,
    holidays: Sequence[Holiday] = (),
) -> bool:
    """Determine whether a brand-process operates on a specific date.

    Rules per SCHEDULING_ENGINE.md Section 2:
    - ALL_365: Operates every day of the year (holidays included).
    - ALL_EXCEPT_HOLIDAYS: Operates every day except applicable public holidays.
    - EXCLUDE_SUNDAY_AND_HOLIDAYS: Operates every day except Sundays and applicable public holidays.
    """
    cal_type = brand_process.calendar_type

    if cal_type == CalendarType.ALL_365:
        return True

    is_holiday = has_applicable_holiday(holidays, brand_process.brand_id, target_date)

    if cal_type == CalendarType.ALL_EXCEPT_HOLIDAYS:
        return not is_holiday

    if cal_type == CalendarType.EXCLUDE_SUNDAY_AND_HOLIDAYS:
        is_sunday = target_date.weekday() == 6  # 6 = Sunday in Python datetime
        return not is_sunday and not is_holiday

    # Fallback default: non-operating if unrecognized
    return False


def resolve_operating_days(
    brand_process: BrandProcess,
    start_date: date,
    end_date: date,
    holidays: Sequence[Holiday] = (),
) -> dict[date, bool]:
    """Resolve operating status for each date in [start_date, end_date] for one brand-process."""
    if start_date > end_date:
        raise ValueError(f"start_date ({start_date}) cannot be after end_date ({end_date})")

    result: dict[date, bool] = {}
    current = start_date
    one_day = timedelta(days=1)

    while current <= end_date:
        result[current] = is_operating_day(brand_process, current, holidays)
        current += one_day

    return result


def get_operating_dates(
    brand_process: BrandProcess,
    start_date: date,
    end_date: date,
    holidays: Sequence[Holiday] = (),
) -> list[date]:
    """Return a list of all active operating dates for a brand-process in the given range."""
    days_map = resolve_operating_days(brand_process, start_date, end_date, holidays)
    return [d for d, operating in days_map.items() if operating]


def resolve_calendar_matrix(
    brand_processes: Sequence[BrandProcess],
    start_date: date,
    end_date: date,
    holidays: Sequence[Holiday] = (),
) -> dict[tuple[str, date], bool]:
    """Resolve operating status for all brand-processes across the entire date range.

    Returns a dict with key (brand_process_id, date) -> is_operating.
    """
    matrix: dict[tuple[str, date], bool] = {}
    for bp in brand_processes:
        bp_days = resolve_operating_days(bp, start_date, end_date, holidays)
        for d, operating in bp_days.items():
            matrix[(bp.id, d)] = operating
    return matrix
