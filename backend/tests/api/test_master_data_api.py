"""Integration tests for master data REST endpoints mounted at /api/v1."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app


@pytest.fixture
def api_client() -> Generator[TestClient, None, None]:
    """Test client with test database session dependency override."""
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

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client

    Base.metadata.drop_all(engine)
    app.dependency_overrides.clear()


def test_pods_api_endpoints(api_client: TestClient) -> None:
    """Test full CRUD operations on /api/v1/pods."""
    # 1. Create Pod
    res = api_client.post("/api/v1/pods", json={"name": "Pod North"})
    assert res.status_code == 201
    pod_data = res.json()
    assert pod_data["name"] == "Pod North"
    pod_id = pod_data["id"]

    # 2. Duplicate Pod Name (409)
    res_dup = api_client.post("/api/v1/pods", json={"name": "Pod North"})
    assert res_dup.status_code == 409
    assert res_dup.json()["error"]["code"] == "CONFLICT"

    # 3. List Pods
    res_list = api_client.get("/api/v1/pods?offset=0&limit=10")
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert list_data["total"] == 1
    assert len(list_data["items"]) == 1

    # 4. Get Pod
    res_get = api_client.get(f"/api/v1/pods/{pod_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == pod_id

    # 5. Update Pod
    res_put = api_client.put(f"/api/v1/pods/{pod_id}", json={"name": "Pod North Star"})
    assert res_put.status_code == 200
    assert res_put.json()["name"] == "Pod North Star"

    # 6. Delete Pod
    res_del = api_client.delete(f"/api/v1/pods/{pod_id}")
    assert res_del.status_code == 200

    # 7. Get Deleted Pod (404)
    res_not_found = api_client.get(f"/api/v1/pods/{pod_id}")
    assert res_not_found.status_code == 404
    assert res_not_found.json()["error"]["code"] == "NOT_FOUND"


def test_employees_and_brands_api(api_client: TestClient) -> None:
    """Test Employee, Brand, and Process endpoints."""
    # 1. Create Pod
    pod_res = api_client.post("/api/v1/pods", json={"name": "Customer Pod"})
    pod_id = pod_res.json()["id"]

    # 2. Create Employee
    emp_payload = {
        "code": "EMP-200",
        "full_name": "Taylor Ray",
        "email": "taylor@example.test",
        "pod_id": pod_id,
        "is_floater": False,
        "weekly_off_count": 1,
    }
    emp_res = api_client.post("/api/v1/employees", json=emp_payload)
    assert emp_res.status_code == 201
    emp_data = emp_res.json()
    assert emp_data["code"] == "EMP-200"
    assert emp_data["pod_name"] == "Customer Pod"

    # Duplicate code (409)
    dup_res = api_client.post("/api/v1/employees", json=emp_payload)
    assert dup_res.status_code == 409

    # 3. Create Process
    proc_res = api_client.post(
        "/api/v1/processes",
        json={"name": "Escalations", "code": "ESC", "description": "L2 Support"},
    )
    assert proc_res.status_code == 201

    # 4. Create Brand
    brand_res = api_client.post(
        "/api/v1/brands",
        json={"name": "Summit", "code": "SUM", "pod_id": pod_id},
    )
    assert brand_res.status_code == 201
    brand_data = brand_res.json()
    assert brand_data["pod_name"] == "Customer Pod"

    # 5. List with filters
    emp_list = api_client.get(f"/api/v1/employees?pod_id={pod_id}&is_floater=false")
    assert emp_list.status_code == 200
    assert emp_list.json()["total"] == 1


def test_brand_process_and_assignment_api_lifecycle(api_client: TestClient) -> None:
    """Test BrandProcess creation, Assignment linking, and dependent deletion constraints."""
    # Setup
    pod_id = api_client.post("/api/v1/pods", json={"name": "Logistics Pod"}).json()["id"]
    emp_id = api_client.post(
        "/api/v1/employees",
        json={"code": "EMP-300", "full_name": "Morgan West", "pod_id": pod_id},
    ).json()["id"]
    proc_id = api_client.post(
        "/api/v1/processes", json={"name": "Returns Ops", "code": "RET"}
    ).json()["id"]
    brand_id = api_client.post(
        "/api/v1/brands", json={"name": "Apex", "code": "APX", "pod_id": pod_id}
    ).json()["id"]

    # 1. Create BrandProcess
    bp_res = api_client.post(
        "/api/v1/brand-processes",
        json={
            "brand_id": brand_id,
            "process_id": proc_id,
            "calendar_type": "ALL_365",
            "min_coverage_default": 2,
        },
    )
    assert bp_res.status_code == 201
    bp_id = bp_res.json()["id"]

    # 2. Duplicate BrandProcess (409)
    bp_dup = api_client.post(
        "/api/v1/brand-processes",
        json={"brand_id": brand_id, "process_id": proc_id},
    )
    assert bp_dup.status_code == 409

    # 3. Create Assignment
    asgn_res = api_client.post(
        "/api/v1/assignments",
        json={
            "employee_id": emp_id,
            "brand_process_id": bp_id,
            "type": "PRIMARY",
            "allocation_pct": 100,
            "valid_from": "2026-12-01",
        },
    )
    assert asgn_res.status_code == 201
    asgn_id = asgn_res.json()["id"]

    # 4. Attempt to delete BrandProcess while Assignment exists (409)
    del_bp_fail = api_client.delete(f"/api/v1/brand-processes/{bp_id}")
    assert del_bp_fail.status_code == 409
    assert del_bp_fail.json()["error"]["code"] == "CONFLICT"

    # 5. Delete Assignment
    del_asgn = api_client.delete(f"/api/v1/assignments/{asgn_id}")
    assert del_asgn.status_code == 200

    # 6. Delete BrandProcess succeeds now
    del_bp_ok = api_client.delete(f"/api/v1/brand-processes/{bp_id}")
    assert del_bp_ok.status_code == 200
