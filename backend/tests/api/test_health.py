"""Tests for health check endpoints and request ID tracking."""

from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    """Verify /health returns 200, status ok, and X-Request-ID header."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "Smart Roster Management System"
    assert "version" in data
    assert "X-Request-ID" in response.headers


def test_api_v1_health(client: TestClient) -> None:
    """Verify /api/v1/health functions identically."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_ready_check(client: TestClient) -> None:
    """Verify /ready returns status ready."""
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_custom_request_id_preserved(client: TestClient) -> None:
    """Verify custom X-Request-ID passed in header is echoed back."""
    custom_id = "test-custom-request-id-12345"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id
