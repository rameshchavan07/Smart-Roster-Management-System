"""Integration tests for Local Roster Repair API (Task T-516)."""

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
from app.models.core import (
    Assignment,
    AssignmentType,
    Brand,
    BrandProcess,
    CalendarType,
    Employee,
    Pod,
    Process,
)
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

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client, testing_session_local, ops_user, pod_user, emp_user

    Base.metadata.drop_all(engine)
    app.dependency_overrides.clear()


def test_roster_local_repair_dry_run_and_apply(
    test_setup: tuple[TestClient, sessionmaker[Session], User, User, User],
) -> None:
    """Test local repair: preview diff with apply=False, and apply changes with apply=True."""
    api_client, session_factory, ops_user, pod_user, emp_user = test_setup

    db: Session = session_factory()
    try:
        # 1. Setup Pod, Brand, Process, BrandProcess, Employees, Assignments
        pod = Pod(name="Repair Pod")
        db.add(pod)
        db.flush()

        proc = Process(name="Customer Support", code="CS")
        brand = Brand(name="Repair Brand", code="RPR", pod_id=pod.id)
        db.add_all([proc, brand])
        db.flush()

        bp = BrandProcess(
            brand_id=brand.id,
            process_id=proc.id,
            calendar_type=CalendarType.ALL_365,
            min_coverage_default=1,
        )
        db.add(bp)
        db.flush()

        emp1 = Employee(code="EMP-R1", full_name="Repair Alice", pod_id=pod.id, weekly_off_count=1)
        emp2 = Employee(code="EMP-R2", full_name="Repair Bob", pod_id=pod.id, weekly_off_count=1)
        db.add_all([emp1, emp2])
        db.flush()

        a1 = Assignment(
            employee_id=emp1.id,
            brand_process_id=bp.id,
            type=AssignmentType.PRIMARY,
        )
        a2 = Assignment(
            employee_id=emp2.id,
            brand_process_id=bp.id,
            type=AssignmentType.PRIMARY,
        )
        db.add_all([a1, a2])

        # 2. Setup Roster Period for Dec 2026 with a gap on Dec 5 (both off)
        period = RosterPeriod(
            month=dt.date(2026, 12, 1),
            version=1,
            status=RosterPeriodStatus.DRAFT,
            is_stale=False,
        )
        db.add(period)
        db.flush()

        dates = [dt.date(2026, 12, i) for i in range(1, 8)]
        for d in dates:
            st1 = (
                RosterEntryStatus.WEEKLY_OFF
                if d == dt.date(2026, 12, 5)
                else RosterEntryStatus.WORK
            )
            st2 = (
                RosterEntryStatus.WEEKLY_OFF
                if d == dt.date(2026, 12, 5)
                else RosterEntryStatus.WORK
            )
            db.add(
                RosterEntry(
                    roster_period_id=period.id,
                    employee_id=emp1.id,
                    date=d,
                    status=st1,
                    source=EntrySource.AUTO,
                )
            )
            db.add(
                RosterEntry(
                    roster_period_id=period.id,
                    employee_id=emp2.id,
                    date=d,
                    status=st2,
                    source=EntrySource.AUTO,
                )
            )

        # Add conflict for Dec 5
        conflict = RosterConflict(
            roster_period_id=period.id,
            code="E001",
            severity=ConflictSeverity.BLOCKING,
            brand_process_id=bp.id,
            date_from=dt.date(2026, 12, 5),
            date_to=dt.date(2026, 12, 5),
            root_causes=["NO_COVERAGE"],
            message="No employees scheduled on 2026-12-05",
        )
        db.add(conflict)
        db.commit()

        # 3. RBAC negative test: Employee cannot run repair (403)
        api_client.app.dependency_overrides[get_current_user] = lambda: emp_user
        res_emp = api_client.post(
            f"/api/v1/rosters/{period.id}/repair",
            json={"dates": ["2026-12-05"], "apply": False},
        )
        assert res_emp.status_code == 403

        # Switch to Pod Lead
        api_client.app.dependency_overrides[get_current_user] = lambda: pod_user

        # 4. Preview Local Repair (apply=False)
        res_preview = api_client.post(
            f"/api/v1/rosters/{period.id}/repair",
            json={
                "dates": ["2026-12-05"],
                "employee_ids": [str(emp1.id), str(emp2.id)],
                "apply": False,
                "use_fallback": True,
            },
        )
        assert res_preview.status_code == 200
        prev_data = res_preview.json()
        assert prev_data["applied"] is False
        assert prev_data["period"] is None

        # Database entries should remain untouched after dry-run
        db.expire_all()
        ent5 = db.scalars(
            select(RosterEntry).where(
                RosterEntry.roster_period_id == period.id,
                RosterEntry.date == dt.date(2026, 12, 5),
                RosterEntry.employee_id == emp1.id,
            )
        ).first()
        assert ent5 is not None
        assert ent5.status == RosterEntryStatus.WEEKLY_OFF

        # 5. Apply Local Repair (apply=True)
        api_client.app.dependency_overrides[get_current_user] = lambda: ops_user

        res_apply = api_client.post(
            f"/api/v1/rosters/{period.id}/repair",
            json={
                "conflict_id": str(conflict.id),
                "apply": True,
                "use_fallback": True,
            },
        )
        assert res_apply.status_code == 200
        apply_data = res_apply.json()
        assert apply_data["applied"] is True
        assert apply_data["period"] is not None

        # Verify audit logs
        db.expire_all()
        repair_audit = db.scalars(
            select(AuditLog).where(AuditLog.action == "ROSTER_LOCAL_REPAIR_APPLY")
        ).first()
        assert repair_audit is not None

    finally:
        db.close()
