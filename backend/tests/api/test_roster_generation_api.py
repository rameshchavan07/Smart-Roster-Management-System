"""Integration tests for Roster Generation and Lifecycle API endpoints.

Conforms to API_DOCUMENTATION.md §4, SCHEDULING_ENGINE.md §§6–9, and SECURITY.md §2.
Tests:
- Authentication & RBAC (Ops Manager only for generation, all authenticated for read)
- CP-SAT engine generation & DB persistence (RosterPeriod, RosterEntry, RosterConflict, AuditLog)
- Multiple versions per month (version increment)
- Fallback solver trigger (`use_fallback=True`)
- Version listing and metadata retrieval
"""

from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user, get_db
from app.db.base import Base
from app.main import create_app
from app.models.auth import AuditLog, User, UserRole
from app.models.core import Assignment, AssignmentType, Brand, BrandProcess, Employee, Pod, Process
from app.models.roster import RosterEntry, RosterPeriod, RosterPeriodStatus
from app.models.rules import WeeklyOffMode, WeeklyOffRule


@pytest.fixture
def test_setup() -> Generator[dict, None, None]:
    """In-memory SQLite database populated with base master data and users."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_factory()

    # 1. Users
    user_ops = User(
        id=uuid.uuid4(),
        email="ops@example.com",
        password_hash="test_hash",
        role=UserRole.OPS_MANAGER,
        is_active=True,
    )
    user_pod_lead = User(
        id=uuid.uuid4(),
        email="lead@example.com",
        password_hash="test_hash",
        role=UserRole.POD_LEAD,
        is_active=True,
    )
    user_emp = User(
        id=uuid.uuid4(),
        email="emp@example.com",
        password_hash="test_hash",
        role=UserRole.EMPLOYEE,
        is_active=True,
    )
    db.add_all([user_ops, user_pod_lead, user_emp])
    db.flush()

    # 2. Master Data: Pod, Brand, Process, BrandProcess
    pod = Pod(name="Apollo Pod")
    db.add(pod)
    db.flush()

    brand = Brand(name="Starlight", code="STL", pod_id=pod.id)
    proc = Process(name="Customer Support", code="CS")
    db.add_all([brand, proc])
    db.flush()

    bp = BrandProcess(
        brand_id=brand.id,
        process_id=proc.id,
        min_coverage_default=1,
    )
    db.add(bp)
    db.flush()

    # 3. Employees, Assignments, and Weekly Off Rules
    employees = []
    for i in range(1, 4):
        emp = Employee(
            full_name=f"Agent {i}",
            code=f"EMP-00{i}",
            email=f"agent{i}@example.com",
            pod_id=pod.id,
        )
        db.add(emp)
        db.flush()
        employees.append(emp)

        asgn = Assignment(
            employee_id=emp.id,
            brand_process_id=bp.id,
            type=AssignmentType.PRIMARY,
        )
        db.add(asgn)

        # Weekly Off Rule (Fixed Sunday = 6)
        wor = WeeklyOffRule(
            employee_id=emp.id,
            mode=WeeklyOffMode.FIXED_MANDATORY,
            weekdays=[6],
        )
        db.add(wor)

    db.commit()

    context = {
        "engine": engine,
        "session_factory": session_factory,
        "users": {
            "ops": user_ops,
            "lead": user_pod_lead,
            "emp": user_emp,
        },
        "employees": employees,
        "brand_process": bp,
    }

    yield context

    Base.metadata.drop_all(engine)


def create_client(context: dict, current_user: User | None = None) -> tuple[TestClient, Session]:
    """Construct a TestClient with overridden DB and optional current user."""
    app = create_app()
    session_factory = context["session_factory"]
    db = session_factory()

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    if current_user:
        app.dependency_overrides[get_current_user] = lambda: current_user

    client = TestClient(app, raise_server_exceptions=False)
    return client, db


def test_roster_generation_permissions(test_setup: dict) -> None:
    """Test RBAC enforcement on POST /api/v1/rosters."""
    # 1. Unauthenticated request fails with 401
    client_unauth, db1 = create_client(test_setup, current_user=None)
    res_unauth = client_unauth.post("/api/v1/rosters", json={"month": "2026-12"})
    assert res_unauth.status_code == 401
    assert res_unauth.json()["error"]["code"] == "UNAUTHENTICATED"
    db1.close()

    # 2. Regular employee fails with 403
    client_emp, db2 = create_client(test_setup, current_user=test_setup["users"]["emp"])
    res_emp = client_emp.post("/api/v1/rosters", json={"month": "2026-12"})
    assert res_emp.status_code == 403
    assert res_emp.json()["error"]["code"] == "FORBIDDEN"
    db2.close()

    # 3. Pod Lead fails with 403 (generation is Ops Manager only)
    client_lead, db3 = create_client(test_setup, current_user=test_setup["users"]["lead"])
    res_lead = client_lead.post("/api/v1/rosters", json={"month": "2026-12"})
    assert res_lead.status_code == 403
    assert res_lead.json()["error"]["code"] == "FORBIDDEN"
    db3.close()


def test_roster_generation_cpsat_and_persistence(test_setup: dict) -> None:
    """Test generating a roster via CP-SAT and verify DB persistence of cells and audit log."""
    client_ops, db = create_client(test_setup, current_user=test_setup["users"]["ops"])

    payload = {
        "month": "2026-12",
        "options": {
            "seed": 42,
            "time_limit_s": 10,
        },
    }
    response = client_ops.post("/api/v1/rosters", json=payload)
    assert response.status_code == 201

    data = response.json()
    period_id = uuid.UUID(data["id"])
    assert data["month"] == "2026-12-01"
    assert data["version"] == 1
    assert data["status"] == "DRAFT"
    assert data["solver_status"] in ["OPTIMAL", "FEASIBLE"]
    assert "summary" in data
    assert "coverage_pct" in data["summary"]

    # Verify DB persistence
    period = db.get(RosterPeriod, period_id)
    assert period is not None
    assert period.status == RosterPeriodStatus.DRAFT
    assert period.version == 1
    assert period.created_by_id == test_setup["users"]["ops"].id

    # Check entries count: 3 employees * 31 days in Dec = 93 entries
    entries = db.scalars(select(RosterEntry).where(RosterEntry.roster_period_id == period_id)).all()
    assert len(entries) == 3 * 31

    # Check AuditLog
    audit = db.scalars(
        select(AuditLog).where(
            AuditLog.entity_type == "ROSTER_PERIOD",
            AuditLog.entity_id == str(period_id),
        )
    ).first()
    assert audit is not None
    assert audit.action == "CREATE_ROSTER"
    assert audit.user_id == test_setup["users"]["ops"].id

    db.close()


def test_roster_versioning_and_listing(test_setup: dict) -> None:
    """Test creating multiple versions for the same month and retrieving them via GET endpoints."""
    client_ops, db = create_client(test_setup, current_user=test_setup["users"]["ops"])

    # 1. Generate version 1
    res1 = client_ops.post("/api/v1/rosters", json={"month": "2026-12"})
    assert res1.status_code == 201
    v1_id = res1.json()["id"]
    assert res1.json()["version"] == 1

    # 2. Generate version 2 for the same month
    res2 = client_ops.post("/api/v1/rosters", json={"month": "2026-12"})
    assert res2.status_code == 201
    v2_id = res2.json()["id"]
    assert res2.json()["version"] == 2
    assert v1_id != v2_id

    # 3. List rosters for 2026-12
    list_res = client_ops.get("/api/v1/rosters?month=2026-12")
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) == 2
    # Verify ordered newest version first
    assert items[0]["version"] == 2
    assert items[1]["version"] == 1
    assert items[0]["entries_count"] == 3 * 31

    # 4. Get metadata for single period
    get_res = client_ops.get(f"/api/v1/rosters/{v1_id}")
    assert get_res.status_code == 200
    v1_meta = get_res.json()
    assert v1_meta["id"] == v1_id
    assert v1_meta["version"] == 1
    assert v1_meta["entries_count"] == 3 * 31

    # 5. Non-existent period returns 404
    non_existent = uuid.uuid4()
    not_found_res = client_ops.get(f"/api/v1/rosters/{non_existent}")
    assert not_found_res.status_code == 404
    assert not_found_res.json()["error"]["code"] == "NOT_FOUND"

    db.close()


def test_roster_generation_fallback(test_setup: dict) -> None:
    """Test generating a roster explicitly triggering greedy fallback."""
    client_ops, db = create_client(test_setup, current_user=test_setup["users"]["ops"])

    payload = {
        "month": "2026-12",
        "options": {
            "use_fallback": True,
            "seed": 99,
        },
    }
    response = client_ops.post("/api/v1/rosters", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["solver_status"] == "FALLBACK"
    assert data["version"] == 1

    period = db.get(RosterPeriod, uuid.UUID(data["id"]))
    assert period is not None
    assert period.solver_status == "FALLBACK"

    db.close()
