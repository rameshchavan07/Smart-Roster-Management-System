"""Comprehensive RBAC and scoping matrix tests for all API endpoints.

Conforms to SECURITY.md §2 and API_DOCUMENTATION.md §1 & §4.
Tests:
- 401 UNAUTHENTICATED for unauthenticated calls
- OPS_MANAGER global permissions
- POD_LEAD scoping (allowed within own pod, 403 on other pods or global resources)
- EMPLOYEE boundaries (self-only access, cannot approve leaves, 403 on management endpoints)
"""

from collections.abc import Generator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user, get_db
from app.db.base import Base
from app.main import create_app
from app.models.auth import User, UserRole
from app.models.core import Employee, Pod
from app.models.rules import Leave, LeaveStatus, LeaveType


@pytest.fixture
def rbac_setup() -> Generator[dict, None, None]:
    """Sets up an in-memory test database with pods, employees, and users across roles."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_factory()

    # Create Pods
    pod_a = Pod(name="Pod Alpha")
    pod_b = Pod(name="Pod Beta")
    db.add_all([pod_a, pod_b])
    db.flush()

    # Create Employees
    # Emp A1 is Pod Lead for Pod A
    emp_a1 = Employee(
        full_name="Alice Lead",
        code="EMP-A1",
        email="alice.lead@example.com",
        pod_id=pod_a.id,
    )
    # Emp A2 is regular Employee in Pod A
    emp_a2 = Employee(
        full_name="Bob Staff",
        code="EMP-A2",
        email="bob.staff@example.com",
        pod_id=pod_a.id,
    )
    # Emp B1 is regular Employee in Pod B
    emp_b1 = Employee(
        full_name="Charlie Beta",
        code="EMP-B1",
        email="charlie.beta@example.com",
        pod_id=pod_b.id,
    )
    db.add_all([emp_a1, emp_a2, emp_b1])
    db.flush()

    pod_a.lead_employee_id = emp_a1.id
    db.flush()

    # Create Users
    user_ops = User(
        email="ops@example.com",
        password_hash="test_hash",
        role=UserRole.OPS_MANAGER,
        is_active=True,
    )
    user_lead_a = User(
        email="lead.a@example.com",
        password_hash="test_hash",
        role=UserRole.POD_LEAD,
        employee_id=emp_a1.id,
        is_active=True,
    )
    user_emp_a2 = User(
        email="emp.a2@example.com",
        password_hash="test_hash",
        role=UserRole.EMPLOYEE,
        employee_id=emp_a2.id,
        is_active=True,
    )
    user_emp_b1 = User(
        email="emp.b1@example.com",
        password_hash="test_hash",
        role=UserRole.EMPLOYEE,
        employee_id=emp_b1.id,
        is_active=True,
    )
    db.add_all([user_ops, user_lead_a, user_emp_a2, user_emp_b1])
    db.commit()

    context = {
        "engine": engine,
        "session_factory": session_factory,
        "pod_a": pod_a,
        "pod_b": pod_b,
        "emp_a1": emp_a1,
        "emp_a2": emp_a2,
        "emp_b1": emp_b1,
        "user_ops": user_ops,
        "user_lead_a": user_lead_a,
        "user_emp_a2": user_emp_a2,
        "user_emp_b1": user_emp_b1,
    }

    yield context

    db.close()
    Base.metadata.drop_all(engine)


def make_client_for_user(rbac_setup: dict, user: User | None) -> TestClient:
    """Create a TestClient with dependency overrides for the test DB and specified user."""
    app = create_app()
    session_factory = rbac_setup["session_factory"]

    def override_get_db() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    if user is not None:
        app.dependency_overrides[get_current_user] = lambda: user

    return TestClient(app, raise_server_exceptions=False)


def test_unauthenticated_requests_fail(rbac_setup: dict) -> None:
    """Protected endpoints must reject unauthenticated requests with 401 UNAUTHENTICATED."""
    client = make_client_for_user(rbac_setup, user=None)

    # Protected routes
    res = client.post("/api/v1/pods", json={"name": "Anon Pod"})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHENTICATED"

    res = client.post(
        "/api/v1/employees",
        json={
            "full_name": "Anon User",
            "code": "ANON1",
            "email": "anon@test.com",
            "pod_id": str(rbac_setup["pod_a"].id),
        },
    )
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHENTICATED"

    res = client.get(f"/api/v1/comp-offs/balance?employee_id={rbac_setup['emp_a1'].id}")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHENTICATED"


def test_employee_permissions_and_boundaries(rbac_setup: dict) -> None:
    """Verify EMPLOYEE permissions: self-only actions allowed; other employees and management blocked."""
    client_a2 = make_client_for_user(rbac_setup, rbac_setup["user_emp_a2"])
    emp_a2_id = str(rbac_setup["emp_a2"].id)
    emp_b1_id = str(rbac_setup["emp_b1"].id)

    # 1. Employee cannot create a pod (403)
    res = client_a2.post("/api/v1/pods", json={"name": "Emp Pod"})
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"

    # 2. Employee cannot create an employee (403)
    res = client_a2.post(
        "/api/v1/employees",
        json={
            "full_name": "New Hire",
            "code": "NH1",
            "email": "nh1@test.com",
            "pod_id": str(rbac_setup["pod_a"].id),
        },
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"

    # 3. Employee can submit leave for SELF in REQUESTED status
    res = client_a2.post(
        "/api/v1/leaves",
        json={
            "employee_id": emp_a2_id,
            "start_date": "2026-11-10",
            "end_date": "2026-11-10",
            "leave_type": "PLANNED",
            "status": "REQUESTED",
        },
    )
    assert res.status_code == 201
    leave_id = res.json()["id"]

    # 4. Employee CANNOT submit leave directly APPROVED (403)
    res_direct_approve = client_a2.post(
        "/api/v1/leaves",
        json={
            "employee_id": emp_a2_id,
            "start_date": "2026-11-12",
            "end_date": "2026-11-12",
            "leave_type": "PLANNED",
            "status": "APPROVED",
        },
    )
    assert res_direct_approve.status_code == 403
    assert res_direct_approve.json()["error"]["code"] == "FORBIDDEN"

    # 5. Employee CANNOT submit leave for ANOTHER employee (403)
    res_other = client_a2.post(
        "/api/v1/leaves",
        json={
            "employee_id": emp_b1_id,
            "start_date": "2026-11-15",
            "end_date": "2026-11-15",
            "leave_type": "PLANNED",
            "status": "REQUESTED",
        },
    )
    assert res_other.status_code == 403
    assert res_other.json()["error"]["code"] == "FORBIDDEN"

    # 6. Employee CANNOT approve leaves (403)
    res_approve = client_a2.post(f"/api/v1/leaves/{leave_id}/approve")
    assert res_approve.status_code == 403

    # 7. Employee CAN query own comp-off balance
    res_bal = client_a2.get(f"/api/v1/comp-offs/balance?employee_id={emp_a2_id}")
    assert res_bal.status_code == 200

    # 8. Employee CANNOT query another employee's comp-off balance (403)
    res_other_bal = client_a2.get(f"/api/v1/comp-offs/balance?employee_id={emp_b1_id}")
    assert res_other_bal.status_code == 403

    # 9. Employee CAN create preference for SELF
    res_pref = client_a2.post(
        "/api/v1/preferences",
        json={
            "employee_id": emp_a2_id,
            "kind": "PREFERRED_OFF_WEEKDAY",
            "value": {"weekday": 0},
            "weight": 5,
        },
    )
    assert res_pref.status_code == 201

    # 10. Employee CANNOT create preference for ANOTHER employee (403)
    res_other_pref = client_a2.post(
        "/api/v1/preferences",
        json={
            "employee_id": emp_b1_id,
            "kind": "PREFERRED_OFF_WEEKDAY",
            "value": {"weekday": 1},
            "weight": 5,
        },
    )
    assert res_other_pref.status_code == 403


def test_pod_lead_scoping_and_boundaries(rbac_setup: dict) -> None:
    """Verify POD_LEAD permissions: scoped to own pod; 403 on other pods or global administration."""
    client_lead = make_client_for_user(rbac_setup, rbac_setup["user_lead_a"])
    pod_a_id = str(rbac_setup["pod_a"].id)
    pod_b_id = str(rbac_setup["pod_b"].id)
    emp_a2_id = str(rbac_setup["emp_a2"].id)
    emp_b1_id = str(rbac_setup["emp_b1"].id)

    # 1. Pod Lead CAN update own pod (Pod A)
    res = client_lead.put(f"/api/v1/pods/{pod_a_id}", json={"name": "Pod Alpha Renamed"})
    assert res.status_code == 200
    assert res.json()["name"] == "Pod Alpha Renamed"

    # 2. Pod Lead CANNOT update another pod (Pod B) -> 403
    res_b = client_lead.put(f"/api/v1/pods/{pod_b_id}", json={"name": "Pod Beta Hacked"})
    assert res_b.status_code == 403
    assert res_b.json()["error"]["code"] == "FORBIDDEN"

    # 3. Pod Lead CANNOT create a new pod (Ops Manager only) -> 403
    res_create_pod = client_lead.post("/api/v1/pods", json={"name": "New Pod"})
    assert res_create_pod.status_code == 403

    # 4. Pod Lead CANNOT delete any pod (Ops Manager only) -> 403
    res_del_pod = client_lead.delete(f"/api/v1/pods/{pod_a_id}")
    assert res_del_pod.status_code == 403

    # 5. Pod Lead CAN create employee in own pod
    res_emp = client_lead.post(
        "/api/v1/employees",
        json={
            "full_name": "Dennis Junior",
            "code": "EMP-A3",
            "email": "dennis@example.com",
            "pod_id": pod_a_id,
        },
    )
    assert res_emp.status_code == 201

    # 6. Pod Lead CANNOT create employee in another pod (Pod B) -> 403
    res_emp_b = client_lead.post(
        "/api/v1/employees",
        json={
            "full_name": "Eve Intruder",
            "code": "EMP-B2",
            "email": "eve@example.com",
            "pod_id": pod_b_id,
        },
    )
    assert res_emp_b.status_code == 403

    # 7. Pod Lead CAN update employee in own pod
    res_update_emp = client_lead.put(
        f"/api/v1/employees/{emp_a2_id}",
        json={"full_name": "Robert Staff"},
    )
    assert res_update_emp.status_code == 200
    assert res_update_emp.json()["full_name"] == "Robert Staff"

    # 8. Pod Lead CANNOT update employee in another pod (Emp B1) -> 403
    res_update_emp_b = client_lead.put(
        f"/api/v1/employees/{emp_b1_id}",
        json={"full_name": "Charles Beta"},
    )
    assert res_update_emp_b.status_code == 403

    # 9. Pod Lead CANNOT delete an employee (Ops Manager only) -> 403
    res_del_emp = client_lead.delete(f"/api/v1/employees/{emp_a2_id}")
    assert res_del_emp.status_code == 403

    # 10. Leave approval scoping:
    # Setup leaves for emp_a2 and emp_b1
    db = rbac_setup["session_factory"]()
    leave_a = Leave(
        employee_id=rbac_setup["emp_a2"].id,
        start_date=date(2026, 11, 20),
        end_date=date(2026, 11, 20),
        type=LeaveType.PLANNED,
        status=LeaveStatus.REQUESTED,
    )
    leave_b = Leave(
        employee_id=rbac_setup["emp_b1"].id,
        start_date=date(2026, 11, 20),
        end_date=date(2026, 11, 20),
        type=LeaveType.PLANNED,
        status=LeaveStatus.REQUESTED,
    )
    db.add_all([leave_a, leave_b])
    db.commit()
    leave_a_id = str(leave_a.id)
    leave_b_id = str(leave_b.id)
    db.close()

    # Pod Lead CAN approve leave of own pod member
    res_app_a = client_lead.post(f"/api/v1/leaves/{leave_a_id}/approve")
    assert res_app_a.status_code == 200
    assert res_app_a.json()["status"] == "APPROVED"

    # Pod Lead CANNOT approve leave of another pod's member -> 403
    res_app_b = client_lead.post(f"/api/v1/leaves/{leave_b_id}/approve")
    assert res_app_b.status_code == 403

    # 11. Pod Lead CANNOT create global holidays (Ops Manager only) -> 403
    res_hol = client_lead.post(
        "/api/v1/holidays",
        json={"name": "Lead Holiday", "date": "2026-12-25"},
    )
    assert res_hol.status_code == 403

    # 12. Pod Lead CANNOT create global processes (Ops Manager only) -> 403
    res_proc = client_lead.post(
        "/api/v1/processes",
        json={"name": "Lead Process", "code": "LP"},
    )
    assert res_proc.status_code == 403


def test_ops_manager_global_permissions(rbac_setup: dict) -> None:
    """Verify OPS_MANAGER has unrestricted global management authority."""
    client_ops = make_client_for_user(rbac_setup, rbac_setup["user_ops"])
    pod_b_id = str(rbac_setup["pod_b"].id)
    emp_b1_id = str(rbac_setup["emp_b1"].id)

    # 1. Ops Manager can create a pod
    res_pod = client_ops.post("/api/v1/pods", json={"name": "Pod Gamma"})
    assert res_pod.status_code == 201

    # 2. Ops Manager can create global process
    res_proc = client_ops.post("/api/v1/processes", json={"name": "Chat Support", "code": "CHT"})
    assert res_proc.status_code == 201

    # 3. Ops Manager can create global holiday
    res_hol = client_ops.post("/api/v1/holidays", json={"name": "Christmas", "date": "2026-12-25"})
    assert res_hol.status_code == 201

    # 4. Ops Manager can update employees across any pod
    res_emp = client_ops.put(
        f"/api/v1/employees/{emp_b1_id}",
        json={"notes": "Global Ops updated this record"},
    )
    assert res_emp.status_code == 200

    # 5. Ops Manager can update any pod
    res_update_pod = client_ops.put(f"/api/v1/pods/{pod_b_id}", json={"name": "Pod Beta Renamed"})
    assert res_update_pod.status_code == 200
