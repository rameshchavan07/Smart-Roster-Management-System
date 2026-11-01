"""Uniform error format and global exception handling per API_DOCUMENTATION.md §3."""

import logging
import uuid
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ErrorDetail(BaseModel):
    """Structured detail for a specific field or constraint issue."""

    field: str | None = None
    issue: str


class ErrorBody(BaseModel):
    """Payload inside standard error envelope."""

    code: str
    message: str
    details: list[dict[str, Any]] | None = None
    request_id: str


class ErrorResponse(BaseModel):
    """Uniform top-level error response envelope."""

    error: ErrorBody


class AppError(Exception):
    """Base application exception returning uniform envelope."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or []


class BadRequestError(AppError):
    """400 Bad Request error."""

    def __init__(
        self,
        message: str = "Bad request",
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            code="BAD_REQUEST",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class AuthenticationError(AppError):
    """401 Unauthenticated error."""

    def __init__(
        self,
        message: str = "Missing or invalid authentication credentials",
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            code="UNAUTHENTICATED",
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class ForbiddenError(AppError):
    """403 Forbidden error."""

    def __init__(
        self,
        message: str = "Permission denied for this action",
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            code="FORBIDDEN",
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class NotFoundError(AppError):
    """404 Not Found error."""

    def __init__(
        self,
        message: str = "Requested resource was not found",
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            code="NOT_FOUND",
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ConflictError(AppError):
    """409 Conflict error (duplicate, overlap, or state conflict)."""

    def __init__(
        self,
        message: str = "State conflict or duplicate resource",
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            code="CONFLICT",
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class BusinessValidationError(AppError):
    """422 Validation / Business logic error."""

    def __init__(
        self,
        message: str = "Validation or business constraint failed",
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class RosterBlockedError(AppError):
    """422 Roster publish attempted with unresolved BLOCKING conflicts."""

    def __init__(
        self,
        message: str = "Cannot publish roster with unresolved BLOCKING conflicts",
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            code="ROSTER_BLOCKED",
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class RateLimitedError(AppError):
    """429 Rate limited error."""

    def __init__(
        self,
        message: str = "Rate limit exceeded. Please retry later",
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            code="RATE_LIMITED",
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
        )


def create_error_response(
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
    request_id: str | None = None,
) -> JSONResponse:
    """Helper to return uniform error response conforming to API_DOCUMENTATION.md §3."""
    req_id = request_id or str(uuid.uuid4())
    content = {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
            "request_id": req_id,
        }
    }
    return JSONResponse(
        status_code=status_code,
        content=content,
        headers={"X-Request-ID": req_id},
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle domain and application level errors."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return create_error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
        request_id=request_id,
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI standard HTTPExceptions with uniform error envelope."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    code_mapping = {
        400: "BAD_REQUEST",
        401: "UNAUTHENTICATED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
        500: "INTERNAL_ERROR",
    }
    code = code_mapping.get(exc.status_code, "ERROR")
    return create_error_response(
        status_code=exc.status_code,
        code=code,
        message=str(exc.detail),
        request_id=request_id,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors with structured details."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    details = []
    for err in exc.errors():
        loc = ".".join(str(item) for item in err.get("loc", []))
        details.append({"field": loc, "issue": err.get("msg", "invalid")})

    return create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="VALIDATION_ERROR",
        message="Request validation failed",
        details=details,
        request_id=request_id,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unhandled server exceptions (500)."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.exception("Unhandled server exception: %s (request_id=%s)", exc, request_id)
    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_ERROR",
        message="An unexpected server error occurred",
        request_id=request_id,
    )
