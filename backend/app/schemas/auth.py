"""Pydantic v2 schemas for authentication, users, and audit logs.

Conforms to SECURITY.md §2 and API_DOCUMENTATION.md §1 & §4.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.auth import UserRole
from app.schemas.common import EMAIL_REGEX


# -----------------------------------------------------------------------------
# User & Auth Schemas
# -----------------------------------------------------------------------------
class UserLoginRequest(BaseModel):
    """Credentials submitted on /auth/login."""

    email: str = Field(pattern=EMAIL_REGEX, max_length=255)
    password: str = Field(min_length=1)


class UserCreate(BaseModel):
    email: str = Field(pattern=EMAIL_REGEX, max_length=255)
    password: str = Field(min_length=8)
    role: UserRole = UserRole.EMPLOYEE
    employee_id: uuid.UUID | None = None


class UserUpdate(BaseModel):
    email: str | None = Field(default=None, pattern=EMAIL_REGEX, max_length=255)
    password: str | None = Field(default=None, min_length=8)
    role: UserRole | None = None
    employee_id: uuid.UUID | None = None
    is_active: bool | None = None


class UserRead(BaseModel):
    """User account details returned in auth responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: UserRole
    employee_id: uuid.UUID | None = None
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime


class TokenResponse(BaseModel):
    """Token response conforming to API_DOCUMENTATION.md §1."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800  # 30 minutes in seconds
    user: UserRead


class RefreshTokenRequest(BaseModel):
    """Refresh token submitted to /auth/refresh."""

    refresh_token: str = Field(min_length=1)


# -----------------------------------------------------------------------------
# AuditLog Schemas
# -----------------------------------------------------------------------------
class AuditLogRead(BaseModel):
    """Read representation of an audit event."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None = None
    action: str
    entity_type: str
    entity_id: str
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    created_at: datetime
    user_email: str | None = None
