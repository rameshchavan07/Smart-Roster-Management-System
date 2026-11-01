"""Unit tests for the pure-Python operating calendar resolver."""

from datetime import date

import pytest

from app.scheduler.calendar import (
    get_applicable_holidays,
    get_operating_dates,
    has_applicable_holiday,
    is_holiday_applicable,
    is_operating_day,
    resolve_calendar_matrix,
    resolve_operating_days,
)
from app.scheduler.domain import BrandProcess, CalendarType, Holiday


def test_calendar_module_isolation() -> None:
    """Verify calendar resolver has no dependencies on fastapi, sqlalchemy, or app.db."""
    forbidden = ["fastapi", "sqlalchemy", "app.api", "app.db", "app.models"]
    import app.scheduler.calendar

    for global_val in vars(app.scheduler.calendar).values():
        val_mod = getattr(global_val, "__module__", "")
        for f in forbidden:
            assert not val_mod.startswith(f), f"Calendar leaks forbidden dependency: {val_mod}"


def test_holiday_applicability() -> None:
    """Test global vs brand-scoped holiday matching."""
    global_holiday = Holiday(date=date(2026, 12, 25), name="Christmas", brand_id=None)
    aurora_holiday = Holiday(date=date(2026, 12, 10), name="Founder Day", brand_id="brand-aurora")

    # Global holiday applies to any brand
    assert is_holiday_applicable(global_holiday, "brand-aurora")
    assert is_holiday_applicable(global_holiday, "brand-glowcare")

    # Brand-scoped holiday applies only to the target brand
    assert is_holiday_applicable(aurora_holiday, "brand-aurora")
    assert not is_holiday_applicable(aurora_holiday, "brand-glowcare")

    holidays = (global_holiday, aurora_holiday)

    # get_applicable_holidays
    aurora_list = get_applicable_holidays(holidays, "brand-aurora")
    assert len(aurora_list) == 2

    glowcare_list = get_applicable_holidays(holidays, "brand-glowcare")
    assert len(glowcare_list) == 1
    assert glowcare_list[0].name == "Christmas"

    # has_applicable_holiday on specific dates
    assert has_applicable_holiday(holidays, "brand-aurora", date(2026, 12, 10))
    assert not has_applicable_holiday(holidays, "brand-glowcare", date(2026, 12, 10))
    assert has_applicable_holiday(holidays, "brand-glowcare", date(2026, 12, 25))


def test_calendar_all_365() -> None:
    """ALL_365 brand-processes operate every single day including holidays and Sundays."""
    bp = BrandProcess(
        id="bp-1",
        brand_id="b-1",
        brand_name="Global 24/7",
        process_id="p-1",
        process_name="Live Support",
        calendar_type=CalendarType.ALL_365,
    )
    holidays = (Holiday(date=date(2026, 12, 25), name="Christmas", brand_id=None),)

    # Regular weekday (Wed 2026-12-02)
    assert is_operating_day(bp, date(2026, 12, 2), holidays)

    # Sunday (Sun 2026-12-06)
    assert is_operating_day(bp, date(2026, 12, 6), holidays)

    # Global holiday (Fri 2026-12-25)
    assert is_operating_day(bp, date(2026, 12, 25), holidays)


def test_calendar_all_except_holidays() -> None:
    """ALL_EXCEPT_HOLIDAYS operates on all days except applicable public holidays."""
    bp_aurora = BrandProcess(
        id="bp-aurora",
        brand_id="b-aurora",
        brand_name="Aurora",
        process_id="p-cs",
        process_name="CS",
        calendar_type=CalendarType.ALL_EXCEPT_HOLIDAYS,
    )
    bp_glow = BrandProcess(
        id="bp-glow",
        brand_id="b-glow",
        brand_name="GlowCare",
        process_id="p-cs",
        process_name="CS",
        calendar_type=CalendarType.ALL_EXCEPT_HOLIDAYS,
    )
    holidays = (
        Holiday(date=date(2026, 12, 25), name="Christmas", brand_id=None),
        Holiday(date=date(2026, 12, 15), name="Aurora Day", brand_id="b-aurora"),
    )

    # Regular weekday
    assert is_operating_day(bp_aurora, date(2026, 12, 2), holidays)
    # Sunday (operates because only holidays are excluded)
    assert is_operating_day(bp_aurora, date(2026, 12, 6), holidays)

    # Global holiday (Christmas) -> non-operating for both
    assert not is_operating_day(bp_aurora, date(2026, 12, 25), holidays)
    assert not is_operating_day(bp_glow, date(2026, 12, 25), holidays)

    # Brand-scoped holiday -> non-operating for Aurora, operating for GlowCare
    assert not is_operating_day(bp_aurora, date(2026, 12, 15), holidays)
    assert is_operating_day(bp_glow, date(2026, 12, 15), holidays)


def test_calendar_exclude_sunday_and_holidays() -> None:
    """EXCLUDE_SUNDAY_AND_HOLIDAYS operates on Mon-Sat except public holidays."""
    bp = BrandProcess(
        id="bp-backoffice",
        brand_id="b-1",
        brand_name="Retail Brand",
        process_id="p-acc",
        process_name="Accounting",
        calendar_type=CalendarType.EXCLUDE_SUNDAY_AND_HOLIDAYS,
    )
    holidays = (Holiday(date=date(2026, 12, 25), name="Christmas", brand_id=None),)

    # Regular weekday (Mon 2026-12-07) -> operates
    assert is_operating_day(bp, date(2026, 12, 7), holidays)

    # Saturday (Sat 2026-12-05) -> operates
    assert is_operating_day(bp, date(2026, 12, 5), holidays)

    # Sunday (Sun 2026-12-06) -> non-operating
    assert not is_operating_day(bp, date(2026, 12, 6), holidays)

    # Holiday on weekday (Fri 2026-12-25) -> non-operating
    assert not is_operating_day(bp, date(2026, 12, 25), holidays)


def test_resolve_operating_days_range() -> None:
    """Test full range resolution and error handling on inverted range."""
    bp = BrandProcess(
        id="bp-1",
        brand_id="b-1",
        brand_name="Brand",
        process_id="p-1",
        process_name="Process",
        calendar_type=CalendarType.EXCLUDE_SUNDAY_AND_HOLIDAYS,
    )
    start = date(2026, 12, 1)  # Tuesday
    end = date(2026, 12, 7)  # Following Monday (7 days total: Tue, Wed, Thu, Fri, Sat, Sun, Mon)
    holidays = (Holiday(date=date(2026, 12, 4), name="Special Friday", brand_id="b-1"),)

    result = resolve_operating_days(bp, start, end, holidays)
    assert len(result) == 7

    # Tue 1, Wed 2, Thu 3: Operating
    assert result[date(2026, 12, 1)] is True
    assert result[date(2026, 12, 2)] is True
    assert result[date(2026, 12, 3)] is True
    # Fri 4: Holiday -> False
    assert result[date(2026, 12, 4)] is False
    # Sat 5: Operating
    assert result[date(2026, 12, 5)] is True
    # Sun 6: Sunday -> False
    assert result[date(2026, 12, 6)] is False
    # Mon 7: Operating
    assert result[date(2026, 12, 7)] is True

    # get_operating_dates returns exactly the 5 operating dates
    operating_dates = get_operating_dates(bp, start, end, holidays)
    assert len(operating_dates) == 5
    assert date(2026, 12, 4) not in operating_dates
    assert date(2026, 12, 6) not in operating_dates

    # Inverted date range raises ValueError
    with pytest.raises(ValueError, match="cannot be after end_date"):
        resolve_operating_days(bp, end, start, holidays)


def test_resolve_calendar_matrix() -> None:
    """Test resolution of multi-brandprocess calendar matrix."""
    bp_365 = BrandProcess(
        id="bp-365",
        brand_id="b-1",
        brand_name="B1",
        process_id="p-1",
        process_name="P1",
        calendar_type=CalendarType.ALL_365,
    )
    bp_no_sun = BrandProcess(
        id="bp-no-sun",
        brand_id="b-2",
        brand_name="B2",
        process_id="p-2",
        process_name="P2",
        calendar_type=CalendarType.EXCLUDE_SUNDAY_AND_HOLIDAYS,
    )

    sunday = date(2026, 12, 6)
    matrix = resolve_calendar_matrix(
        brand_processes=[bp_365, bp_no_sun],
        start_date=sunday,
        end_date=sunday,
        holidays=(),
    )

    assert matrix[("bp-365", sunday)] is True
    assert matrix[("bp-no-sun", sunday)] is False


# ---------------------------------------------------------------------------
# Table-Driven Calendar Matrix Suite (TC-CAL-01 to TC-CAL-04)
# ---------------------------------------------------------------------------
CALENDAR_TABLE_CASES = [
    # TC-CAL-01: ALL_365 operates 365 days a year including Sundays, Saturdays, and Holidays
    (
        "TC-CAL-01-weekday",
        CalendarType.ALL_365,
        date(2026, 12, 2),  # Wednesday
        "brand-1",
        (Holiday(date=date(2026, 12, 25), name="Christmas"),),
        True,
    ),
    (
        "TC-CAL-01-saturday",
        CalendarType.ALL_365,
        date(2026, 12, 5),  # Saturday
        "brand-1",
        (),
        True,
    ),
    (
        "TC-CAL-01-sunday",
        CalendarType.ALL_365,
        date(2026, 12, 6),  # Sunday
        "brand-1",
        (),
        True,
    ),
    (
        "TC-CAL-01-global-holiday",
        CalendarType.ALL_365,
        date(2026, 12, 25),  # Christmas Friday
        "brand-1",
        (Holiday(date=date(2026, 12, 25), name="Christmas"),),
        True,
    ),
    (
        "TC-CAL-01-brand-holiday",
        CalendarType.ALL_365,
        date(2026, 12, 10),
        "brand-1",
        (Holiday(date=date(2026, 12, 10), name="Founder Day", brand_id="brand-1"),),
        True,
    ),
    # TC-CAL-02: ALL_EXCEPT_HOLIDAYS operates on all days except applicable public holidays
    (
        "TC-CAL-02-weekday-normal",
        CalendarType.ALL_EXCEPT_HOLIDAYS,
        date(2026, 12, 2),  # Wednesday
        "brand-1",
        (Holiday(date=date(2026, 12, 25), name="Christmas"),),
        True,
    ),
    (
        "TC-CAL-02-sunday-normal",
        CalendarType.ALL_EXCEPT_HOLIDAYS,
        date(2026, 12, 6),  # Sunday (no holiday) -> Operates!
        "brand-1",
        (),
        True,
    ),
    (
        "TC-CAL-02-saturday-normal",
        CalendarType.ALL_EXCEPT_HOLIDAYS,
        date(2026, 12, 5),  # Saturday -> Operates!
        "brand-1",
        (),
        True,
    ),
    (
        "TC-CAL-02-global-holiday",
        CalendarType.ALL_EXCEPT_HOLIDAYS,
        date(2026, 12, 25),  # Christmas Friday -> Non-operating
        "brand-1",
        (Holiday(date=date(2026, 12, 25), name="Christmas"),),
        False,
    ),
    (
        "TC-CAL-02-holiday-on-sunday",
        CalendarType.ALL_EXCEPT_HOLIDAYS,
        date(2026, 12, 6),  # Sunday + Holiday -> Non-operating
        "brand-1",
        (Holiday(date=date(2026, 12, 6), name="Sunday Festival"),),
        False,
    ),
    # TC-CAL-03: EXCLUDE_SUNDAY_AND_HOLIDAYS operates Mon-Sat except public holidays
    (
        "TC-CAL-03-monday-normal",
        CalendarType.EXCLUDE_SUNDAY_AND_HOLIDAYS,
        date(2026, 12, 7),  # Monday -> Operates
        "brand-1",
        (),
        True,
    ),
    (
        "TC-CAL-03-saturday-normal",
        CalendarType.EXCLUDE_SUNDAY_AND_HOLIDAYS,
        date(2026, 12, 5),  # Saturday -> Operates
        "brand-1",
        (),
        True,
    ),
    (
        "TC-CAL-03-sunday-normal",
        CalendarType.EXCLUDE_SUNDAY_AND_HOLIDAYS,
        date(2026, 12, 6),  # Sunday -> Non-operating
        "brand-1",
        (),
        False,
    ),
    (
        "TC-CAL-03-weekday-holiday",
        CalendarType.EXCLUDE_SUNDAY_AND_HOLIDAYS,
        date(2026, 12, 25),  # Friday Christmas -> Non-operating
        "brand-1",
        (Holiday(date=date(2026, 12, 25), name="Christmas"),),
        False,
    ),
    (
        "TC-CAL-03-sunday-holiday",
        CalendarType.EXCLUDE_SUNDAY_AND_HOLIDAYS,
        date(2026, 12, 6),  # Sunday + Holiday -> Non-operating
        "brand-1",
        (Holiday(date=date(2026, 12, 6), name="Sunday Festival"),),
        False,
    ),
    # TC-CAL-04: Brand-specific holiday affects only matching brand
    (
        "TC-CAL-04-matching-brand",
        CalendarType.ALL_EXCEPT_HOLIDAYS,
        date(2026, 12, 10),
        "brand-aurora",
        (Holiday(date=date(2026, 12, 10), name="Aurora Day", brand_id="brand-aurora"),),
        False,  # Closed for Aurora
    ),
    (
        "TC-CAL-04-other-brand",
        CalendarType.ALL_EXCEPT_HOLIDAYS,
        date(2026, 12, 10),
        "brand-glowcare",
        (Holiday(date=date(2026, 12, 10), name="Aurora Day", brand_id="brand-aurora"),),
        True,  # Open for GlowCare
    ),
    (
        "TC-CAL-04-exclude-sunday-matching-brand",
        CalendarType.EXCLUDE_SUNDAY_AND_HOLIDAYS,
        date(2026, 12, 10),  # Thursday
        "brand-aurora",
        (Holiday(date=date(2026, 12, 10), name="Aurora Day", brand_id="brand-aurora"),),
        False,  # Closed for Aurora
    ),
    (
        "TC-CAL-04-exclude-sunday-other-brand",
        CalendarType.EXCLUDE_SUNDAY_AND_HOLIDAYS,
        date(2026, 12, 10),  # Thursday
        "brand-glowcare",
        (Holiday(date=date(2026, 12, 10), name="Aurora Day", brand_id="brand-aurora"),),
        True,  # Open for GlowCare
    ),
]


@pytest.mark.parametrize(
    ("case_id", "cal_type", "target_date", "brand_id", "holidays", "expected_operating"),
    CALENDAR_TABLE_CASES,
)
def test_calendar_matrix_table_driven(
    case_id: str,
    cal_type: CalendarType,
    target_date: date,
    brand_id: str,
    holidays: tuple[Holiday, ...],
    expected_operating: bool,
) -> None:
    """Parametrized table-driven test covering all calendar types, day types, and holiday scopes."""
    bp = BrandProcess(
        id=f"bp-{brand_id}",
        brand_id=brand_id,
        brand_name=f"Brand {brand_id}",
        process_id="proc-1",
        process_name="CS",
        calendar_type=cal_type,
    )
    result = is_operating_day(bp, target_date, holidays)
    assert result == expected_operating, (
        f"Case {case_id} failed: Expected operating={expected_operating} "
        f"for {cal_type.value} on {target_date} with {len(holidays)} holiday(s), got {result}"
    )

