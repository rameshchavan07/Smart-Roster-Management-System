"""FastAPI request dependencies (database session, current user, authentication).

Conforms to SECURITY.md §2 and API_DOCUMENTATION.md §1 & §4.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AuthenticationError
from app.core.security import parse_token_payload
from app.db.session import get_db
from app.models.auth import User
from app.repositories.auth import UserRepository

# HTTPBearer extracts Authorization: Bearer <token> header without auto-raising generic 403
_oauth2_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    auth_creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_oauth2_scheme)],
) -> User:
    """Validate Bearer access token and return the authenticated User entity.

    Raises:
        AuthenticationError: If token is missing, invalid, expired, or user not found/inactive.
    """
    if not auth_creds or not auth_creds.credentials:
        raise AuthenticationError("Missing or invalid authentication credentials")

    token = auth_creds.credentials
    token_payload = parse_token_payload(token, expected_type="access")

    user_repo = UserRepository(db)
    user = user_repo.get_by_id(token_payload.sub)
    if not user:
        raise AuthenticationError("User account not found")

    if not user.is_active:
        raise AuthenticationError("User account is inactive")

    return user


def get_current_user_optional(
    db: Annotated[Session, Depends(get_db)],
    auth_creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_oauth2_scheme)],
) -> User | None:
    """Extract authenticated user if valid token present, otherwise return None."""
    if not auth_creds or not auth_creds.credentials:
        return None

    try:
        token_payload = parse_token_payload(auth_creds.credentials, expected_type="access")
        user_repo = UserRepository(db)
        user = user_repo.get_by_id(token_payload.sub)
        if user and user.is_active:
            return user
    except Exception:
        return None
    return None
