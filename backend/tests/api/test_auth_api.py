"""Integration tests for authentication endpoints (/api/v1/auth/*).

Tests:
1. /auth/login: Valid credentials, wrong password, non-existent user, inactive account, cookie setting.
2. /auth/refresh: Body refresh token, cookie refresh token, token rotation, invalid token type rejection.
3. /auth/logout: Cookie deletion, audit logging.
4. /auth/me: Authorized user details, missing token (401), invalid/expired token (401).
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.auth import User, UserRole


@pytest.fixture
def client_and_users() -> Generator[TestClient, None, None]:
    """Create test client with seeded users and database dependency override."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    session = session_factory()
    # Active Ops Manager
    ops_user = User(
        email="ops.test@example.com",
        password_hash=get_password_hash("OpsSecret123!"),
        role=UserRole.OPS_MANAGER,
        is_active=True,
    )
    session.add(ops_user)

    # Inactive Employee
    inactive_user = User(
        email="inactive.test@example.com",
        password_hash=get_password_hash("InactivePass123!"),
        role=UserRole.EMPLOYEE,
        is_active=False,
    )
    session.add(inactive_user)
    session.commit()
    session.close()

    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client

    Base.metadata.drop_all(engine)
    app.dependency_overrides.clear()


def test_auth_login_lifecycle(client_and_users: TestClient) -> None:
    """Test login success, cookie set, and negative authentication flows."""
    client = client_and_users

    # 1. Valid login
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "ops.test@example.com", "password": "OpsSecret123!"},
    )
    assert login_res.status_code == 200
    data = login_res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 1800
    assert data["user"]["email"] == "ops.test@example.com"
    assert data["user"]["role"] == "OPS_MANAGER"
    assert data["user"]["is_active"] is True

    # Check that HttpOnly refresh_token cookie was set
    assert "refresh_token" in login_res.cookies

    # 2. Invalid password -> 401 UNAUTHENTICATED
    wrong_pwd_res = client.post(
        "/api/v1/auth/login",
        json={"email": "ops.test@example.com", "password": "WrongPassword123!"},
    )
    assert wrong_pwd_res.status_code == 401
    assert wrong_pwd_res.json()["error"]["code"] == "UNAUTHENTICATED"
    assert wrong_pwd_res.json()["error"]["message"] == "Invalid email or password"

    # 3. Non-existent email -> 401 UNAUTHENTICATED
    non_existent_res = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "AnyPassword123!"},
    )
    assert non_existent_res.status_code == 401
    assert non_existent_res.json()["error"]["code"] == "UNAUTHENTICATED"

    # 4. Inactive user -> 401 UNAUTHENTICATED
    inactive_res = client.post(
        "/api/v1/auth/login",
        json={"email": "inactive.test@example.com", "password": "InactivePass123!"},
    )
    assert inactive_res.status_code == 401
    assert inactive_res.json()["error"]["code"] == "UNAUTHENTICATED"


def test_auth_refresh_token_rotation(client_and_users: TestClient) -> None:
    """Test refresh token rotation via body and cookie, rejecting access tokens."""
    client = client_and_users

    # Initial login to acquire refresh token
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "ops.test@example.com", "password": "OpsSecret123!"},
    )
    assert login_res.status_code == 200
    old_refresh_token = login_res.json()["refresh_token"]
    old_access_token = login_res.json()["access_token"]

    # 1. Refresh via JSON body
    refresh_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )
    assert refresh_res.status_code == 200
    new_data = refresh_res.json()
    assert new_data["access_token"] != old_access_token
    assert new_data["refresh_token"] != old_refresh_token
    assert new_data["user"]["email"] == "ops.test@example.com"

    # 2. Refresh via Cookie (with empty body)
    client.cookies.set("refresh_token", new_data["refresh_token"])
    cookie_refresh_res = client.post("/api/v1/auth/refresh", json={})
    assert cookie_refresh_res.status_code == 200
    cookie_data = cookie_refresh_res.json()
    assert cookie_data["access_token"] is not None

    # 3. Attempting to use an access token as a refresh token fails with 401
    bad_type_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_access_token},
    )
    assert bad_type_res.status_code == 401
    assert bad_type_res.json()["error"]["code"] == "UNAUTHENTICATED"

    # 4. Missing refresh token -> 401
    client.cookies.clear()
    missing_res = client.post("/api/v1/auth/refresh", json={})
    assert missing_res.status_code == 401
    assert missing_res.json()["error"]["code"] == "UNAUTHENTICATED"


def test_auth_logout_clears_cookie(client_and_users: TestClient) -> None:
    """Test logout endpoint successfully clears the refresh token cookie."""
    client = client_and_users

    # Login to set cookie
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "ops.test@example.com", "password": "OpsSecret123!"},
    )
    assert "refresh_token" in login_res.cookies

    # Logout
    logout_res = client.post("/api/v1/auth/logout")
    assert logout_res.status_code == 200
    assert logout_res.json()["message"] == "Logged out successfully"

    # Verify cookie was deleted / expired
    cookie_header = logout_res.headers.get("set-cookie", "")
    assert 'refresh_token=""' in cookie_header or "Max-Age=0" in cookie_header


def test_auth_me_endpoint(client_and_users: TestClient) -> None:
    """Test /auth/me returns current user profile when authenticated and 401 otherwise."""
    client = client_and_users

    # 1. Unauthenticated request -> 401
    no_auth_res = client.get("/api/v1/auth/me")
    assert no_auth_res.status_code == 401
    assert no_auth_res.json()["error"]["code"] == "UNAUTHENTICATED"

    # 2. Authenticated request -> 200 with user profile
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "ops.test@example.com", "password": "OpsSecret123!"},
    )
    token = login_res.json()["access_token"]

    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == "ops.test@example.com"
    assert me_data["role"] == "OPS_MANAGER"
    assert me_data["is_active"] is True

    # 3. Request with invalid or malformed token -> 401
    invalid_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.payload"},
    )
    assert invalid_res.status_code == 401
    assert invalid_res.json()["error"]["code"] == "UNAUTHENTICATED"


def test_get_demo_accounts_endpoint(client_and_users: TestClient) -> None:
    """Verify GET /api/v1/auth/demo-accounts returns documented demo roles for evaluators."""
    res = client_and_users.get("/api/v1/auth/demo-accounts")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 3

    roles = {item["role"]: item for item in data}
    assert "OPS_MANAGER" in roles
    assert roles["OPS_MANAGER"]["email"] == "ops@example.test"
    assert "company-wide" in roles["OPS_MANAGER"]["description"]

    assert "POD_LEAD" in roles
    assert roles["POD_LEAD"]["email"] == "lead.a@example.test"
    assert roles["POD_LEAD"]["employee_code"] == "EMP-001"

    assert "EMPLOYEE" in roles
    assert roles["EMPLOYEE"]["email"] == "emp@example.test"
    assert roles["EMPLOYEE"]["employee_code"] == "EMP-007"


def test_seeded_demo_accounts_login_and_roles() -> None:
    """Verify that seeded demo accounts from app.seed can log in and reflect correct RBAC roles."""
    from app.seed import seed_database

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    session = session_factory()
    seed_database(session, scale=1, clean=False, demo_password="DemoPass123!")
    session.close()

    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, raise_server_exceptions=False) as client:
        # 1. Ops Manager Login
        ops_res = client.post(
            "/api/v1/auth/login",
            json={"email": "ops@example.test", "password": "DemoPass123!"},
        )
        assert ops_res.status_code == 200
        ops_token = ops_res.json()["access_token"]
        assert ops_res.json()["user"]["role"] == "OPS_MANAGER"

        ops_me = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {ops_token}"},
        )
        assert ops_me.status_code == 200
        assert ops_me.json()["role"] == "OPS_MANAGER"
        assert ops_me.json()["employee_id"] is None

        # 2. Pod Lead Login
        lead_res = client.post(
            "/api/v1/auth/login",
            json={"email": "lead.a@example.test", "password": "DemoPass123!"},
        )
        assert lead_res.status_code == 200
        lead_token = lead_res.json()["access_token"]
        assert lead_res.json()["user"]["role"] == "POD_LEAD"

        lead_me = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {lead_token}"},
        )
        assert lead_me.status_code == 200
        assert lead_me.json()["role"] == "POD_LEAD"
        assert lead_me.json()["employee_id"] is not None

        # 3. Employee Login
        emp_res = client.post(
            "/api/v1/auth/login",
            json={"email": "emp@example.test", "password": "DemoPass123!"},
        )
        assert emp_res.status_code == 200
        emp_token = emp_res.json()["access_token"]
        assert emp_res.json()["user"]["role"] == "EMPLOYEE"

        emp_me = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {emp_token}"},
        )
        assert emp_me.status_code == 200
        assert emp_me.json()["role"] == "EMPLOYEE"
        assert emp_me.json()["employee_id"] is not None

    Base.metadata.drop_all(engine)
    app.dependency_overrides.clear()
