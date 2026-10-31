"""Uniform error format and global exception handling."""

import uuid
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    field: str | None = None
    issue: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[dict[str, Any]] | None = None
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorBody


class AppError(Exception):
    """Base application exception."""

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


def create_error_response(
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
    request_id: str | None = None,
) -> JSONResponse:
    """Helper to return uniform error response."""
    req_id = request_id or str(uuid.uuid4())
    content = {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
            "request_id": req_id,
        }
    }
    return JSONResponse(status_code=status_code, content=content)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return create_error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
        request_id=request_id,
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
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
