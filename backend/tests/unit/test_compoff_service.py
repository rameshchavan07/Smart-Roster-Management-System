"""Unit tests for CompOffService and holiday work accrual (Task T-514)."""

import datetime as dt

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.errors import ConflictError
from app.db.base import Base
from app.models.auth import AuditLog
from app.models.core import Employee, Pod
from app.models.roster import (
    EntrySource,
    RosterEntry,
    RosterEntryStatus,
    RosterPeriod,
    RosterPeriodStatus,
)
from app.models.rules import CompOffKind, Leave, LeaveStatus, LeaveType
from app.schemas.rules import CompOffLedgerCreate, CompOffRedeemRequest
from app.services.compoff import CompOffService


@pytest.fixture
def db_session() -> Session:
    """Create a fresh in-memory SQLite database session for unit testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    import app.models  # noqa: F401 - Register all models with Base.metadata

    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_compoff_balance_calculation(db_session: Session) -> None:
    """Test get_balance accurately computes earned, redeemed, and available comp-offs."""
    service = CompOffService(db_session)
    pod = Pod(name="Core Pod")
    db_session.add(pod)
    db_session.flush()

    emp = Employee(code="EMP-101", full_name="Alice Smith", pod_id=pod.id)
    db_session.add(emp)
    db_session.flush()

    # Initial balance is zero
    bal = service.get_balance(emp.id)
    assert bal.earned == 0
    assert bal.redeemed == 0
    assert bal.available == 0

    # Add 2 earned credits
    service.create_entry(
        CompOffLedgerCreate(
            employee_id=emp.id,
            entry_date=dt.date(2026, 12, 25),
            kind=CompOffKind.EARNED,
            note="Christmas holiday work",
        )
    )
    service.create_entry(
        CompOffLedgerCreate(
            employee_id=emp.id,
            entry_date=dt.date(2027, 1, 1),
            kind=CompOffKind.EARNED,
            note="New Year holiday work",
        )
    )
    db_session.flush()

    bal = service.get_balance(emp.id)
    assert bal.earned == 2
    assert bal.redeemed == 0
    assert bal.available == 2

    # Bulk balances
    emp2 = Employee(code="EMP-102", full_name="Bob Jones", pod_id=pod.id)
    db_session.add(emp2)
    db_session.flush()

    bulk_map = service.get_balances_for_employees([emp.id, emp2.id])
    assert bulk_map[str(emp.id)] == 2
    assert bulk_map[str(emp2.id)] == 0


def test_compoff_redemption_flow(db_session: Session) -> None:
    """Test redeeming a comp-off credit generates leave, updates ledger, and marks roster stale."""
    service = CompOffService(db_session)
    pod = Pod(name="Operations Pod")
    db_session.add(pod)
    db_session.flush()

    emp = Employee(code="EMP-201", full_name="Carol White", pod_id=pod.id)
    db_session.add(emp)
    db_session.flush()

    # Create draft roster for December 2026
    period = RosterPeriod(
        month=dt.date(2026, 12, 1),
        version=1,
        status=RosterPeriodStatus.DRAFT,
        is_stale=False,
    )
    db_session.add(period)
    db_session.flush()

    # Redeem with 0 balance should fail
    with pytest.raises(ConflictError, match="No available comp-off balance"):
        service.redeem_compoff(
            CompOffRedeemRequest(
                employee_id=emp.id,
                date=dt.date(2026, 12, 15),
            )
        )

    # Earn 1 credit
    service.create_entry(
        CompOffLedgerCreate(
            employee_id=emp.id,
            entry_date=dt.date(2026, 11, 26),
            kind=CompOffKind.EARNED,
        )
    )
    db_session.flush()

    # Redeem credit for 2026-12-15
    redeemed = service.redeem_compoff(
        CompOffRedeemRequest(
            employee_id=emp.id,
            date=dt.date(2026, 12, 15),
            note="Pre-approved comp off",
        )
    )
    db_session.flush()

    assert redeemed.kind == CompOffKind.REDEEMED
    assert redeemed.entry_date == dt.date(2026, 12, 15)

    # Balance check: 1 earned, 1 redeemed, 0 available
    bal = service.get_balance(emp.id)
    assert bal.earned == 1
    assert bal.redeemed == 1
    assert bal.available == 0

    # Verify corresponding Leave record was generated
    leave = db_session.scalars(
        select(Leave).where(
            Leave.employee_id == emp.id,
            Leave.start_date == dt.date(2026, 12, 15),
        )
    ).first()
    assert leave is not None
    assert leave.type == LeaveType.COMP_OFF
    assert leave.status == LeaveStatus.APPROVED

    # Verify December roster is marked stale
    db_session.refresh(period)
    assert period.is_stale is True

    # Audit log check
    audit = db_session.scalars(select(AuditLog).where(AuditLog.action == "compoff.redeem")).first()
    assert audit is not None
    assert audit.entity_type == "CompOffLedger"


def test_accrue_holiday_work_credits(db_session: Session) -> None:
    """Test accrual of comp-off credits from HOLIDAY_WORK cells in a roster period."""
    service = CompOffService(db_session)
    pod = Pod(name="CS Pod")
    db_session.add(pod)
    db_session.flush()

    emp1 = Employee(code="EMP-301", full_name="David Miller", pod_id=pod.id)
    emp2 = Employee(code="EMP-302", full_name="Emma Watson", pod_id=pod.id)
    db_session.add_all([emp1, emp2])
    db_session.flush()

    period = RosterPeriod(
        month=dt.date(2026, 12, 1),
        version=1,
        status=RosterPeriodStatus.PUBLISHED,
    )
    db_session.add(period)
    db_session.flush()

    # Entry 1: emp1 worked holiday on Christmas Dec 25
    e1 = RosterEntry(
        roster_period_id=period.id,
        employee_id=emp1.id,
        date=dt.date(2026, 12, 25),
        status=RosterEntryStatus.HOLIDAY_WORK,
        source=EntrySource.AUTO,
    )
    # Entry 2: emp2 normal WORK on Dec 25 (non-holiday or normal shift)
    e2 = RosterEntry(
        roster_period_id=period.id,
        employee_id=emp2.id,
        date=dt.date(2026, 12, 25),
        status=RosterEntryStatus.WORK,
        source=EntrySource.AUTO,
    )
    # Entry 3: emp2 worked holiday on Dec 26
    e3 = RosterEntry(
        roster_period_id=period.id,
        employee_id=emp2.id,
        date=dt.date(2026, 12, 26),
        status=RosterEntryStatus.HOLIDAY_WORK,
        source=EntrySource.AUTO,
    )
    db_session.add_all([e1, e2, e3])
    db_session.flush()

    # Initial balances: 0
    assert service.get_balance(emp1.id).available == 0
    assert service.get_balance(emp2.id).available == 0

    # Run accrual
    created = service.accrue_holiday_work_credits(period.id)
    db_session.flush()

    assert len(created) == 2
    emp_ids_credited = {c.employee_id for c in created}
    assert emp_ids_credited == {emp1.id, emp2.id}

    # Balances updated
    assert service.get_balance(emp1.id).available == 1
    assert service.get_balance(emp2.id).available == 1

    # Idempotency: running accrual again produces 0 new entries
    second_run = service.accrue_holiday_work_credits(period.id)
    assert len(second_run) == 0

    # Balances stay 1
    assert service.get_balance(emp1.id).available == 1
    assert service.get_balance(emp2.id).available == 1
