"""Integration tests for Audit Log API (Task T-519)."""

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
from app.models.auth import AuditLog, User, UserRole


@pytest.fixture
def test_setup() -> Generator[
    tuple[TestClient, sessionmaker[Session], User, User, User], None, None
]:
    """Test client and session factory with role-switching capability."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    import app.models  # noqa: F401

    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(
        autocommit=False, autoflush=False, expire_on_commit=False, bind=engine
    )

    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    ops_user = User(
        id=uuid.uuid4(),
        email="ops.manager@example.com",
        password_hash="test_hash",
        role=UserRole.OPS_MANAGER,
        is_active=True,
    )
    pod_user = User(
        id=uuid.uuid4(),
        email="pod.lead@example.com",
        password_hash="test_hash",
        role=UserRole.POD_LEAD,
        is_active=True,
    )
    emp_user = User(
        id=uuid.uuid4(),
        email="employee@example.com",
        password_hash="test_hash",
        role=UserRole.EMPLOYEE,
        is_active=True,
    )

    current_test_user = ops_user

    def override_get_current_user() -> User:
        return current_test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    # Seed sample audit log entries
    db: Session = testing_session_local()
    db.add_all([ops_user, pod_user, emp_user])
    db.flush()

    log1 = AuditLog(
        id=uuid.uuid4(),
        user_id=ops_user.id,
        action="ROSTER_GENERATE",
        entity_type="RosterPeriod",
        entity_id="period-001",
        before=None,
        after={"version": 1, "month": "2026-12-01"},
        created_at=dt.datetime(2026, 12, 1, 10, 0, 0, tzinfo=dt.UTC),
    )
    log2 = AuditLog(
        id=uuid.uuid4(),
        user_id=ops_user.id,
        action="ROSTER_CELL_EDIT",
        entity_type="RosterEntry",
        entity_id="entry-101",
        before={"status": "WORK"},
        after={"status": "WEEKLY_OFF"},
        created_at=dt.datetime(2026, 12, 2, 11, 0, 0, tzinfo=dt.UTC),
    )
    log3 = AuditLog(
        id=uuid.uuid4(),
        user_id=pod_user.id,
        action="LEAVE_APPROVE",
        entity_type="Leave",
        entity_id="leave-501",
        before={"status": "PENDING"},
        after={"status": "APPROVED"},
        created_at=dt.datetime(2026, 12, 3, 12, 0, 0, tzinfo=dt.UTC),
    )
    db.add_all([log1, log2, log3])
    db.commit()
    db.close()

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client, testing_session_local, ops_user, pod_user, emp_user

    Base.metadata.drop_all(engine)
    app.dependency_overrides.clear()


def test_list_audit_logs_default(
    test_setup: tuple[TestClient, sessionmaker[Session], User, User, User],
) -> None:
    """Test retrieving all audit logs with default pagination."""
    client, _, ops_user, _, _ = test_setup

    client.app.dependency_overrides[get_current_user] = lambda: ops_user
    res = client.get("/api/v1/audit-logs")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    assert data["offset"] == 0
    assert data["limit"] == 50

    # Ordered descending by created_at
    assert data["items"][0]["action"] == "LEAVE_APPROVE"
    assert data["items"][0]["user_email"] == "pod.lead@example.com"
    assert data["items"][1]["action"] == "ROSTER_CELL_EDIT"
    assert data["items"][2]["action"] == "ROSTER_GENERATE"


def test_list_audit_logs_filters(
    test_setup: tuple[TestClient, sessionmaker[Session], User, User, User],
) -> None:
    """Test filtering audit logs by action, entity_type, entity_id, user_id, date range."""
    client, _, ops_user, pod_user, _ = test_setup
    client.app.dependency_overrides[get_current_user] = lambda: ops_user

    # Filter by action
    res_act = client.get("/api/v1/audit-logs?action=ROSTER_GENERATE")
    assert res_act.status_code == 200
    act_data = res_act.json()
    assert act_data["total"] == 1
    assert act_data["items"][0]["action"] == "ROSTER_GENERATE"
    assert act_data["items"][0]["entity_id"] == "period-001"

    # Filter by entity_type
    res_ent = client.get("/api/v1/audit-logs?entity_type=RosterEntry")
    assert res_ent.status_code == 200
    ent_data = res_ent.json()
    assert ent_data["total"] == 1
    assert ent_data["items"][0]["entity_type"] == "RosterEntry"

    # Filter by user_id
    res_user = client.get(f"/api/v1/audit-logs?user_id={pod_user.id}")
    assert res_user.status_code == 200
    user_data = res_user.json()
    assert user_data["total"] == 1
    assert user_data["items"][0]["action"] == "LEAVE_APPROVE"

    # Filter by date range
    res_date = client.get("/api/v1/audit-logs?date_from=2026-12-02&date_to=2026-12-02")
    assert res_date.status_code == 200
    date_data = res_date.json()
    assert date_data["total"] == 1
    assert date_data["items"][0]["action"] == "ROSTER_CELL_EDIT"


def test_list_audit_logs_pagination(
    test_setup: tuple[TestClient, sessionmaker[Session], User, User, User],
) -> None:
    """Test pagination offset and limit."""
    client, _, ops_user, _, _ = test_setup
    client.app.dependency_overrides[get_current_user] = lambda: ops_user

    res_page = client.get("/api/v1/audit-logs?offset=1&limit=1")
    assert res_page.status_code == 200
    page_data = res_page.json()
    assert page_data["total"] == 3
    assert len(page_data["items"]) == 1
    assert page_data["offset"] == 1
    assert page_data["limit"] == 1
    assert page_data["items"][0]["action"] == "ROSTER_CELL_EDIT"


def test_audit_logs_rbac_enforcement(
    test_setup: tuple[TestClient, sessionmaker[Session], User, User, User],
) -> None:
    """Test RBAC: Ops Manager and Pod Lead allowed (200), Employee rejected (403)."""
    client, _, ops_user, pod_user, emp_user = test_setup

    # Ops Manager: allowed
    client.app.dependency_overrides[get_current_user] = lambda: ops_user
    res_ops = client.get("/api/v1/audit-logs")
    assert res_ops.status_code == 200

    # Pod Lead: allowed
    client.app.dependency_overrides[get_current_user] = lambda: pod_user
    res_pod = client.get("/api/v1/audit-logs")
    assert res_pod.status_code == 200

    # Employee: forbidden (403)
    client.app.dependency_overrides[get_current_user] = lambda: emp_user
    res_emp = client.get("/api/v1/audit-logs")
    assert res_emp.status_code == 403
