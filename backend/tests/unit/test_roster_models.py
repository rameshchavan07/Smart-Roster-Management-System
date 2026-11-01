"""Unit tests for roster, conflict, user, and audit ORM models."""

import uuid
from collections.abc import Generator
from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.auth import AuditLog, User, UserRole
from app.models.core import Brand, BrandProcess, CalendarType, Employee, Pod, Process
from app.models.roster import (
    ConflictSeverity,
    EntrySource,
    RosterConflict,
    RosterEntry,
    RosterEntryStatus,
    RosterPeriod,
    RosterPeriodStatus,
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


def test_roster_table_metadata() -> None:
    """Verify that all auth, audit, and roster tables are registered on Base.metadata."""
    table_names = set(Base.metadata.tables.keys())
    expected = {
        "users",
        "audit_logs",
        "roster_periods",
        "roster_entries",
        "roster_conflicts",
    }
    assert expected.issubset(table_names)


def test_user_and_audit_log_models(db_session: Session) -> None:
    """Test User creation, role assignment, Employee link, and AuditLog recording."""
    pod = Pod(name="Pod Operations")
    db_session.add(pod)
    db_session.flush()

    emp = Employee(code="EMP-MGR", full_name="Ops Lead", pod_id=pod.id)
    db_session.add(emp)
    db_session.flush()

    # Create User
    user = User(
        email="ops.lead@example.test",
        password_hash="scrypt:hashedpassword",
        role=UserRole.OPS_MANAGER,
        employee_id=emp.id,
    )
    db_session.add(user)
    db_session.commit()

    # Query back User & test navigation to Employee
    queried_user = db_session.execute(
        select(User).where(User.email == "ops.lead@example.test")
    ).scalar_one()
    assert queried_user.role == UserRole.OPS_MANAGER
    assert queried_user.employee is not None
    assert queried_user.employee.code == "EMP-MGR"

    # Create AuditLog
    audit = AuditLog(
        user_id=user.id,
        action="roster.published",
        entity_type="RosterPeriod",
        entity_id=str(uuid.uuid4()),
        before={"status": "DRAFT"},
        after={"status": "PUBLISHED"},
    )
    db_session.add(audit)
    db_session.commit()

    queried_audit = db_session.execute(
        select(AuditLog).where(AuditLog.action == "roster.published")
    ).scalar_one()
    assert queried_audit.user is not None
    assert queried_audit.user.email == "ops.lead@example.test"
    assert queried_audit.before == {"status": "DRAFT"}
    assert queried_audit.after == {"status": "PUBLISHED"}

    # Unique email constraint test
    dup_user = User(
        email="ops.lead@example.test",
        password_hash="hash2",
        role=UserRole.EMPLOYEE,
    )
    db_session.add(dup_user)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_roster_period_and_versioning(db_session: Session) -> None:
    """Test RosterPeriod version tracking, self-referential tree, and unique constraints."""
    user = User(
        email="planner@example.test",
        password_hash="secret",
        role=UserRole.OPS_MANAGER,
    )
    db_session.add(user)
    db_session.flush()

    month = date(2026, 12, 1)

    # Version 1
    period_v1 = RosterPeriod(
        month=month,
        version=1,
        status=RosterPeriodStatus.DRAFT,
        solver_status="OPTIMAL",
        generation_params={"seed": 42, "time_limit": 30.0},
        created_by_id=user.id,
    )
    db_session.add(period_v1)
    db_session.commit()

    # Version 2 referencing Version 1
    period_v2 = RosterPeriod(
        month=month,
        version=2,
        status=RosterPeriodStatus.DRAFT,
        solver_status="OPTIMAL",
        generation_params={"seed": 42, "note": "manual adjustments"},
        parent_period_id=period_v1.id,
        created_by_id=user.id,
    )
    db_session.add(period_v2)
    db_session.commit()

    # Test parent/child navigation
    queried_v1 = db_session.execute(
        select(RosterPeriod).where(RosterPeriod.id == period_v1.id)
    ).scalar_one()
    assert len(queried_v1.child_periods) == 1
    assert queried_v1.child_periods[0].version == 2

    queried_v2 = db_session.execute(
        select(RosterPeriod).where(RosterPeriod.id == period_v2.id)
    ).scalar_one()
    assert queried_v2.parent_period is not None
    assert queried_v2.parent_period.version == 1
    assert queried_v2.creator is not None
    assert queried_v2.creator.email == "planner@example.test"

    # Test unique constraint on (month, version)
    duplicate_v1 = RosterPeriod(
        month=month,
        version=1,
        status=RosterPeriodStatus.GENERATING,
    )
    db_session.add(duplicate_v1)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_roster_entries_and_constraints(db_session: Session) -> None:
    """Test RosterEntry creation, foreign keys, unique constraint, and cascade deletion."""
    pod = Pod(name="Pod Alpha")
    emp = Employee(code="EMP-E1", full_name="Roster Emp", pod=pod)
    period = RosterPeriod(month=date(2026, 12, 1), version=1)
    db_session.add_all([pod, emp, period])
    db_session.flush()

    # Valid entry
    entry1 = RosterEntry(
        roster_period_id=period.id,
        employee_id=emp.id,
        date=date(2026, 12, 1),
        status=RosterEntryStatus.WORK,
        source=EntrySource.AUTO,
    )
    entry2 = RosterEntry(
        roster_period_id=period.id,
        employee_id=emp.id,
        date=date(2026, 12, 2),
        status=RosterEntryStatus.WEEKLY_OFF,
        source=EntrySource.MANUAL,
        is_locked=True,
    )
    db_session.add_all([entry1, entry2])
    db_session.commit()

    queried_period = db_session.execute(
        select(RosterPeriod).where(RosterPeriod.id == period.id)
    ).scalar_one()
    assert len(queried_period.entries) == 2

    # Duplicate entry on same period, employee, date
    dup_entry = RosterEntry(
        roster_period_id=period.id,
        employee_id=emp.id,
        date=date(2026, 12, 1),
        status=RosterEntryStatus.LEAVE,
    )
    db_session.add(dup_entry)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Cascade delete test
    db_session.delete(queried_period)
    db_session.commit()
    remaining_entries = db_session.execute(select(RosterEntry)).scalars().all()
    assert len(remaining_entries) == 0


def test_roster_conflicts_and_acknowledgement(db_session: Session) -> None:
    """Test RosterConflict creation, JSON fields, FK relationships, and acknowledge flow."""
    pod = Pod(name="Pod Gamma")
    emp = Employee(code="EMP-C1", full_name="Conflict Employee", pod=pod)
    brand = Brand(name="Brand C", code="BC")
    proc = Process(name="Process C", code="PC")
    user = User(email="ack.lead@example.test", password_hash="hash", role=UserRole.POD_LEAD)
    period = RosterPeriod(month=date(2026, 12, 1), version=1)
    db_session.add_all([pod, emp, brand, proc, user, period])
    db_session.flush()

    bp = BrandProcess(brand_id=brand.id, process_id=proc.id, calendar_type=CalendarType.ALL_365)
    db_session.add(bp)
    db_session.flush()

    conflict = RosterConflict(
        roster_period_id=period.id,
        code="C01",
        severity=ConflictSeverity.BLOCKING,
        brand_process_id=bp.id,
        employee_id=emp.id,
        date_from=date(2026, 12, 5),
        date_to=date(2026, 12, 5),
        root_causes=["Process is OPEN on 2026-12-05", "Assigned staff is on approved leave"],
        message="Daily coverage shortfall for Brand C / Process C on 2026-12-05",
        suggestions=[{"action": "SWAP_SHIFT", "score": 9.5}],
    )
    db_session.add(conflict)
    db_session.commit()

    queried_conflict = db_session.execute(
        select(RosterConflict).where(RosterConflict.code == "C01")
    ).scalar_one()
    assert queried_conflict.severity == ConflictSeverity.BLOCKING
    assert queried_conflict.brand_process is not None
    assert queried_conflict.brand_process.brand.code == "BC"
    assert queried_conflict.employee is not None
    assert queried_conflict.employee.code == "EMP-C1"
    assert len(queried_conflict.root_causes) == 2
    assert len(queried_conflict.suggestions) == 1
    assert queried_conflict.is_acknowledged is False

    # Acknowledge conflict
    queried_conflict.is_acknowledged = True
    queried_conflict.acknowledged_by_id = user.id
    queried_conflict.acknowledged_reason = "Manual override: temporary floor supervisor covers"
    db_session.commit()

    reloaded_conflict = db_session.execute(
        select(RosterConflict).where(RosterConflict.code == "C01")
    ).scalar_one()
    assert reloaded_conflict.is_acknowledged is True
    assert reloaded_conflict.acknowledged_by is not None
    assert reloaded_conflict.acknowledged_by.email == "ack.lead@example.test"
