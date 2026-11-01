"""Unit tests for rules, availability, leave, and holiday ORM models."""

from collections.abc import Generator
from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.core import Brand, BrandProcess, CalendarType, Employee, Pod, Process
from app.models.rules import (
    CompOffKind,
    CompOffLedger,
    CoverageRule,
    EmployeePreference,
    Holiday,
    Leave,
    LeaveStatus,
    LeaveType,
    PreferenceKind,
    WeeklyOffMode,
    WeeklyOffRule,
)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Create an in-memory SQLite database and provide a test session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_rules_table_metadata() -> None:
    """Verify that all rules tables are registered on Base.metadata."""
    table_names = set(Base.metadata.tables.keys())
    expected = {
        "coverage_rules",
        "holidays",
        "leaves",
        "comp_off_ledger",
        "weekly_off_rules",
        "employee_preferences",
    }
    assert expected.issubset(table_names)


def test_coverage_rule_and_constraints(db_session: Session) -> None:
    """Test CoverageRule constraints: mutual exclusivity of weekday vs specific_date."""
    brand = Brand(name="Brand R", code="BR")
    proc = Process(name="Voice", code="VCE")
    db_session.add_all([brand, proc])
    db_session.flush()

    bp = BrandProcess(brand_id=brand.id, process_id=proc.id, calendar_type=CalendarType.ALL_365)
    db_session.add(bp)
    db_session.flush()

    # Valid: with weekday
    rule_weekday = CoverageRule(brand_process_id=bp.id, weekday=0, min_staff=2)
    db_session.add(rule_weekday)
    db_session.commit()

    # Valid: with specific_date
    rule_date = CoverageRule(brand_process_id=bp.id, specific_date=date(2026, 12, 14), min_staff=3)
    db_session.add(rule_date)
    db_session.commit()

    # Navigation from BrandProcess
    queried_bp = db_session.execute(
        select(BrandProcess).where(BrandProcess.id == bp.id)
    ).scalar_one()
    assert len(queried_bp.coverage_rules) == 2

    # Invalid: both provided -> CheckConstraint failure
    rule_both = CoverageRule(
        brand_process_id=bp.id,
        weekday=1,
        specific_date=date(2026, 12, 15),
        min_staff=2,
    )
    db_session.add(rule_both)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_holiday_global_and_brand_scoped(db_session: Session) -> None:
    """Test Holiday unique constraint on (date, brand_id)."""
    brand = Brand(name="Brand H", code="BH")
    db_session.add(brand)
    db_session.flush()

    # Global holiday
    h_global = Holiday(date=date(2026, 12, 25), name="Christmas", brand_id=None)
    # Brand-scoped holiday on same date
    h_brand = Holiday(date=date(2026, 12, 25), name="Brand Special", brand_id=brand.id)
    db_session.add_all([h_global, h_brand])
    db_session.commit()

    # Duplicate brand holiday on same date
    h_dup = Holiday(date=date(2026, 12, 25), name="Duplicate Brand Holiday", brand_id=brand.id)
    db_session.add(h_dup)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_leave_model_and_date_range_check(db_session: Session) -> None:
    """Test Leave model and check constraint enforcing end_date >= start_date."""
    pod = Pod(name="Pod L")
    db_session.add(pod)
    db_session.flush()

    emp = Employee(code="EMP-L1", full_name="Leave Tester", pod_id=pod.id)
    db_session.add(emp)
    db_session.flush()

    # Valid leave
    valid_leave = Leave(
        employee_id=emp.id,
        start_date=date(2026, 12, 10),
        end_date=date(2026, 12, 12),
        type=LeaveType.PLANNED,
        status=LeaveStatus.APPROVED,
        note="Vacation",
    )
    db_session.add(valid_leave)
    db_session.commit()

    queried_emp = db_session.execute(select(Employee).where(Employee.id == emp.id)).scalar_one()
    assert len(queried_emp.leaves) == 1
    assert queried_emp.leaves[0].type == LeaveType.PLANNED

    # Invalid leave: end_date < start_date
    invalid_leave = Leave(
        employee_id=emp.id,
        start_date=date(2026, 12, 15),
        end_date=date(2026, 12, 10),
        type=LeaveType.SICK,
    )
    db_session.add(invalid_leave)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_compoff_weeklyoff_and_preference_models(db_session: Session) -> None:
    """Test CompOffLedger, WeeklyOffRule, and EmployeePreference models and navigation."""
    pod = Pod(name="Pod R")
    db_session.add(pod)
    db_session.flush()

    emp = Employee(code="EMP-R1", full_name="Rules Tester", pod_id=pod.id)
    db_session.add(emp)
    db_session.flush()

    # 1. CompOff entry
    compoff = CompOffLedger(
        employee_id=emp.id,
        entry_date=date(2026, 12, 1),
        kind=CompOffKind.EARNED,
        note="Holiday work",
    )
    # 2. WeeklyOffRule
    weekly_rule = WeeklyOffRule(
        employee_id=emp.id,
        mode=WeeklyOffMode.FIXED_MANDATORY,
        weekdays=[6],  # Sunday
    )
    # 3. Preference
    pref = EmployeePreference(
        employee_id=emp.id,
        kind=PreferenceKind.PREFERRED_OFF_WEEKDAY,
        value={"weekday": 6},
        weight=5,
    )
    db_session.add_all([compoff, weekly_rule, pref])
    db_session.commit()

    queried_emp = db_session.execute(select(Employee).where(Employee.id == emp.id)).scalar_one()
    assert len(queried_emp.comp_off_entries) == 1
    assert queried_emp.comp_off_entries[0].kind == CompOffKind.EARNED

    assert len(queried_emp.weekly_off_rules) == 1
    assert queried_emp.weekly_off_rules[0].mode == WeeklyOffMode.FIXED_MANDATORY
    assert queried_emp.weekly_off_rules[0].weekdays == [6]

    assert len(queried_emp.preferences) == 1
    assert queried_emp.preferences[0].kind == PreferenceKind.PREFERRED_OFF_WEEKDAY
    assert queried_emp.preferences[0].value == {"weekday": 6}
