"""Authentication and user session services.

Conforms to SECURITY.md §1, §2 and API_DOCUMENTATION.md §1 & §4.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AuthenticationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    parse_token_payload,
    verify_password,
)
from app.repositories.auth import UserRepository
from app.repositories.core import AuditLogRepository
from app.schemas.auth import TokenResponse, UserLoginRequest, UserRead


class AuthService:
    """Service handling user login, token refresh, and logout."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.audit_repo = AuditLogRepository(session)

    def login(
        self,
        data: UserLoginRequest,
        actor_ip: str | None = None,
    ) -> tuple[TokenResponse, str]:
        """Authenticate user with email and password, returning tokens.

        Raises:
            AuthenticationError: If email or password is invalid or account is inactive.
        """
        user = self.user_repo.get_by_email(data.email)
        if not user or not user.is_active:
            raise AuthenticationError("Invalid email or password")

        if not verify_password(data.password, user.password_hash):
            raise AuthenticationError("Invalid email or password")

        user.last_login_at = dt.datetime.now(dt.UTC)
        self.session.flush()

        settings = get_settings()
        access_token = create_access_token(
            subject=user.id,
            role=user.role.value,
            employee_id=user.employee_id,
        )
        refresh_token = create_refresh_token(subject=user.id)

        self.audit_repo.log_mutation(
            action="auth.login",
            entity_type="User",
            entity_id=str(user.id),
            user_id=user.id,
            before=None,
            after={"ip": actor_ip} if actor_ip else None,
        )

        token_response = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_MINUTES * 60,
            user=UserRead.model_validate(user),
        )
        return token_response, refresh_token

    def refresh(
        self,
        token_str: str,
        actor_ip: str | None = None,
    ) -> tuple[TokenResponse, str]:
        """Rotate access and refresh tokens.

        Raises:
            AuthenticationError: If refresh token is expired, invalid, or user is inactive.
        """
        payload = parse_token_payload(token_str, expected_type="refresh")
        user = self.user_repo.get_by_id(payload.sub)
        if not user or not user.is_active:
            raise AuthenticationError("User account not found or inactive")

        settings = get_settings()
        new_access_token = create_access_token(
            subject=user.id,
            role=user.role.value,
            employee_id=user.employee_id,
        )
        new_refresh_token = create_refresh_token(subject=user.id)

        self.audit_repo.log_mutation(
            action="auth.refresh",
            entity_type="User",
            entity_id=str(user.id),
            user_id=user.id,
            before={"jti": payload.jti},
            after={"ip": actor_ip} if actor_ip else None,
        )

        token_response = TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_MINUTES * 60,
            user=UserRead.model_validate(user),
        )
        return token_response, new_refresh_token

    def logout(self, user_id: uuid.UUID | None = None) -> None:
        """Log user session termination."""
        if user_id:
            self.audit_repo.log_mutation(
                action="auth.logout",
                entity_type="User",
                entity_id=str(user_id),
                user_id=user_id,
                before=None,
                after=None,
            )
