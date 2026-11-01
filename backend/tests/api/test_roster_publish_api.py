"""Integration tests for Roster publish, conflict acknowledgment, and cloning (Task T-515)."""

import datetime as dt
import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.auth import AuditLog, User, UserRole
from app.models.core import Employee, Pod
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
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    ops_user = User(
        id=uuid.uuid4(),
        email="ops.lead@example.com",
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
        email="staff@example.com",
        password_hash="test_hash",
        role=UserRole.EMPLOYEE,
        is_active=True,
    )

    current_test_user = ops_user

    def override_get_current_user() -> User:
        return current_test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client, testing_session_local, ops_user, pod_user, emp_user

    Base.metadata.drop_all(engine)
    app.dependency_overrides.clear()


def test_publish_gating_and_acknowledgment_flow(
    test_setup: tuple[TestClient, sessionmaker[Session], User, User, User],
) -> None:
    """Test publish gating on unacknowledged BLOCKING conflicts and acknowledgment workflow (Scenario S5)."""
    api_client, session_factory, ops_user, pod_user, emp_user = test_setup

    db: Session = session_factory()
    try:
        pod = Pod(name="Orion Pod")
        db.add(pod)
        db.flush()

        emp1 = Employee(code="EMP-023", full_name="Aditi Rao", pod_id=pod.id)
        emp2 = Employee(code="EMP-024", full_name="Dev Malhotra", pod_id=pod.id)
        db.add_all([emp1, emp2])
        db.flush()

        period = RosterPeriod(
            month=dt.date(2026, 12, 1),
            version=1,
            status=RosterPeriodStatus.DRAFT,
            is_stale=False,
        )
        db.add(period)
        db.flush()

        # Add a BLOCKING conflict (Scenario S5: Orion CS Friday mandatory off leaves zero coverage)
        conflict = RosterConflict(
            roster_period_id=period.id,
            code="E001",
            severity=ConflictSeverity.BLOCKING,
            date_from=dt.date(2026, 12, 4),
            date_to=dt.date(2026, 12, 4),
            root_causes=["NO_COVERAGE", "FIXED_MANDATORY_OFF"],
            message="No active employees scheduled for Orion CS on 2026-12-04",
            is_acknowledged=False,
        )
        db.add(conflict)

        # Add a WARNING conflict (non-blocking)
        warn_conflict = RosterConflict(
            roster_period_id=period.id,
            code="W001",
            severity=ConflictSeverity.WARNING,
            date_from=dt.date(2026, 12, 7),
            date_to=dt.date(2026, 12, 7),
            root_causes=["PREFERENCE_UNHONOURED"],
            message="Dev Malhotra requested Sunday off",
            is_acknowledged=False,
        )
        db.add(warn_conflict)
        db.commit()

        # 1. Attempt publish with unacknowledged BLOCKING conflict -> 422 ROSTER_BLOCKED
        pub_blocked = api_client.post(f"/api/v1/rosters/{period.id}/publish")
        assert pub_blocked.status_code == 422
        blocked_err = pub_blocked.json()["error"]
        assert blocked_err["code"] == "ROSTER_BLOCKED"
        assert len(blocked_err["details"]) == 1
        assert blocked_err["details"][0]["conflict_id"] == str(conflict.id)

        # 2. RBAC negative test: Pod Lead cannot publish (403)
        api_client.app.dependency_overrides[get_current_user] = lambda: pod_user
        pod_pub = api_client.post(f"/api/v1/rosters/{period.id}/publish")
        assert pod_pub.status_code == 403

        # 3. RBAC negative test: Pod Lead cannot acknowledge (403)
        pod_ack = api_client.post(
            f"/api/v1/rosters/{period.id}/acknowledge",
            json={"conflict_id": str(conflict.id), "reason": "Authorized coverage waiver"},
        )
        assert pod_ack.status_code == 403

        # Switch back to Ops Manager
        api_client.app.dependency_overrides[get_current_user] = lambda: ops_user

        # 4. Acknowledge with short reason fails validation (min_length=5)
        short_ack = api_client.post(
            f"/api/v1/rosters/{period.id}/acknowledge",
            json={"conflict_id": str(conflict.id), "reason": "No"},
        )
        assert short_ack.status_code == 422

        # 5. Acknowledge the BLOCKING conflict with valid reason
        ack_res = api_client.post(
            f"/api/v1/rosters/{period.id}/acknowledge",
            json={
                "conflict_id": str(conflict.id),
                "reason": "Solo shift covered on-call by regional standby team",
            },
        )
        assert ack_res.status_code == 200
        ack_data = ack_res.json()
        assert ack_data["is_acknowledged"] is True
        assert (
            ack_data["acknowledged_reason"] == "Solo shift covered on-call by regional standby team"
        )

        # Check AuditLog for conflict acknowledgment
        db.expire_all()
        ack_audit = db.scalars(
            select(AuditLog).where(AuditLog.action == "ROSTER_CONFLICT_ACKNOWLEDGE")
        ).first()
        assert ack_audit is not None
        assert ack_audit.entity_id == str(conflict.id)

        # 6. Now publish succeeds (warning conflict remains unacknowledged, but does not block)
        pub_ok = api_client.post(f"/api/v1/rosters/{period.id}/publish")
        assert pub_ok.status_code == 200
        pub_data = pub_ok.json()
        assert pub_data["status"] == "PUBLISHED"
        assert pub_data["published_at"] is not None
        assert pub_data["is_stale"] is False

        # 7. Attempting to publish again returns 409 CONFLICT
        pub_repeat = api_client.post(f"/api/v1/rosters/{period.id}/publish")
        assert pub_repeat.status_code == 409

    finally:
        db.close()


def test_roster_clone_and_supersede_workflow(
    test_setup: tuple[TestClient, sessionmaker[Session], User, User, User],
) -> None:
    """Test cloning a roster into draft v2, and publishing v2 archiving superseded v1."""
    api_client, session_factory, ops_user, pod_user, emp_user = test_setup

    db: Session = session_factory()
    try:
        pod = Pod(name="Apex Pod")
        db.add(pod)
        db.flush()

        emp = Employee(code="EMP-032", full_name="Farhan Ali", pod_id=pod.id)
        db.add(emp)
        db.flush()

        # 1. Create published roster v1 with 1 cell
        period_v1 = RosterPeriod(
            month=dt.date(2026, 12, 1),
            version=1,
            status=RosterPeriodStatus.PUBLISHED,
            solver_status="OPTIMAL",
            is_stale=False,
            published_at=dt.datetime.now(dt.UTC),
        )
        db.add(period_v1)
        db.flush()

        entry_v1 = RosterEntry(
            roster_period_id=period_v1.id,
            employee_id=emp.id,
            date=dt.date(2026, 12, 1),
            status=RosterEntryStatus.WORK,
            source=EntrySource.AUTO,
        )
        db.add(entry_v1)
        db.commit()

        # 2. Pod lead clones published v1 into draft v2
        api_client.app.dependency_overrides[get_current_user] = lambda: pod_user

        clone_res = api_client.post(
            f"/api/v1/rosters/{period_v1.id}/clone",
            json={"note": "Alternate branch exploring rotating shifts"},
        )
        assert clone_res.status_code == 201
        v2_data = clone_res.json()
        assert v2_data["version"] == 2
        assert v2_data["status"] == "DRAFT"
        assert v2_data["month"] == "2026-12-01"
        assert v2_data["entries_count"] == 1
        v2_id = uuid.UUID(v2_data["id"])

        # Verify AuditLog for clone
        db.expire_all()
        clone_audit = db.scalars(select(AuditLog).where(AuditLog.action == "ROSTER_CLONE")).first()
        assert clone_audit is not None
        assert clone_audit.after["version"] == 2

        # 3. Publish v2 as Ops Manager
        api_client.app.dependency_overrides[get_current_user] = lambda: ops_user

        pub_v2 = api_client.post(f"/api/v1/rosters/{v2_id}/publish")
        assert pub_v2.status_code == 200
        assert pub_v2.json()["status"] == "PUBLISHED"

        # 4. Verify v1 was automatically archived as superseded
        db.expire_all()
        reloaded_v1 = db.get(RosterPeriod, period_v1.id)
        assert reloaded_v1 is not None
        assert reloaded_v1.status == RosterPeriodStatus.ARCHIVED

        # Verify superseded audit log
        supersede_audit = db.scalars(
            select(AuditLog).where(AuditLog.action == "ROSTER_ARCHIVE_SUPERSEDED")
        ).first()
        assert supersede_audit is not None
        assert supersede_audit.entity_id == str(period_v1.id)

    finally:
        db.close()
