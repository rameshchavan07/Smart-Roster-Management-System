"""FastAPI request dependencies (database session, authentication, RBAC, and scoping).

Conforms to SECURITY.md §2 and API_DOCUMENTATION.md §1 & §4.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AuthenticationError, ForbiddenError, NotFoundError
from app.core.security import parse_token_payload
from app.db.session import get_db
from app.models.auth import User, UserRole
from app.models.core import Employee, Pod
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


def require_roles(*allowed_roles: UserRole) -> Callable[..., User]:
    """Dependency checking that the authenticated user possesses one of the allowed roles.

    Raises:
        ForbiddenError: If user's role is not within allowed_roles.
    """

    def role_checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role not in allowed_roles:
            role_names = ", ".join(r.value for r in allowed_roles)
            raise ForbiddenError(f"Insufficient permissions: requires one of [{role_names}]")
        return current_user

    return role_checker


# Role shortcut dependencies
require_ops_manager = require_roles(UserRole.OPS_MANAGER)
require_pod_lead_or_manager = require_roles(UserRole.OPS_MANAGER, UserRole.POD_LEAD)


def get_user_pod_id(user: User, db: Session) -> uuid.UUID | None:
    """Resolve the pod ID associated with a user (via their employee record or led pod)."""
    if not user.employee_id:
        return None

    emp = db.query(Employee).filter(Employee.id == user.employee_id).first()
    if emp:
        return emp.pod_id

    pod = db.query(Pod).filter(Pod.lead_employee_id == user.employee_id).first()
    if pod:
        return pod.id

    return None


def check_pod_scope(user: User, pod_id: uuid.UUID, db: Session) -> None:
    """Verify that user has permission to manage the target pod.

    - OPS_MANAGER: Allowed for all pods.
    - POD_LEAD: Allowed only for own pod.
    - EMPLOYEE: Denied.
    """
    if user.role == UserRole.OPS_MANAGER:
        return

    if user.role == UserRole.POD_LEAD:
        user_pod_id = get_user_pod_id(user, db)
        if not user_pod_id or user_pod_id != pod_id:
            raise ForbiddenError("Pod leads can only manage resources in their own pod")
        return

    raise ForbiddenError("Employees do not have pod management permissions")


def check_employee_scope(user: User, target_employee_id: uuid.UUID, db: Session) -> None:
    """Verify that user has permission to view or manage the target employee.

    - OPS_MANAGER: Allowed for all employees.
    - POD_LEAD: Allowed for employees in own pod.
    - EMPLOYEE: Allowed only for own employee record.
    """
    if user.role == UserRole.OPS_MANAGER:
        return

    if user.role == UserRole.POD_LEAD:
        target_emp = db.query(Employee).filter(Employee.id == target_employee_id).first()
        if not target_emp:
            raise NotFoundError(f"Employee '{target_employee_id}' not found")

        user_pod_id = get_user_pod_id(user, db)
        if not user_pod_id or target_emp.pod_id != user_pod_id:
            raise ForbiddenError("Pod leads can only manage employees within their own pod")
        return

    if user.role == UserRole.EMPLOYEE:
        if not user.employee_id or user.employee_id != target_employee_id:
            raise ForbiddenError("Employees can only access their own records")
        return

    raise ForbiddenError("Permission denied")
