"""Employee preferences REST endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    check_employee_scope,
    get_current_user,
    get_db,
)
from app.core.errors import ForbiddenError
from app.models.auth import User, UserRole
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.rules import (
    EmployeePreferenceCreate,
    EmployeePreferenceRead,
    EmployeePreferenceUpdate,
)
from app.services.rules import EmployeePreferenceService

router = APIRouter(prefix="/preferences", tags=["Preferences"])


@router.get("", response_model=PaginatedResponse[EmployeePreferenceRead])
def list_preferences(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    employee_id: uuid.UUID | None = None,
) -> PaginatedResponse[EmployeePreferenceRead]:
    """List employee preferences with optional employee filter."""
    if current_user.role == UserRole.EMPLOYEE:
        if employee_id is not None and employee_id != current_user.employee_id:
            raise ForbiddenError("Employees can only view their own preferences")
        employee_id = current_user.employee_id
    elif employee_id is not None:
        check_employee_scope(current_user, employee_id, db)

    service = EmployeePreferenceService(db)
    items, total = service.list_preferences(offset=offset, limit=limit, employee_id=employee_id)
    read_items = [EmployeePreferenceRead.model_validate(item) for item in items]
    return PaginatedResponse[EmployeePreferenceRead](
        items=read_items, total=total, limit=limit, offset=offset
    )


@router.post("", response_model=EmployeePreferenceRead, status_code=status.HTTP_201_CREATED)
def create_preference(
    data: EmployeePreferenceCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> EmployeePreferenceRead:
    """Create a new scheduling preference."""
    check_employee_scope(current_user, data.employee_id, db)
    service = EmployeePreferenceService(db)
    pref = service.create_preference(data)
    db.commit()
    db.refresh(pref)
    return EmployeePreferenceRead.model_validate(pref)


@router.get("/{pref_id}", response_model=EmployeePreferenceRead)
def get_preference(
    pref_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> EmployeePreferenceRead:
    """Get preference by ID."""
    service = EmployeePreferenceService(db)
    pref = service.get_preference(pref_id)
    check_employee_scope(current_user, pref.employee_id, db)
    return EmployeePreferenceRead.model_validate(pref)


@router.put("/{pref_id}", response_model=EmployeePreferenceRead)
def update_preference(
    pref_id: uuid.UUID,
    data: EmployeePreferenceUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> EmployeePreferenceRead:
    """Update preference parameters."""
    service = EmployeePreferenceService(db)
    pref = service.get_preference(pref_id)
    check_employee_scope(current_user, pref.employee_id, db)

    updated_pref = service.update_preference(pref_id, data)
    db.commit()
    db.refresh(updated_pref)
    return EmployeePreferenceRead.model_validate(updated_pref)


@router.delete("/{pref_id}", response_model=MessageResponse)
def delete_preference(
    pref_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MessageResponse:
    """Delete a scheduling preference."""
    service = EmployeePreferenceService(db)
    pref = service.get_preference(pref_id)
    check_employee_scope(current_user, pref.employee_id, db)

    service.delete_preference(pref_id)
    db.commit()
    return MessageResponse(message=f"EmployeePreference '{pref_id}' deleted successfully")
