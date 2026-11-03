"""Unit tests for security headers middleware and rate limiting (T-903).

Conforms to docs/SECURITY.md §5, §6 and §10.
"""

from fastapi.testclient import TestClient

from app.core.rate_limit import SlidingWindowRateLimiter, login_rate_limiter, solver_rate_limiter
from app.main import app

client = TestClient(app)


def test_security_headers_present_on_responses() -> None:
    """Verify that all responses carry the required browser security headers per SECURITY.md §5."""
    response = client.get("/health")
    assert response.status_code == 200

    # Required transport and browser protection headers
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "camera=()" in response.headers.get("Permissions-Policy", "")
    assert "frame-ancestors 'none'" in response.headers.get("Content-Security-Policy", "")


def test_rate_limiter_sliding_window_logic() -> None:
    """Verify in-memory sliding window rate limiter triggers 429 when limit exceeded."""
    test_limiter = SlidingWindowRateLimiter(limit=3, window_seconds=10)
    test_limiter.enabled_in_tests = True

    # First 3 hits should succeed without exception
    test_limiter.check("client_test_key")
    test_limiter.check("client_test_key")
    test_limiter.check("client_test_key")

    # 4th hit should raise RateLimitedError with details
    try:
        test_limiter.check("client_test_key")
        raise AssertionError("Expected RateLimitedError")
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 429
        assert getattr(exc, "code", None) == "RATE_LIMITED"


def test_auth_login_rate_limiting_endpoint() -> None:
    """Verify repeated failed login attempts trigger HTTP 429 RateLimited."""
    login_rate_limiter.reset()
    login_rate_limiter.enabled_in_tests = True

    try:
        # Trigger failed logins up to the limit
        for _ in range(15):
            resp = client.post(
                "/api/v1/auth/login",
                json={"email": "brute_force@example.test", "password": "wrong_password"},
            )
            assert resp.status_code in (401, 429)

        # 16th request must be rate limited with uniform 429 envelope
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "brute_force@example.test", "password": "wrong_password"},
        )
        assert resp.status_code == 429
        body = resp.json()
        assert body["error"]["code"] == "RATE_LIMITED"
        assert "retry" in body["error"]["message"].lower() or "too many" in body["error"]["message"].lower()
        assert "request_id" in body["error"]
    finally:
        # Reset for other tests
        login_rate_limiter.reset()
        login_rate_limiter.enabled_in_tests = False
        solver_rate_limiter.reset()
        solver_rate_limiter.enabled_in_tests = False
