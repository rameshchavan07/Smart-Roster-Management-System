"""Unit tests for Pydantic v2 schemas and uniform error handling middleware."""

import uuid
from datetime import date

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.errors import (
    AuthenticationError,
    BadRequestError,
    BusinessValidationError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RateLimitedError,
    RosterBlockedError,
)
from app.main import create_app
from app.models.core import AssignmentType, CalendarType
from app.models.roster import EntrySource, RosterEntryStatus
from app.schemas.auth import UserLoginRequest
from app.schemas.common import PaginatedResponse
from app.schemas.core import (
    AssignmentCreate,
    BrandCreate,
    BrandProcessCreate,
    EmployeeCreate,
    PodCreate,
    ProcessCreate,
)
from app.schemas.roster import (
    RosterAcknowledgeRequest,
    RosterEntryUpdateItem,
    RosterGenerateRequest,
)
from app.schemas.rules import (
    CoverageRuleCreate,
    LeaveCreate,
)


# -----------------------------------------------------------------------------
# Schema Validation Tests
# -----------------------------------------------------------------------------
def test_coverage_rule_schema_validation() -> None:
    """Test CoverageRule mutual exclusivity constraint between weekday and specific_date."""
    bp_id = uuid.uuid4()

    # Valid with weekday
    rule_weekday = CoverageRuleCreate(brand_process_id=bp_id, weekday=0, min_staff=2)
    assert rule_weekday.weekday == 0
    assert rule_weekday.specific_date is None

    # Valid with specific_date
    rule_date = CoverageRuleCreate(
        brand_process_id=bp_id, specific_date=date(2026, 12, 14), min_staff=1
    )
    assert rule_date.specific_date == date(2026, 12, 14)

    # Invalid: both provided
    with pytest.raises(ValidationError):
        CoverageRuleCreate(
            brand_process_id=bp_id,
            weekday=1,
            specific_date=date(2026, 12, 14),
            min_staff=1,
        )

    # Invalid: neither provided
    with pytest.raises(ValidationError):
        CoverageRuleCreate(brand_process_id=bp_id, min_staff=1)


def test_leave_schema_date_range_validation() -> None:
    """Test LeaveCreate validates end_date >= start_date."""
    emp_id = uuid.uuid4()

    # Valid leave
    valid_leave = LeaveCreate(
        employee_id=emp_id,
        start_date=date(2026, 12, 10),
        end_date=date(2026, 12, 12),
    )
    assert valid_leave.start_date <= valid_leave.end_date

    # Invalid leave: end_date < start_date
    with pytest.raises(ValidationError):
        LeaveCreate(
            employee_id=emp_id,
            start_date=date(2026, 12, 15),
            end_date=date(2026, 12, 10),
        )


def test_master_data_schemas() -> None:
    """Test instantiation and valid serialization of master data schemas."""
    pod = PodCreate(name="Pod Alpha")
    assert pod.name == "Pod Alpha"

    proc = ProcessCreate(name="Voice", code="VOICE")
    assert proc.code == "VOICE"

    brand = BrandCreate(name="Aurora", code="AURORA")
    assert brand.name == "Aurora"

    emp = EmployeeCreate(
        code="EMP-100",
        full_name="Alex River",
        email="alex@example.test",
        pod_id=uuid.uuid4(),
        weekly_off_count=1,
        max_consecutive_days=6,
    )
    assert emp.weekly_off_count == 1

    bp = BrandProcessCreate(
        brand_id=uuid.uuid4(),
        process_id=uuid.uuid4(),
        calendar_type=CalendarType.ALL_365,
        min_coverage_default=2,
    )
    assert bp.min_coverage_default == 2

    asgn = AssignmentCreate(
        employee_id=emp.pod_id,
        brand_process_id=bp.brand_id,
        type=AssignmentType.PRIMARY,
    )
    assert asgn.type == AssignmentType.PRIMARY


def test_roster_schemas() -> None:
    """Test roster generation, entry update, and conflict schemas."""
    gen_req = RosterGenerateRequest(month=date(2026, 12, 1), seed=42)
    assert gen_req.month == date(2026, 12, 1)

    entry_edit = RosterEntryUpdateItem(
        employee_id=uuid.uuid4(),
        date=date(2026, 12, 5),
        status=RosterEntryStatus.WORK,
        source=EntrySource.MANUAL,
    )
    assert entry_edit.source == EntrySource.MANUAL

    ack = RosterAcknowledgeRequest(
        conflict_id=uuid.uuid4(),
        reason="Approved by operations head for floor cover",
    )
    assert len(ack.reason) >= 5


def test_paginated_response_wrapper() -> None:
    """Test generic PaginatedResponse container."""
    items = ["item1", "item2", "item3"]
    paginated = PaginatedResponse[str](items=items, total=10, limit=3, offset=0)
    assert paginated.total == 10
    assert len(paginated.items) == 3


# -----------------------------------------------------------------------------
# Uniform Error Envelope and Handler Tests
# -----------------------------------------------------------------------------
@pytest.fixture
def test_app_client() -> TestClient:
    """FastAPI TestClient with custom test routes raising each application exception."""
    app = create_app()
    test_router = APIRouter(prefix="/test-errors")

    @test_router.get("/bad-request")
    def raise_bad_request() -> None:
        raise BadRequestError(message="Invalid query params", details=[{"param": "foo"}])

    @test_router.get("/unauthorized")
    def raise_unauthorized() -> None:
        raise AuthenticationError()

    @test_router.get("/forbidden")
    def raise_forbidden() -> None:
        raise ForbiddenError()

    @test_router.get("/not-found")
    def raise_not_found() -> None:
        raise NotFoundError(message="Employee EMP-999 not found")

    @test_router.get("/conflict")
    def raise_conflict() -> None:
        raise ConflictError(message="Roster already published for month")

    @test_router.get("/business-validation")
    def raise_business_validation() -> None:
        raise BusinessValidationError(message="Leave cannot overlap existing leave")

    @test_router.get("/roster-blocked")
    def raise_roster_blocked() -> None:
        raise RosterBlockedError()

    @test_router.get("/rate-limited")
    def raise_rate_limited() -> None:
        raise RateLimitedError()

    @test_router.get("/unhandled-server-error")
    def raise_unhandled() -> None:
        raise RuntimeError("Unexpected failure")

    @test_router.post("/body-validation")
    def check_body_validation(req: UserLoginRequest) -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(test_router)
    return TestClient(app, raise_server_exceptions=False)


def test_uniform_error_envelope_structure(test_app_client: TestClient) -> None:
    """Verify that every error response matches API_DOCUMENTATION.md §3."""
    cases = [
        ("/test-errors/bad-request", 400, "BAD_REQUEST"),
        ("/test-errors/unauthorized", 401, "UNAUTHENTICATED"),
        ("/test-errors/forbidden", 403, "FORBIDDEN"),
        ("/test-errors/not-found", 404, "NOT_FOUND"),
        ("/test-errors/conflict", 409, "CONFLICT"),
        ("/test-errors/business-validation", 422, "VALIDATION_ERROR"),
        ("/test-errors/roster-blocked", 422, "ROSTER_BLOCKED"),
        ("/test-errors/rate-limited", 429, "RATE_LIMITED"),
        ("/test-errors/unhandled-server-error", 500, "INTERNAL_ERROR"),
    ]

    for path, expected_status, expected_code in cases:
        response = test_app_client.get(path, headers={"X-Request-ID": "test-req-123"})
        assert response.status_code == expected_status, f"Failed on {path}"
        data = response.json()

        assert "error" in data, f"Missing 'error' envelope in {path}"
        error = data["error"]
        assert error["code"] == expected_code
        assert "message" in error
        assert "details" in error
        assert error["request_id"] == "test-req-123"
        assert response.headers.get("X-Request-ID") == "test-req-123"


def test_request_validation_error_envelope(test_app_client: TestClient) -> None:
    """Verify that FastAPI/Pydantic validation errors format cleanly into error envelope."""
    response = test_app_client.post(
        "/test-errors/body-validation",
        json={"email": "not-an-email", "password": ""},
        headers={"X-Request-ID": "validation-req-001"},
    )
    assert response.status_code == 422
    data = response.json()

    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert data["error"]["message"] == "Request validation failed"
    assert data["error"]["request_id"] == "validation-req-001"
    assert len(data["error"]["details"]) > 0
    # Field details check
    field_names = [d["field"] for d in data["error"]["details"]]
    assert any("email" in f for f in field_names)
