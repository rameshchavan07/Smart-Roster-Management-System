"""Integration tests for Comp-off endpoints (Task T-514)."""

import datetime as dt
import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.auth import User, UserRole
from app.models.roster import (
    EntrySource,
    RosterEntry,
    RosterEntryStatus,
    RosterPeriod,
    RosterPeriodStatus,
)


@pytest.fixture
def api_client() -> Generator[TestClient, None, None]:
    """Test client with test database session and admin user dependency override."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    import app.models  # noqa: F401

    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    admin_user = User(
        id=uuid.uuid4(),
        email="ops.manager@example.com",
        password_hash="test_hash",
        role=UserRole.OPS_MANAGER,
        is_active=True,
    )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: admin_user

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client

    Base.metadata.drop_all(engine)
    app.dependency_overrides.clear()


def test_employee_compoff_balance_endpoint(api_client: TestClient) -> None:
    """Test GET /api/v1/employees/{id}/comp-off-balance per docs/API_DOCUMENTATION.md §4."""
    pod_id = api_client.post("/api/v1/pods", json={"name": "Delta Pod"}).json()["id"]
    emp_id = api_client.post(
        "/api/v1/employees",
        json={"code": "EMP-801", "full_name": "Daniel Craig", "pod_id": pod_id},
    ).json()["id"]

    # Initial balance check via /employees/{id}/comp-off-balance
    bal_res = api_client.get(f"/api/v1/employees/{emp_id}/comp-off-balance")
    assert bal_res.status_code == 200
    assert bal_res.json() == {
        "employee_id": emp_id,
        "earned": 0,
        "redeemed": 0,
        "available": 0,
    }

    # Credit 1 comp-off via manual credit
    credit_res = api_client.post(
        "/api/v1/comp-offs",
        json={
            "employee_id": emp_id,
            "entry_date": "2026-12-25",
            "kind": "EARNED",
            "note": "Holiday work on Christmas",
        },
    )
    assert credit_res.status_code == 201

    # Check updated balance
    bal_res2 = api_client.get(f"/api/v1/employees/{emp_id}/comp-off-balance")
    assert bal_res2.status_code == 200
    assert bal_res2.json() == {
        "employee_id": emp_id,
        "earned": 1,
        "redeemed": 0,
        "available": 1,
    }


def test_roster_accrue_holiday_work_api(api_client: TestClient) -> None:
    """Test POST /api/v1/rosters/{id}/accrue-compoffs and POST /api/v1/comp-offs/accrue-from-roster/{id}."""
    pod_id = api_client.post("/api/v1/pods", json={"name": "Echo Pod"}).json()["id"]
    emp1_id = api_client.post(
        "/api/v1/employees",
        json={"code": "EMP-802", "full_name": "Eva Green", "pod_id": pod_id},
    ).json()["id"]
    emp2_id = api_client.post(
        "/api/v1/employees",
        json={"code": "EMP-803", "full_name": "Frank Castle", "pod_id": pod_id},
    ).json()["id"]

    # Directly create a roster period with HOLIDAY_WORK entries in DB using test engine
    from app.db.session import get_db

    db_gen = api_client.app.dependency_overrides[get_db]()
    db: Session = next(db_gen)

    period = RosterPeriod(
        month=dt.date(2026, 12, 1),
        version=1,
        status=RosterPeriodStatus.DRAFT,
    )
    db.add(period)
    db.flush()

    e1 = RosterEntry(
        roster_period_id=period.id,
        employee_id=uuid.UUID(emp1_id),
        date=dt.date(2026, 12, 25),
        status=RosterEntryStatus.HOLIDAY_WORK,
        source=EntrySource.AUTO,
    )
    e2 = RosterEntry(
        roster_period_id=period.id,
        employee_id=uuid.UUID(emp2_id),
        date=dt.date(2026, 12, 25),
        status=RosterEntryStatus.HOLIDAY_WORK,
        source=EntrySource.AUTO,
    )
    db.add_all([e1, e2])
    db.commit()

    # Call POST /api/v1/rosters/{period_id}/accrue-compoffs
    accrue_res = api_client.post(f"/api/v1/rosters/{period.id}/accrue-compoffs")
    assert accrue_res.status_code == 201
    accrued = accrue_res.json()
    assert len(accrued) == 2

    # Balances for emp1 and emp2 should now be 1
    bal1 = api_client.get(f"/api/v1/employees/{emp1_id}/comp-off-balance").json()
    bal2 = api_client.get(f"/api/v1/employees/{emp2_id}/comp-off-balance").json()
    assert bal1["available"] == 1
    assert bal2["available"] == 1

    # Second call (idempotent)
    accrue_again = api_client.post(f"/api/v1/comp-offs/accrue-from-roster/{period.id}")
    assert accrue_again.status_code == 201
    assert len(accrue_again.json()) == 0
