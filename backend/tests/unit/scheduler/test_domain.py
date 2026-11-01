"""Unit tests for pure-Python scheduler domain types and constraints."""

from datetime import date

import pytest

from app.scheduler.domain import (
    Conflict,
    ConflictCode,
    ConflictSeverity,
    CoverageCell,
    CoverageRule,
    DemandCell,
    SupplyAvailability,
    SupplyCell,
    ValidationResult,
)


def test_scheduler_pure_python_isolation() -> None:
    """Verify that scheduler module does not import db, api, models, fastapi, or sqlalchemy."""
    forbidden = ["fastapi", "sqlalchemy", "app.api", "app.db", "app.models"]
    for _mod in forbidden:
        # Check that scheduler itself doesn't import these modules
        import app.scheduler
        import app.scheduler.domain

        # Verify no forbidden module is referenced in scheduler domain globals
        for global_val in vars(app.scheduler.domain).values():
            val_mod = getattr(global_val, "__module__", "")
            for f in forbidden:
                assert not val_mod.startswith(f), f"Scheduler leaks forbidden dependency: {val_mod}"


def test_coverage_rule_validation() -> None:
    """Test CoverageRule constraints on weekday vs specific_date."""
    # Valid with weekday
    rule_weekday = CoverageRule(
        brand_process_id="bp-1",
        min_staff=2,
        weekday=0,  # Monday
    )
    assert rule_weekday.weekday == 0
    assert rule_weekday.specific_date is None

    # Valid with specific_date
    rule_date = CoverageRule(
        brand_process_id="bp-1",
        min_staff=3,
        specific_date=date(2026, 12, 14),
    )
    assert rule_date.specific_date == date(2026, 12, 14)
    assert rule_date.weekday is None

    # Invalid: neither provided
    with pytest.raises(ValueError, match="exactly one of 'weekday' or 'specific_date'"):
        CoverageRule(brand_process_id="bp-1", min_staff=2)

    # Invalid: both provided
    with pytest.raises(ValueError, match="exactly one of 'weekday' or 'specific_date'"):
        CoverageRule(
            brand_process_id="bp-1",
            min_staff=2,
            weekday=2,
            specific_date=date(2026, 12, 14),
        )

    # Invalid weekday (<0 or >6)
    with pytest.raises(ValueError, match="Weekday must be between 0"):
        CoverageRule(brand_process_id="bp-1", min_staff=2, weekday=7)


def test_validation_result_from_conflicts() -> None:
    """Test ValidationResult computation from conflict list."""
    conflicts = (
        Conflict(
            code=ConflictCode.E001,
            severity=ConflictSeverity.BLOCKING,
            brand_process_id="bp-1",
            date_from=date(2026, 12, 14),
            message="No coverage on 14 Dec",
        ),
        Conflict(
            code=ConflictCode.E008,
            severity=ConflictSeverity.WARNING,
            employee_id="emp-1",
            date_from=date(2026, 12, 14),
            message="Employee on 4 processes",
        ),
        Conflict(
            code=ConflictCode.W002,
            severity=ConflictSeverity.INFO,
            employee_id="emp-2",
            message="Weekend off distribution gap",
        ),
    )

    result = ValidationResult.from_conflicts(conflicts)
    assert not result.is_valid
    assert result.blocking_count == 1
    assert result.warning_count == 1
    assert result.info_count == 1
    assert len(result.conflicts) == 3

    # Clean validation result with only warnings/info
    clean_result = ValidationResult.from_conflicts(conflicts[1:])
    assert clean_result.is_valid
    assert clean_result.blocking_count == 0
    assert clean_result.warning_count == 1
    assert clean_result.info_count == 1


def test_domain_dataclasses_immutability() -> None:
    """Verify dataclasses are frozen and enforce immutability."""
    d_cell = DemandCell(
        brand_process_id="bp-1",
        brand_id="b-1",
        brand_name="Brand A",
        process_id="p-1",
        process_name="Inbound Voice",
        date=date(2026, 12, 1),
        is_operating_day=True,
        required_headcount=2,
    )
    with pytest.raises(AttributeError):
        # Object is frozen
        d_cell.required_headcount = 3  # type: ignore[misc]

    s_cell = SupplyCell(
        employee_id="e-1",
        employee_code="EMP-001",
        employee_name="Alice Smith",
        date=date(2026, 12, 1),
        availability=SupplyAvailability.AVAILABLE,
    )
    with pytest.raises(AttributeError):
        s_cell.availability = SupplyAvailability.LEAVE  # type: ignore[misc]


def test_conflict_code_catalog() -> None:
    """Verify all required conflict codes from SCHEDULING_ENGINE.md are present."""
    expected_codes = {
        "E001",
        "E002",
        "E003",
        "E004",
        "E005",
        "E006",
        "E007",
        "E008",
        "E009",
        "W001",
        "W002",
        "W003",
        "W004",
    }
    actual_codes = {code.value for code in ConflictCode}
    assert expected_codes == actual_codes


def test_coverage_cell_property() -> None:
    """Test CoverageCell is_fully_covered property."""
    covered = CoverageCell(
        brand_process_id="bp-1",
        date=date(2026, 12, 1),
        required=2,
        covered=2,
        shortfall=0,
    )
    assert covered.is_fully_covered

    shortfall = CoverageCell(
        brand_process_id="bp-1",
        date=date(2026, 12, 1),
        required=2,
        covered=1,
        shortfall=1,
    )
    assert not shortfall.is_fully_covered
