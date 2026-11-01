"""Security, password hashing, and JWT utilities.

Conforms to SECURITY.md §1, §2 and API_DOCUMENTATION.md §1.
Implements:
- Argon2id password hashing and verification.
- JWT access and refresh token creation and verification.
- Token payload parsing with uniform error handling.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

import argon2
import argon2.exceptions
import jwt
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.errors import AuthenticationError

# Argon2id password hasher with default parameters
_hasher = argon2.PasswordHasher()


def get_password_hash(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return _hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an Argon2 hash.

    Returns False on mismatch, invalid hash format, or corrupt data.
    """
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (
        argon2.exceptions.VerifyMismatchError,
        argon2.exceptions.InvalidHashError,
        argon2.exceptions.VerificationError,
    ):
        return False


class TokenPayload(BaseModel):
    """Parsed claims from a verified JWT token."""

    sub: uuid.UUID
    role: str | None = None
    employee_id: uuid.UUID | None = None
    type: str  # "access" | "refresh"
    exp: int
    iat: int
    jti: str | None = None


def create_access_token(
    subject: str | uuid.UUID,
    role: str,
    employee_id: str | uuid.UUID | None = None,
    expires_delta: dt.timedelta | None = None,
) -> str:
    """Create a signed JWT access token."""
    settings = get_settings()
    now = dt.datetime.now(dt.UTC)
    delta = expires_delta or dt.timedelta(minutes=settings.JWT_ACCESS_MINUTES)
    expire = now + delta

    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "employee_id": str(employee_id) if employee_id else None,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    subject: str | uuid.UUID,
    expires_delta: dt.timedelta | None = None,
) -> str:
    """Create a signed JWT refresh token with unique JTI for rotation."""
    settings = get_settings()
    now = dt.datetime.now(dt.UTC)
    delta = expires_delta or dt.timedelta(days=settings.JWT_REFRESH_DAYS)
    expire = now + delta

    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT signature and expiration.

    Raises:
        AuthenticationError: If token is expired, invalid, or malformed.
    """
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError as e:
        raise AuthenticationError("Token has expired") from e
    except (jwt.InvalidTokenError, jwt.DecodeError) as e:
        raise AuthenticationError("Invalid or malformed token") from e


def verify_token_type(payload: dict[str, Any], expected_type: str) -> None:
    """Verify that decoded token payload matches the expected token type."""
    token_type = payload.get("type")
    if token_type != expected_type:
        raise AuthenticationError(
            f"Invalid token type: expected '{expected_type}', got '{token_type}'"
        )


def parse_token_payload(
    token: str,
    expected_type: str | None = None,
) -> TokenPayload:
    """Decode token, optionally verify token type, and parse into structured TokenPayload."""
    payload = decode_token(token)
    if expected_type is not None:
        verify_token_type(payload, expected_type)

    try:
        return TokenPayload(
            sub=uuid.UUID(payload["sub"]),
            role=payload.get("role"),
            employee_id=(uuid.UUID(payload["employee_id"]) if payload.get("employee_id") else None),
            type=payload["type"],
            exp=payload["exp"],
            iat=payload["iat"],
            jti=payload.get("jti"),
        )
    except (KeyError, ValueError, TypeError) as e:
        raise AuthenticationError("Token payload is missing or has invalid claims") from e
