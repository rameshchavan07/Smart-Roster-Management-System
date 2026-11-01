"""Integration tests for rules and availability REST endpoints mounted at /api/v1."""

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


@pytest.fixture
def api_client() -> Generator[TestClient, None, None]:
    """Test client with test database session and admin user dependency override."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
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


def test_coverage_rules_api(api_client: TestClient) -> None:
    """Test CRUD operations on /api/v1/coverage-rules."""
    # Setup Pod, Process, Brand, BrandProcess
    pod_id = api_client.post("/api/v1/pods", json={"name": "Support Pod"}).json()["id"]
    proc_id = api_client.post("/api/v1/processes", json={"name": "Tickets", "code": "TCK"}).json()[
        "id"
    ]
    brand_id = api_client.post(
        "/api/v1/brands", json={"name": "AlphaBrand", "code": "AB", "pod_id": pod_id}
    ).json()["id"]
    bp_id = api_client.post(
        "/api/v1/brand-processes",
        json={"brand_id": brand_id, "process_id": proc_id, "min_coverage_default": 1},
    ).json()["id"]

    # 1. Create Coverage Rule (weekday=0: Monday)
    res = api_client.post(
        "/api/v1/coverage-rules",
        json={"brand_process_id": bp_id, "weekday": 0, "min_staff": 3, "reason": "Busy Monday"},
    )
    assert res.status_code == 201
    rule_data = res.json()
    assert rule_data["min_staff"] == 3
    rule_id = rule_data["id"]

    # 2. List Coverage Rules
    res_list = api_client.get(f"/api/v1/coverage-rules?brand_process_id={bp_id}")
    assert res_list.status_code == 200
    assert res_list.json()["total"] == 1

    # 3. Update Rule
    res_up = api_client.put(f"/api/v1/coverage-rules/{rule_id}", json={"min_staff": 4})
    assert res_up.status_code == 200
    assert res_up.json()["min_staff"] == 4

    # 4. Delete Rule
    res_del = api_client.delete(f"/api/v1/coverage-rules/{rule_id}")
    assert res_del.status_code == 200


def test_holidays_api(api_client: TestClient) -> None:
    """Test Holiday CRUD and unique constraint enforcement."""
    # 1. Create Global Holiday
    res = api_client.post(
        "/api/v1/holidays",
        json={"date": "2026-12-25", "name": "Christmas Day"},
    )
    assert res.status_code == 201
    h_id = res.json()["id"]

    # 2. Duplicate Global Holiday (409)
    res_dup = api_client.post(
        "/api/v1/holidays",
        json={"date": "2026-12-25", "name": "Christmas Day Duplicate"},
    )
    assert res_dup.status_code == 409
    assert res_dup.json()["error"]["code"] == "CONFLICT"

    # 3. List Holidays
    res_list = api_client.get("/api/v1/holidays?year=2026")
    assert res_list.status_code == 200
    assert res_list.json()["total"] == 1

    # 4. Update Holiday
    res_up = api_client.put(f"/api/v1/holidays/{h_id}", json={"name": "Christmas Holiday"})
    assert res_up.status_code == 200
    assert res_up.json()["name"] == "Christmas Holiday"

    # 5. Delete Holiday
    res_del = api_client.delete(f"/api/v1/holidays/{h_id}")
    assert res_del.status_code == 200


def test_weekly_off_and_preference_api(api_client: TestClient) -> None:
    """Test WeeklyOffRules and EmployeePreferences endpoints."""
    pod_id = api_client.post("/api/v1/pods", json={"name": "Care Pod"}).json()["id"]
    emp_id = api_client.post(
        "/api/v1/employees",
        json={"code": "EMP-400", "full_name": "Robin Banks", "pod_id": pod_id},
    ).json()["id"]

    # 1. WeeklyOffRule Create
    wo_res = api_client.post(
        "/api/v1/weekly-off-rules",
        json={"employee_id": emp_id, "mode": "FIXED_MANDATORY", "weekdays": [6]},
    )
    assert wo_res.status_code == 201
    wo_id = wo_res.json()["id"]

    # 2. WeeklyOffRule Update
    wo_up = api_client.put(
        f"/api/v1/weekly-off-rules/{wo_id}",
        json={"mode": "FIXED_PREFERRED", "weekdays": [5, 6]},
    )
    assert wo_up.status_code == 200
    assert wo_up.json()["weekdays"] == [5, 6]

    # 3. Employee Preference Create
    pref_res = api_client.post(
        "/api/v1/preferences",
        json={
            "employee_id": emp_id,
            "kind": "PREFERRED_OFF_WEEKDAY",
            "value": {"weekday": 6},
            "weight": 5,
        },
    )
    assert pref_res.status_code == 201
    pref_id = pref_res.json()["id"]

    # 4. Preference Update
    pref_up = api_client.put(f"/api/v1/preferences/{pref_id}", json={"weight": 8})
    assert pref_up.status_code == 200
    assert pref_up.json()["weight"] == 8


def test_leaves_and_compoff_lifecycle_api(api_client: TestClient) -> None:
    """Test Leave request/approval, overlap rejection, and CompOff balance/redemption."""
    pod_id = api_client.post("/api/v1/pods", json={"name": "Dev Pod"}).json()["id"]
    emp_id = api_client.post(
        "/api/v1/employees",
        json={"code": "EMP-500", "full_name": "Chris Green", "pod_id": pod_id},
    ).json()["id"]

    # 1. Create Leave Request
    leave_res = api_client.post(
        "/api/v1/leaves",
        json={
            "employee_id": emp_id,
            "start_date": "2026-12-10",
            "end_date": "2026-12-12",
            "type": "PLANNED",
            "note": "Family trip",
        },
    )
    assert leave_res.status_code == 201
    leave_data = leave_res.json()
    assert leave_data["status"] == "REQUESTED"
    leave_id = leave_data["id"]

    # 2. Overlapping Leave Conflict (409)
    overlap_res = api_client.post(
        "/api/v1/leaves",
        json={
            "employee_id": emp_id,
            "start_date": "2026-12-11",
            "end_date": "2026-12-14",
            "type": "SICK",
        },
    )
    assert overlap_res.status_code == 409
    assert overlap_res.json()["error"]["code"] == "CONFLICT"

    # 3. Approve Leave
    appr_res = api_client.post(f"/api/v1/leaves/{leave_id}/approve")
    assert appr_res.status_code == 200
    assert appr_res.json()["status"] == "APPROVED"

    # 4. Comp-off initial balance
    bal_res = api_client.get(f"/api/v1/comp-offs/balance?employee_id={emp_id}")
    assert bal_res.status_code == 200
    assert bal_res.json()["available"] == 0

    # 5. Attempt Comp-off redeem with 0 balance (409)
    zero_redeem = api_client.post(
        "/api/v1/comp-offs/redeem",
        json={"employee_id": emp_id, "date": "2026-12-20"},
    )
    assert zero_redeem.status_code == 409

    # 6. Credit Comp-off
    credit_res = api_client.post(
        "/api/v1/comp-offs",
        json={
            "employee_id": emp_id,
            "entry_date": "2026-12-05",
            "kind": "EARNED",
            "note": "Holiday shift coverage",
        },
    )
    assert credit_res.status_code == 201

    # 7. Balance check (1 available)
    bal_after = api_client.get(f"/api/v1/comp-offs/balance?employee_id={emp_id}")
    assert bal_after.json()["available"] == 1

    # 8. Redeem Comp-off
    redeem_ok = api_client.post(
        "/api/v1/comp-offs/redeem",
        json={"employee_id": emp_id, "date": "2026-12-20"},
    )
    assert redeem_ok.status_code == 201

    # 9. Balance check (0 available, 1 redeemed)
    bal_final = api_client.get(f"/api/v1/comp-offs/balance?employee_id={emp_id}")
    assert bal_final.json()["available"] == 0
    assert bal_final.json()["redeemed"] == 1
