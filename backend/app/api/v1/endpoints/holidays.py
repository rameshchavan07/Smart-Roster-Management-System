"""Holidays REST endpoints."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_ops_manager
from app.models.auth import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.rules import (
    HolidayCreate,
    HolidayRead,
    HolidayUpdate,
)
from app.services.rules import HolidayService

router = APIRouter(prefix="/holidays", tags=["Holidays"])


def _to_holiday_read(h: Any) -> HolidayRead:
    res = HolidayRead.model_validate(h)
    if hasattr(h, "brand") and h.brand is not None:
        res.brand_name = h.brand.name
    return res


@router.get("", response_model=PaginatedResponse[HolidayRead])
def list_holidays(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    brand_id: uuid.UUID | None = None,
    year: int | None = None,
    is_active: bool | None = None,
) -> PaginatedResponse[HolidayRead]:
    """List holidays with optional brand or year filter."""
    service = HolidayService(db)
    items, total = service.list_holidays(
        offset=offset,
        limit=limit,
        brand_id=brand_id,
        year=year,
        is_active=is_active,
    )
    read_items = [_to_holiday_read(item) for item in items]
    return PaginatedResponse[HolidayRead](items=read_items, total=total, limit=limit, offset=offset)


@router.post("", response_model=HolidayRead, status_code=status.HTTP_201_CREATED)
def create_holiday(
    data: HolidayCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_ops_manager)],
) -> HolidayRead:
    """Create a new global or brand-scoped holiday (Ops Manager only)."""
    service = HolidayService(db)
    holiday = service.create_holiday(data)
    db.commit()
    db.refresh(holiday)
    return _to_holiday_read(holiday)


@router.get("/{holiday_id}", response_model=HolidayRead)
def get_holiday(
    holiday_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> HolidayRead:
    """Get holiday by ID."""
    service = HolidayService(db)
    holiday = service.get_holiday(holiday_id)
    return _to_holiday_read(holiday)


@router.put("/{holiday_id}", response_model=HolidayRead)
def update_holiday(
    holiday_id: uuid.UUID,
    data: HolidayUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_ops_manager)],
) -> HolidayRead:
    """Update holiday attributes (Ops Manager only)."""
    service = HolidayService(db)
    holiday = service.update_holiday(holiday_id, data)
    db.commit()
    db.refresh(holiday)
    return _to_holiday_read(holiday)


@router.delete("/{holiday_id}", response_model=MessageResponse)
def delete_holiday(
    holiday_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_ops_manager)],
) -> MessageResponse:
    """Delete a holiday (Ops Manager only)."""
    service = HolidayService(db)
    service.delete_holiday(holiday_id)
    db.commit()
    return MessageResponse(message=f"Holiday '{holiday_id}' deleted successfully")
