"""Authentication REST API endpoints (/auth/login, /auth/refresh, /auth/logout, /auth/me).

Conforms to SECURITY.md §1, §5 and API_DOCUMENTATION.md §1 & §4.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_user_optional, get_db
from app.core.config import get_settings
from app.core.errors import AuthenticationError
from app.core.rate_limit import login_rate_limiter
from app.models.auth import User, UserRole
from app.schemas.auth import (
    DemoAccountRead,
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserRead,
)
from app.schemas.common import MessageResponse
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(
    data: UserLoginRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    """Authenticate user with email and password, returning JWT access and refresh tokens."""
    settings = get_settings()
    auth_service = AuthService(db)
    client_ip = request.client.host if request.client else "unknown"

    # Enforce login rate limit per IP + email (SECURITY.md §1)
    login_rate_limiter.check(f"login:{client_ip}:{data.email}")

    token_response, refresh_token = auth_service.login(data, actor_ip=client_ip)
    db.commit()

    # Set secure HttpOnly cookie for web clients
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.APP_ENV != "local",
        samesite="lax",
        max_age=settings.JWT_REFRESH_DAYS * 86400,
        path="/api/v1/auth",
    )
    return token_response


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def refresh_token(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    data: RefreshTokenRequest | None = None,
    refresh_token_cookie: Annotated[str | None, Cookie(alias="refresh_token")] = None,
) -> TokenResponse:
    """Rotate JWT access and refresh tokens using either JSON payload or HttpOnly cookie."""
    token_str = (
        data.refresh_token if data and data.refresh_token else None
    ) or refresh_token_cookie
    if not token_str:
        raise AuthenticationError("Missing refresh token")

    settings = get_settings()
    auth_service = AuthService(db)
    client_ip = request.client.host if request.client else None

    token_response, new_refresh_token = auth_service.refresh(token_str, actor_ip=client_ip)
    db.commit()

    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=settings.APP_ENV != "local",
        samesite="lax",
        max_age=settings.JWT_REFRESH_DAYS * 86400,
        path="/api/v1/auth",
    )
    return token_response


@router.post("/logout", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def logout(
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_current_user_optional)] = None,
) -> MessageResponse:
    """Terminate session and delete the refresh token cookie."""
    auth_service = AuthService(db)
    auth_service.logout(user_id=current_user.id if current_user else None)
    db.commit()

    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
    )
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserRead, status_code=status.HTTP_200_OK)
def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserRead:
    """Return the currently authenticated user's profile and RBAC role."""
    return UserRead.model_validate(current_user)


@router.get("/demo-accounts", response_model=list[DemoAccountRead], status_code=status.HTTP_200_OK)
def get_demo_accounts() -> list[DemoAccountRead]:
    """Return publicly documented demo accounts for evaluators conforming to SAMPLE_DATA.md §8."""
    settings = get_settings()
    pwd = settings.DEMO_PASSWORD if settings.APP_ENV != "production" else None
    return [
        DemoAccountRead(
            role=UserRole.OPS_MANAGER,
            email="ops@example.test",
            description="Full company-wide management, generation, and publishing",
            default_password=pwd,
        ),
        DemoAccountRead(
            role=UserRole.POD_LEAD,
            email="lead.a@example.test",
            description="Pod A scoped management; reviews own pod roster",
            employee_code="EMP-001",
            employee_name="Aarav Sharma",
            default_password=pwd,
        ),
        DemoAccountRead(
            role=UserRole.EMPLOYEE,
            email="emp@example.test",
            description="Linked to EMP-007 (Riya Shah); read-only personal schedule & ledger",
            employee_code="EMP-007",
            employee_name="Riya Shah",
            default_password=pwd,
        ),
    ]
