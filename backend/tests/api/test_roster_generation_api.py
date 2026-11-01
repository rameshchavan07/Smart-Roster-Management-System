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

import datetime as dt
import time
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
from app.seed import seed_database


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


def test_roster_grid_views(test_setup: dict) -> None:
    """Test all 5 view modes (company, pod, brand, process, employee) on /grid."""
    client_ops, db = create_client(test_setup, current_user=test_setup["users"]["ops"])

    # Generate a roster
    gen_res = client_ops.post("/api/v1/rosters", json={"month": "2026-12"})
    assert gen_res.status_code == 201
    period_id = gen_res.json()["id"]

    # 1. Company view (all active employees)
    grid_company = client_ops.get(f"/api/v1/rosters/{period_id}/grid?view=company")
    assert grid_company.status_code == 200
    comp_data = grid_company.json()
    assert comp_data["view"] == "company"
    assert comp_data["start_date"] == "2026-12-01"
    assert comp_data["end_date"] == "2026-12-31"
    assert len(comp_data["rows"]) == 3
    # Check cells inside row
    first_row = comp_data["rows"][0]
    assert len(first_row["cells"]) == 31
    assert "2026-12-01" in first_row["cells"]
    assert first_row["cells"]["2026-12-01"]["status"] in [
        "WORK",
        "WEEKLY_OFF",
        "HOLIDAY_WORK",
        "HOLIDAY_OFF",
    ]

    # 2. Pod view (scoped by pod_id)
    pod = db.scalars(select(Pod)).first()
    assert pod is not None
    grid_pod = client_ops.get(f"/api/v1/rosters/{period_id}/grid?view=pod&ref_id={pod.id}")
    assert grid_pod.status_code == 200
    assert len(grid_pod.json()["rows"]) == 3

    # 3. Brand view (scoped by brand_id)
    brand = db.scalars(select(Brand)).first()
    assert brand is not None
    grid_brand = client_ops.get(f"/api/v1/rosters/{period_id}/grid?view=brand&ref_id={brand.id}")
    assert grid_brand.status_code == 200
    assert len(grid_brand.json()["rows"]) == 3

    # 4. Process view (scoped by process_id)
    proc = db.scalars(select(Process)).first()
    assert proc is not None
    grid_proc = client_ops.get(f"/api/v1/rosters/{period_id}/grid?view=process&ref_id={proc.id}")
    assert grid_proc.status_code == 200
    assert len(grid_proc.json()["rows"]) == 3

    # 5. Employee view (scoped to 1 employee)
    emp = test_setup["employees"][0]
    grid_emp = client_ops.get(f"/api/v1/rosters/{period_id}/grid?view=employee&ref_id={emp.id}")
    assert grid_emp.status_code == 200
    assert len(grid_emp.json()["rows"]) == 1
    assert grid_emp.json()["rows"][0]["employee_id"] == str(emp.id)

    # 6. Invalid view mode returns 422
    invalid_view = client_ops.get(f"/api/v1/rosters/{period_id}/grid?view=invalid_mode")
    assert invalid_view.status_code == 422
    assert invalid_view.json()["error"]["code"] == "VALIDATION_ERROR"

    db.close()


def test_roster_coverage_endpoint(test_setup: dict) -> None:
    """Test /coverage endpoint across dates and with brand-process filter."""
    client_ops, db = create_client(test_setup, current_user=test_setup["users"]["ops"])

    # Generate a roster
    gen_res = client_ops.post("/api/v1/rosters", json={"month": "2026-12"})
    period_id = gen_res.json()["id"]

    # 1. Full coverage for December (31 days * 1 brand-process = 31 cells)
    cov_res = client_ops.get(f"/api/v1/rosters/{period_id}/coverage")
    assert cov_res.status_code == 200
    cells = cov_res.json()
    assert len(cells) == 31
    sample = cells[0]
    assert sample["date"] == "2026-12-01"
    assert "required" in sample
    assert "actual" in sample
    assert "shortfall" in sample
    assert sample["brand_name"] == "Starlight"
    assert sample["process_name"] == "Customer Support"

    # 2. Date range filter
    week_res = client_ops.get(
        f"/api/v1/rosters/{period_id}/coverage?date_from=2026-12-01&date_to=2026-12-07"
    )
    assert week_res.status_code == 200
    assert len(week_res.json()) == 7

    db.close()


def test_roster_day_view_endpoint(test_setup: dict) -> None:
    """Test /day endpoint returning staffing breakdown per brand-process on a single date."""
    client_ops, db = create_client(test_setup, current_user=test_setup["users"]["ops"])

    gen_res = client_ops.post("/api/v1/rosters", json={"month": "2026-12"})
    period_id = gen_res.json()["id"]

    day_res = client_ops.get(f"/api/v1/rosters/{period_id}/day?date=2026-12-15")
    assert day_res.status_code == 200
    data = day_res.json()
    assert data["date"] == "2026-12-15"
    assert len(data["groups"]) == 1

    group = data["groups"][0]
    assert group["brand_name"] == "Starlight"
    assert group["process_name"] == "Customer Support"
    assert group["actual"] == len(group["working_employees"])
    assert len(group["working_employees"]) + len(group["off_employees"]) == 3

    db.close()


def test_roster_conflicts_endpoint(test_setup: dict) -> None:
    """Test /conflicts endpoint with severity and date filtering."""
    client_ops, db = create_client(test_setup, current_user=test_setup["users"]["ops"])

    gen_res = client_ops.post("/api/v1/rosters", json={"month": "2026-12"})
    period_id = gen_res.json()["id"]

    # 1. Fetch all conflicts
    all_conflicts = client_ops.get(f"/api/v1/rosters/{period_id}/conflicts")
    assert all_conflicts.status_code == 200
    assert isinstance(all_conflicts.json(), list)

    # 2. Filter by severity
    blocking = client_ops.get(f"/api/v1/rosters/{period_id}/conflicts?severity=BLOCKING")
    assert blocking.status_code == 200
    for c in blocking.json():
        assert c["severity"] == "BLOCKING"

    # 3. Filter by non-existent employee
    random_emp = uuid.uuid4()
    empty_res = client_ops.get(f"/api/v1/rosters/{period_id}/conflicts?employee_id={random_emp}")
    assert empty_res.status_code == 200
    assert len(empty_res.json()) == 0

    db.close()


def test_roster_read_endpoints_unauth_and_not_found(test_setup: dict) -> None:
    """Test 401 unauthenticated and 404 not found on read endpoints."""
    # 1. Unauthenticated requests fail with 401
    client_unauth, db1 = create_client(test_setup, current_user=None)
    fake_id = uuid.uuid4()
    assert client_unauth.get(f"/api/v1/rosters/{fake_id}/grid").status_code == 401
    assert client_unauth.get(f"/api/v1/rosters/{fake_id}/coverage").status_code == 401
    assert client_unauth.get(f"/api/v1/rosters/{fake_id}/day?date=2026-12-01").status_code == 401
    assert client_unauth.get(f"/api/v1/rosters/{fake_id}/conflicts").status_code == 401
    db1.close()

    # 2. Authenticated user with non-existent period_id fails with 404
    client_ops, db2 = create_client(test_setup, current_user=test_setup["users"]["ops"])
    assert client_ops.get(f"/api/v1/rosters/{fake_id}/grid").status_code == 404
    assert client_ops.get(f"/api/v1/rosters/{fake_id}/coverage").status_code == 404
    assert client_ops.get(f"/api/v1/rosters/{fake_id}/day?date=2026-12-01").status_code == 404
    assert client_ops.get(f"/api/v1/rosters/{fake_id}/conflicts").status_code == 404
    db2.close()


def test_seeded_december_2026_full_lifecycle_and_timings() -> None:
    """Generate December 2026 from full seed dataset (36 employees) and verify all 5 grid views."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_factory()

    # Seed scale 1 (36 employees, 25 brands, 6 pods, holidays, leaves)
    seed_database(db, scale=1, clean=False)

    ops_user = db.scalars(select(User).where(User.role == UserRole.OPS_MANAGER)).first()
    assert ops_user is not None

    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: ops_user

    with TestClient(app, raise_server_exceptions=False) as client:
        start_t = time.perf_counter()
        gen_res = client.post(
            "/api/v1/rosters",
            json={
                "month": "2026-12",
                "options": {
                    "seed": 42,
                    "time_limit_s": 15,
                },
            },
        )
        elapsed_gen = time.perf_counter() - start_t
        assert gen_res.status_code == 201
        period_data = gen_res.json()
        period_id = period_data["id"]

        print(
            f"\n[TIMING] December 2026 (36 emps) generation time: {elapsed_gen:.2f}s, solver_status={period_data['solver_status']}"
        )
        assert period_data["month"] == "2026-12-01"
        assert period_data["status"] == "DRAFT"
        assert period_data["version"] == 1
        assert "summary" in period_data

        # 1. Company View: exactly 36 employee rows * 31 days = 1,116 cells
        t0 = time.perf_counter()
        grid_res = client.get(f"/api/v1/rosters/{period_id}/grid?view=company")
        elapsed_grid = time.perf_counter() - t0
        assert grid_res.status_code == 200
        grid_data = grid_res.json()
        assert len(grid_data["rows"]) == 36
        print(
            f"[TIMING] Company grid (36 rows x 31 days) retrieval time: {elapsed_grid * 1000:.1f}ms"
        )

        # 2. Pod View
        pod_a = db.scalars(select(Pod).where(Pod.name.like("Pod A%"))).first()
        assert pod_a is not None
        pod_res = client.get(f"/api/v1/rosters/{period_id}/grid?view=pod&ref_id={pod_a.id}")
        assert pod_res.status_code == 200
        assert len(pod_res.json()["rows"]) == 5  # Pod A has EMP-001 (lead) + EMP-007, 008, 009, 010

        # 3. Brand View
        brand_aurora = db.scalars(select(Brand).where(Brand.name == "Aurora")).first()
        assert brand_aurora is not None
        brand_res = client.get(
            f"/api/v1/rosters/{period_id}/grid?view=brand&ref_id={brand_aurora.id}"
        )
        assert brand_res.status_code == 200
        assert len(brand_res.json()["rows"]) >= 1

        # 4. Process View
        proc_cs = db.scalars(select(Process).where(Process.code == "CS")).first()
        assert proc_cs is not None
        proc_res = client.get(f"/api/v1/rosters/{period_id}/grid?view=process&ref_id={proc_cs.id}")
        assert proc_res.status_code == 200
        assert len(proc_res.json()["rows"]) >= 1

        # 5. Employee View
        emp_riya = db.scalars(select(Employee).where(Employee.code == "EMP-007")).first()
        assert emp_riya is not None
        emp_res = client.get(f"/api/v1/rosters/{period_id}/grid?view=employee&ref_id={emp_riya.id}")
        assert emp_res.status_code == 200
        assert len(emp_res.json()["rows"]) == 1

        # 6. Coverage View
        cov_res = client.get(f"/api/v1/rosters/{period_id}/coverage")
        assert cov_res.status_code == 200
        cov_data = cov_res.json()
        assert len(cov_data) > 0

        # 7. Day View
        day_res = client.get(f"/api/v1/rosters/{period_id}/day?date=2026-12-14")
        assert day_res.status_code == 200
        day_data = day_res.json()
        assert len(day_data["groups"]) > 0

        # 8. Conflicts View
        conflicts_res = client.get(f"/api/v1/rosters/{period_id}/conflicts")
        assert conflicts_res.status_code == 200
        assert isinstance(conflicts_res.json(), list)

    db.close()
    Base.metadata.drop_all(engine)


def test_roster_impact_simulation(test_setup: dict) -> None:
    """Test POST /api/v1/rosters/{id}/impact dry-run simulation without DB mutation."""
    client_ops, db = create_client(test_setup, current_user=test_setup["users"]["ops"])

    gen_res = client_ops.post("/api/v1/rosters", json={"month": "2026-12"})
    period_id = gen_res.json()["id"]

    # 1. Non-existent period -> 404
    fake_id = uuid.uuid4()
    assert (
        client_ops.post(f"/api/v1/rosters/{fake_id}/impact", json={"changes": []}).status_code
        == 404
    )

    # 2. Empty changes request returns unchanged count
    empty_impact = client_ops.post(f"/api/v1/rosters/{period_id}/impact", json={"changes": []})
    assert empty_impact.status_code == 200
    assert len(empty_impact.json()["new_conflicts"]) == 0
    assert len(empty_impact.json()["resolved_conflicts"]) == 0

    # 3. Simulate cell edit
    emp = test_setup["employees"][0]
    cell_before = db.scalars(
        select(RosterEntry).where(
            RosterEntry.roster_period_id == uuid.UUID(period_id),
            RosterEntry.employee_id == emp.id,
            RosterEntry.date == dt.date(2026, 12, 1),
        )
    ).first()
    assert cell_before is not None
    orig_status = cell_before.status.value

    impact_res = client_ops.post(
        f"/api/v1/rosters/{period_id}/impact",
        json={
            "edits": [
                {
                    "employee_id": str(emp.id),
                    "date": "2026-12-01",
                    "status": "WEEKLY_OFF",
                }
            ]
        },
    )
    assert impact_res.status_code == 200
    res_data = impact_res.json()
    assert "is_feasible" in res_data
    assert "new_conflicts" in res_data
    assert "affected_dates" in res_data
    assert "2026-12-01" in res_data["affected_dates"]

    # Verify dry-run: cell in DB was NOT modified
    cell_after = db.scalars(
        select(RosterEntry).where(
            RosterEntry.roster_period_id == uuid.UUID(period_id),
            RosterEntry.employee_id == emp.id,
            RosterEntry.date == dt.date(2026, 12, 1),
        )
    ).first()
    assert cell_after is not None
    assert cell_after.status.value == orig_status

    db.close()


def test_roster_impact_scenario_s1() -> None:
    """Golden test for Scenario S1: Add leave for single-resource brand (Aurora) sole employee (Riya Shah)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_factory()

    # Seed scale 1 dataset
    seed_database(db, scale=1, clean=False)

    ops_user = db.scalars(select(User).where(User.role == UserRole.OPS_MANAGER)).first()
    assert ops_user is not None

    emp_riya = db.scalars(select(Employee).where(Employee.code == "EMP-007")).first()
    assert emp_riya is not None
    assert emp_riya.full_name == "Riya Shah"

    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: ops_user

    with TestClient(app, raise_server_exceptions=False) as client:
        # Generate initial clean December 2026 roster
        gen_res = client.post("/api/v1/rosters", json={"month": "2026-12", "options": {"seed": 42}})
        assert gen_res.status_code == 201
        period_id = gen_res.json()["id"]

        # Run impact simulation: add leave for Riya Shah from 2026-12-13 to 2026-12-15
        impact_payload = {
            "changes": [
                {
                    "type": "ADD_LEAVE",
                    "employee_id": str(emp_riya.id),
                    "start_date": "2026-12-13",
                    "end_date": "2026-12-15",
                }
            ]
        }
        res = client.post(f"/api/v1/rosters/{period_id}/impact", json=impact_payload)
        assert res.status_code == 200
        data = res.json()

        assert data["is_feasible"] is False
        assert len(data["new_conflicts"]) > 0

        # Check affected dates: 13, 14, 15 Dec
        expected_dates = ["2026-12-13", "2026-12-14", "2026-12-15"]
        assert all(d in data["affected_dates"] for d in expected_dates)

        # Inspect conflicts on affected dates:
        # 13 Dec (Sun): 2 gaps (CS + ACC) were already in baseline (unchanged_conflicts)
        # 14 Dec (Mon) & 15 Dec (Tue): 3 new gaps each (CS, ACC, NDR) -> 6 new_conflicts
        # Total Aurora gaps across 13-15 Dec = 8
        aurora_new_gaps = [c for c in data["new_conflicts"] if c.get("brand") == "Aurora"]
        assert len(aurora_new_gaps) == 6

        aurora_total_gaps = [
            c
            for c in data["new_conflicts"] + data["unchanged_conflicts"]
            if c.get("brand") == "Aurora" and c.get("date") in expected_dates
        ]
        assert len(aurora_total_gaps) == 8  # CS (Sun-Tue = 3), ACC (Sun-Tue = 3), NDR (Mon-Tue = 2)

        # On 2026-12-13 (Sunday): NDR is closed (EXCLUDE_SUNDAY_AND_HOLIDAYS), so only CS and ACC fail
        dec13_processes = {c["process"] for c in aurora_total_gaps if c.get("date") == "2026-12-13"}
        assert any("Customer Support" in p for p in dec13_processes)
        assert any("Abandoned Cart" in p for p in dec13_processes)
        assert not any("Non-Delivery" in p for p in dec13_processes)

        # On 2026-12-14 (Monday): all 3 processes operate and fail
        dec14_processes = {c["process"] for c in aurora_total_gaps if c.get("date") == "2026-12-14"}
        assert any("Customer Support" in p for p in dec14_processes)
        assert any("Abandoned Cart" in p for p in dec14_processes)
        assert any("Non-Delivery" in p for p in dec14_processes)

        # Suggestions should include floater Kabir Nair (EMP-033)
        sample_gap = aurora_new_gaps[0]
        assert "LEAVE" in sample_gap["root_causes"]
        assert len(sample_gap["suggestions"]) > 0

        suggestion_names = [
            s.get("employee") for s in sample_gap["suggestions"] if s.get("employee")
        ]
        assert any("Kabir" in name for name in suggestion_names)

        # Verify net_effect on floater suggestion
        kabir_sugg = next(s for s in sample_gap["suggestions"] if "Kabir" in s.get("employee", ""))
        assert kabir_sugg["net_effect"]["fixes"] >= 1
        assert kabir_sugg["net_effect"]["opens"] == 0

    db.close()
    Base.metadata.drop_all(engine)
