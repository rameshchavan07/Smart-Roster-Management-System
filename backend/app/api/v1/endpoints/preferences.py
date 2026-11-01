"""Employee preferences REST endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
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
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    employee_id: uuid.UUID | None = None,
) -> PaginatedResponse[EmployeePreferenceRead]:
    """List employee preferences with optional employee filter."""
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
) -> EmployeePreferenceRead:
    """Create a new scheduling preference."""
    service = EmployeePreferenceService(db)
    pref = service.create_preference(data)
    db.commit()
    db.refresh(pref)
    return EmployeePreferenceRead.model_validate(pref)


@router.get("/{pref_id}", response_model=EmployeePreferenceRead)
def get_preference(
    pref_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> EmployeePreferenceRead:
    """Get preference by ID."""
    service = EmployeePreferenceService(db)
    pref = service.get_preference(pref_id)
    return EmployeePreferenceRead.model_validate(pref)


@router.put("/{pref_id}", response_model=EmployeePreferenceRead)
def update_preference(
    pref_id: uuid.UUID,
    data: EmployeePreferenceUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> EmployeePreferenceRead:
    """Update preference parameters."""
    service = EmployeePreferenceService(db)
    pref = service.update_preference(pref_id, data)
    db.commit()
    db.refresh(pref)
    return EmployeePreferenceRead.model_validate(pref)


@router.delete("/{pref_id}", response_model=MessageResponse)
def delete_preference(
    pref_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    """Delete a scheduling preference."""
    service = EmployeePreferenceService(db)
    service.delete_preference(pref_id)
    db.commit()
    return MessageResponse(message=f"EmployeePreference '{pref_id}' deleted successfully")
