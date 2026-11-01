"""Unit tests for the seed data script (app.seed).

Verifies that seed_database() correctly populates the database per SAMPLE_DATA.md:
- 6 Pods (A to F) with proper lead associations
- 36 Employees (6 Leads, 26 Primary Staff, 4 Floaters)
- 4 Processes (CS, ACC, RET, NDR)
- 25 Brands (20 single-resource, 5 multi-resource)
- BrandProcesses and Assignments
- Coverage Rules & Overrides (Pulse, Nova, Aurora)
- Weekly Off Rules (Fixed Mandatory, Fixed Preferred, Rotating, Any)
- Holidays (Christmas Dec 25 global, Dec 10 for BRD-05)
- Pre-seeded leaves for Dec 2026 (Pooja, EMP-018, EMP-026, EMP-029; EMP-007 has 0 leaves)
- Demo users with valid Argon2 password hashes
- Clean database functionality
- Scaled seeding (--scale 3)
"""

from __future__ import annotations

import pytest
from argon2 import PasswordHasher
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.auth import User, UserRole
from app.models.core import Assignment, Brand, BrandProcess, Employee, Pod, Process
from app.models.rules import (
    CoverageRule,
    Holiday,
    Leave,
    WeeklyOffMode,
    WeeklyOffRule,
)
from app.seed import clean_database, seed_database


@pytest.fixture
def db_session() -> Session:
    """Create an isolated in-memory SQLite database and session for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_seed_database_standard_scale(db_session: Session) -> None:
    """Verify standard scale=1 matches SAMPLE_DATA.md exact topology."""
    counts = seed_database(db_session, scale=1, clean=False, demo_password="TestPassword123!")

    # Top-level entity counts
    assert counts["pods"] == 6
    assert counts["employees"] == 36
    assert counts["processes"] == 4
    assert counts["brands"] == 25
    assert counts["coverage_rules"] == 3
    assert counts["holidays"] == 2
    assert counts["leaves"] == 4
    assert counts["users"] == 3

    # Pods and Leads
    pods = db_session.query(Pod).order_by(Pod.name).all()
    assert len(pods) == 6
    for p in pods:
        assert p.lead_employee_id is not None
        assert p.lead is not None
        assert p.lead.pod_id == p.id

    # Employees and Floaters
    floaters = db_session.query(Employee).filter(Employee.is_floater.is_(True)).all()
    assert len(floaters) == 4
    floater_codes = {f.code for f in floaters}
    assert floater_codes == {"EMP-033", "EMP-034", "EMP-035", "EMP-036"}

    # Weekly Off Quotas (EMP-012 and EMP-030 have 2 weekly offs)
    emp_012 = db_session.query(Employee).filter(Employee.code == "EMP-012").one()
    emp_030 = db_session.query(Employee).filter(Employee.code == "EMP-030").one()
    assert emp_012.weekly_off_count == 2
    assert emp_030.weekly_off_count == 2

    # Single-Resource Brands vs Multi-Resource Brands
    brands = db_session.query(Brand).all()
    assert len(brands) == 25

    # Aurora (BRD-01) in Pod A
    aurora = db_session.query(Brand).filter(Brand.code == "BRD-01").one()
    aurora_bps = db_session.query(BrandProcess).filter(BrandProcess.brand_id == aurora.id).all()
    assert len(aurora_bps) == 3  # CS, ACC, NDR

    # Nova (BRD-21) in Pod B has 3 staff assigned
    nova = db_session.query(Brand).filter(Brand.code == "BRD-21").one()
    nova_bps = db_session.query(BrandProcess).filter(BrandProcess.brand_id == nova.id).all()
    assert len(nova_bps) == 3

    nova_asgns = (
        db_session.query(Assignment)
        .filter(Assignment.brand_process_id.in_([bp.id for bp in nova_bps]))
        .all()
    )
    # Aarav (CS Primary, ACC Backup), Pooja (ACC Primary), Vikram (NDR Primary) = 4 assignments
    assert len(nova_asgns) == 4

    # Pulse (BRD-23) CS has 2 Primary staff: Neha & Rahul
    pulse = db_session.query(Brand).filter(Brand.code == "BRD-23").one()
    pulse_cs = (
        db_session.query(BrandProcess)
        .filter(
            BrandProcess.brand_id == pulse.id,
            BrandProcess.process.has(code="CS"),
        )
        .one()
    )
    pulse_asgns = (
        db_session.query(Assignment).filter(Assignment.brand_process_id == pulse_cs.id).all()
    )
    assert len(pulse_asgns) == 2
    pulse_emp_codes = {a.employee.code for a in pulse_asgns}
    assert pulse_emp_codes == {"EMP-021", "EMP-022"}

    # Coverage Rule Overrides
    pulse_cr = (
        db_session.query(CoverageRule).filter(CoverageRule.brand_process_id == pulse_cs.id).one()
    )
    assert pulse_cr.weekday == 0  # Monday
    assert pulse_cr.min_staff == 2

    aurora_cs = (
        db_session.query(BrandProcess)
        .filter(
            BrandProcess.brand_id == aurora.id,
            BrandProcess.process.has(code="CS"),
        )
        .one()
    )
    aurora_cr = (
        db_session.query(CoverageRule).filter(CoverageRule.brand_process_id == aurora_cs.id).one()
    )
    assert aurora_cr.specific_date.isoformat() == "2026-12-18"
    assert aurora_cr.min_staff == 2

    # Weekly-off Policy Rules
    mand_rules = (
        db_session.query(WeeklyOffRule)
        .filter(WeeklyOffRule.mode == WeeklyOffMode.FIXED_MANDATORY)
        .all()
    )
    assert len(mand_rules) == 2
    mand_emp_codes = {r.employee.code for r in mand_rules}
    assert mand_emp_codes == {"EMP-023", "EMP-024"}
    for r in mand_rules:
        assert r.weekdays == [4]  # Friday

    pref_rules = (
        db_session.query(WeeklyOffRule)
        .filter(WeeklyOffRule.mode == WeeklyOffMode.FIXED_PREFERRED)
        .all()
    )
    assert len(pref_rules) == 3
    pref_emp_codes = {r.employee.code for r in pref_rules}
    assert pref_emp_codes == {"EMP-007", "EMP-015", "EMP-022"}

    # Holidays
    holidays = db_session.query(Holiday).all()
    assert len(holidays) == 2
    global_h = [h for h in holidays if h.brand_id is None]
    assert len(global_h) == 1
    assert global_h[0].name == "Christmas"
    assert global_h[0].date.isoformat() == "2026-12-25"

    brand_h = [h for h in holidays if h.brand_id is not None]
    assert len(brand_h) == 1
    assert brand_h[0].name == "Regional Event"
    assert brand_h[0].brand.code == "BRD-05"

    # Leaves: EMP-007 has 0 leaves for demo clean state
    emp_007 = db_session.query(Employee).filter(Employee.code == "EMP-007").one()
    emp_007_leaves = db_session.query(Leave).filter(Leave.employee_id == emp_007.id).all()
    assert len(emp_007_leaves) == 0

    # 4 Pre-seeded approved leaves
    leaves = db_session.query(Leave).all()
    assert len(leaves) == 4
    leave_emp_codes = {lv.employee.code for lv in leaves}
    assert leave_emp_codes == {"EMP-016", "EMP-018", "EMP-026", "EMP-029"}

    # Users and Passwords
    users = db_session.query(User).all()
    assert len(users) == 3
    hasher = PasswordHasher()
    for u in users:
        assert hasher.verify(u.password_hash, "TestPassword123!")

    ops_user = db_session.query(User).filter(User.role == UserRole.OPS_MANAGER).one()
    assert ops_user.email == "ops@example.test"
    assert ops_user.employee_id is None

    lead_user = db_session.query(User).filter(User.role == UserRole.POD_LEAD).one()
    assert lead_user.email == "lead.a@example.test"
    assert lead_user.employee.code == "EMP-001"

    emp_user = db_session.query(User).filter(User.role == UserRole.EMPLOYEE).one()
    assert emp_user.email == "emp@example.test"
    assert emp_user.employee.code == "EMP-007"


def test_clean_database(db_session: Session) -> None:
    """Verify clean_database completely clears tables without foreign key violations."""
    seed_database(db_session, scale=1, clean=False)
    assert db_session.query(Employee).count() == 36

    clean_database(db_session)
    assert db_session.query(Employee).count() == 0
    assert db_session.query(Pod).count() == 0
    assert db_session.query(Brand).count() == 0
    assert db_session.query(Process).count() == 0
    assert db_session.query(Assignment).count() == 0
    assert db_session.query(CoverageRule).count() == 0
    assert db_session.query(Holiday).count() == 0
    assert db_session.query(Leave).count() == 0
    assert db_session.query(User).count() == 0


def test_seed_database_scale_3(db_session: Session) -> None:
    """Verify scale=3 produces stress dataset topology: 18 pods, 108 emps, 75 brands."""
    counts = seed_database(db_session, scale=3, clean=False)
    assert counts["pods"] == 18
    assert counts["employees"] == 108
    assert counts["brands"] == 75
