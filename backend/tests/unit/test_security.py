"""Unit tests for security utilities (password hashing and JWT management).

Verifies:
1. Argon2id password hashing and verification.
2. Access token generation, claims, and verification.
3. Refresh token generation with unique JTI.
4. Expiration detection and error handling.
5. Tampered token and invalid signature rejection.
6. Token type validation (access vs refresh).
7. Structured TokenPayload parsing.
"""

from __future__ import annotations

import datetime as dt
import uuid

import jwt
import pytest

from app.core.config import get_settings
from app.core.errors import AuthenticationError
from app.core.security import (
    TokenPayload,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    parse_token_payload,
    verify_password,
    verify_token_type,
)


def test_password_hashing_and_verification() -> None:
    """Verify that password hashing produces valid Argon2id hashes and validates correctly."""
    pwd = "SecurePassword123!"
    hashed = get_password_hash(pwd)

    # Hash should be an Argon2 string
    assert hashed.startswith("$argon2")
    assert hashed != pwd

    # Correct password succeeds
    assert verify_password(pwd, hashed) is True

    # Incorrect password fails
    assert verify_password("WrongPassword!", hashed) is False

    # Empty or corrupt hash fails gracefully
    assert verify_password(pwd, "not-a-valid-hash") is False
    assert verify_password(pwd, "") is False


def test_access_token_creation_and_claims() -> None:
    """Verify access token creation contains expected claims."""
    user_id = uuid.uuid4()
    emp_id = uuid.uuid4()
    token = create_access_token(
        subject=user_id,
        role="OPS_MANAGER",
        employee_id=emp_id,
    )
    assert isinstance(token, str)

    payload = decode_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["role"] == "OPS_MANAGER"
    assert payload["employee_id"] == str(emp_id)
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "iat" in payload
    assert payload["exp"] > payload["iat"]


def test_refresh_token_creation_and_claims() -> None:
    """Verify refresh token creation contains JTI and refresh type."""
    user_id = uuid.uuid4()
    token = create_refresh_token(subject=user_id)
    assert isinstance(token, str)

    payload = decode_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "refresh"
    assert "jti" in payload
    assert uuid.UUID(payload["jti"])  # valid UUID
    assert "role" not in payload


def test_token_expiration_raises_authentication_error() -> None:
    """Verify that expired tokens raise AuthenticationError."""
    user_id = uuid.uuid4()
    expired_token = create_access_token(
        subject=user_id,
        role="EMPLOYEE",
        expires_delta=dt.timedelta(seconds=-10),  # expired in the past
    )

    with pytest.raises(AuthenticationError, match="Token has expired"):
        decode_token(expired_token)


def test_tampered_token_raises_authentication_error() -> None:
    """Verify that tampered tokens or invalid signatures are rejected."""
    user_id = uuid.uuid4()
    token = create_access_token(subject=user_id, role="POD_LEAD")

    # 1. Corrupt signature
    parts = token.split(".")
    tampered = f"{parts[0]}.{parts[1]}.invalid_signature"
    with pytest.raises(AuthenticationError, match="Invalid or malformed token"):
        decode_token(tampered)

    # 2. Token signed with wrong secret
    fake_token = jwt.encode(
        {"sub": str(user_id), "type": "access"},
        "wrong-secret-key-that-is-at-least-32-bytes-long",
        algorithm="HS256",
    )
    with pytest.raises(AuthenticationError, match="Invalid or malformed token"):
        decode_token(fake_token)


def test_token_type_verification() -> None:
    """Verify that token type checking prevents using refresh tokens as access tokens."""
    user_id = uuid.uuid4()
    refresh_token = create_refresh_token(subject=user_id)
    payload = decode_token(refresh_token)

    # Verifying as refresh succeeds
    verify_token_type(payload, "refresh")

    # Verifying as access fails with AuthenticationError
    with pytest.raises(
        AuthenticationError, match="Invalid token type: expected 'access', got 'refresh'"
    ):
        verify_token_type(payload, "access")


def test_parse_token_payload_success_and_failure() -> None:
    """Verify parse_token_payload correctly parses and validates typed payload."""
    user_id = uuid.uuid4()
    emp_id = uuid.uuid4()
    access_token = create_access_token(
        subject=user_id,
        role="OPS_MANAGER",
        employee_id=emp_id,
    )

    parsed = parse_token_payload(access_token, expected_type="access")
    assert isinstance(parsed, TokenPayload)
    assert parsed.sub == user_id
    assert parsed.role == "OPS_MANAGER"
    assert parsed.employee_id == emp_id
    assert parsed.type == "access"

    # Token with invalid UUID in subject raises AuthenticationError
    settings = get_settings()
    now = dt.datetime.now(dt.UTC)
    bad_uuid_token = jwt.encode(
        {
            "sub": "not-a-uuid",
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int((now + dt.timedelta(minutes=10)).timestamp()),
        },
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    with pytest.raises(AuthenticationError, match="Token payload is missing or has invalid claims"):
        parse_token_payload(bad_uuid_token, expected_type="access")
