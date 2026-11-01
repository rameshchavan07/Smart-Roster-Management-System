"""Unit tests for the pure-Python demand builder."""

from datetime import date

import pytest

from app.scheduler.demand import (
    build_demand_cell,
    build_demand_lookup,
    build_demand_matrix,
)
from app.scheduler.domain import BrandProcess, CalendarType, CoverageRule, Holiday


def test_demand_module_isolation() -> None:
    """Verify demand builder has no dependencies on fastapi, sqlalchemy, or app.db."""
    forbidden = ["fastapi", "sqlalchemy", "app.api", "app.db", "app.models"]
    import app.scheduler.demand

    for global_val in vars(app.scheduler.demand).values():
        val_mod = getattr(global_val, "__module__", "")
        for f in forbidden:
            assert not val_mod.startswith(f), f"Demand leaks forbidden dependency: {val_mod}"


def test_demand_precedence_default_minimum() -> None:
    """When no overrides exist, demand defaults to BrandProcess.min_coverage_default."""
    bp = BrandProcess(
        id="bp-1",
        brand_id="b-1",
        brand_name="Brand A",
        process_id="p-1",
        process_name="CS",
        calendar_type=CalendarType.ALL_365,
        min_coverage_default=2,
    )
    cell = build_demand_cell(bp, date(2026, 12, 1))
    assert cell.is_operating_day is True
    assert cell.required_headcount == 2
    assert cell.reason == "default minimum"


def test_demand_precedence_weekday_override() -> None:
    """Weekday override takes precedence over default minimum."""
    bp = BrandProcess(
        id="bp-1",
        brand_id="b-1",
        brand_name="Brand A",
        process_id="p-1",
        process_name="CS",
        calendar_type=CalendarType.ALL_365,
        min_coverage_default=1,
    )
    # Target date 2026-12-07 is a Monday (weekday 0)
    rule_monday = CoverageRule(
        brand_process_id="bp-1",
        weekday=0,
        min_staff=3,
        reason="Peak Monday volumes",
    )
    rules = (rule_monday,)

    # On Monday: gets 3 (weekday override)
    cell_mon = build_demand_cell(bp, date(2026, 12, 7), rules=rules)
    assert cell_mon.required_headcount == 3
    assert cell_mon.reason == "Peak Monday volumes"

    # On Tuesday: falls back to default minimum 1
    cell_tue = build_demand_cell(bp, date(2026, 12, 8), rules=rules)
    assert cell_tue.required_headcount == 1
    assert cell_tue.reason == "default minimum"


def test_demand_precedence_date_override_beats_weekday() -> None:
    """Specific date override takes precedence over weekday override."""
    bp = BrandProcess(
        id="bp-1",
        brand_id="b-1",
        brand_name="Brand A",
        process_id="p-1",
        process_name="CS",
        calendar_type=CalendarType.ALL_365,
        min_coverage_default=1,
    )
    # Target date 2026-12-14 is a Monday (weekday 0)
    rule_monday = CoverageRule(
        brand_process_id="bp-1",
        weekday=0,
        min_staff=2,
        reason="Regular Monday min 2",
    )
    rule_specific_date = CoverageRule(
        brand_process_id="bp-1",
        specific_date=date(2026, 12, 14),
        min_staff=5,
        reason="Flash Sale Spike",
    )
    rules = (rule_monday, rule_specific_date)

    # 14 Dec (Mon): Specific date override wins (5 staff)
    cell_14 = build_demand_cell(bp, date(2026, 12, 14), rules=rules)
    assert cell_14.required_headcount == 5
    assert cell_14.reason == "Flash Sale Spike"

    # 21 Dec (Mon): No date override, weekday override wins (2 staff)
    cell_21 = build_demand_cell(bp, date(2026, 12, 21), rules=rules)
    assert cell_21.required_headcount == 2
    assert cell_21.reason == "Regular Monday min 2"


def test_demand_zero_on_non_operating_days() -> None:
    """Demand must be 0 on non-operating days, even if an override exists."""
    bp = BrandProcess(
        id="bp-backoffice",
        brand_id="b-1",
        brand_name="Brand A",
        process_id="p-acc",
        process_name="Accounting",
        calendar_type=CalendarType.EXCLUDE_SUNDAY_AND_HOLIDAYS,
        min_coverage_default=2,
    )
    sunday = date(2026, 12, 6)
    rule_sunday = CoverageRule(
        brand_process_id="bp-backoffice",
        weekday=6,
        min_staff=10,  # Even if someone accidentally set a rule on Sunday
        reason="Erroneous Sunday rule",
    )
    cell = build_demand_cell(bp, sunday, rules=(rule_sunday,))
    assert cell.is_operating_day is False
    assert cell.required_headcount == 0
    assert cell.reason == "non-operating day"

    # Global holiday on Monday
    holiday_monday = date(2026, 12, 7)
    holidays = (Holiday(date=holiday_monday, name="National Day", brand_id=None),)
    rule_monday = CoverageRule(
        brand_process_id="bp-backoffice",
        weekday=0,
        min_staff=5,
    )
    cell_holiday = build_demand_cell(bp, holiday_monday, holidays=holidays, rules=(rule_monday,))
    assert cell_holiday.is_operating_day is False
    assert cell_holiday.required_headcount == 0
    assert cell_holiday.reason == "non-operating day"


def test_build_demand_matrix_and_lookup() -> None:
    """Test full matrix generation and fast lookup dict."""
    bp1 = BrandProcess(
        id="bp-1",
        brand_id="b-1",
        brand_name="Brand 1",
        process_id="p-1",
        process_name="CS",
        calendar_type=CalendarType.ALL_365,
        min_coverage_default=1,
    )
    bp2 = BrandProcess(
        id="bp-2",
        brand_id="b-2",
        brand_name="Brand 2",
        process_id="p-1",
        process_name="CS",
        calendar_type=CalendarType.ALL_365,
        min_coverage_default=2,
    )

    start = date(2026, 12, 1)
    end = date(2026, 12, 3)

    matrix = build_demand_matrix(
        brand_processes=(bp2, bp1),  # Unsorted order
        start_date=start,
        end_date=end,
    )

    # 3 days * 2 brand processes = 6 cells
    assert len(matrix) == 6

    # Verify deterministic sort order: date first, then bp.id
    assert matrix[0].date == start and matrix[0].brand_process_id == "bp-1"
    assert matrix[1].date == start and matrix[1].brand_process_id == "bp-2"
    assert matrix[2].date == date(2026, 12, 2) and matrix[2].brand_process_id == "bp-1"

    # Lookup test
    lookup = build_demand_lookup(matrix)
    assert len(lookup) == 6
    assert lookup[("bp-1", start)].required_headcount == 1
    assert lookup[("bp-2", start)].required_headcount == 2

    # Inverted date range raises ValueError
    with pytest.raises(ValueError, match="cannot be after end_date"):
        build_demand_matrix(brand_processes=(bp1,), start_date=end, end_date=start)
