"""Leaves REST endpoints."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.rules import LeaveStatus
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.rules import (
    LeaveCreate,
    LeaveRead,
    LeaveUpdate,
)
from app.services.rules import LeaveService

router = APIRouter(prefix="/leaves", tags=["Leaves"])


def _to_leave_read(leave: Any) -> LeaveRead:
    res = LeaveRead.model_validate(leave)
    if hasattr(leave, "employee") and leave.employee is not None:
        res.employee_name = leave.employee.full_name
        res.employee_code = leave.employee.code
    return res


@router.get("", response_model=PaginatedResponse[LeaveRead])
def list_leaves(
    db: Annotated[Session, Depends(get_db)],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    employee_id: uuid.UUID | None = None,
    status: LeaveStatus | None = None,
) -> PaginatedResponse[LeaveRead]:
    """List leave requests with optional employee and status filters."""
    service = LeaveService(db)
    items, total = service.list_leaves(
        offset=offset,
        limit=limit,
        employee_id=employee_id,
        status=status,
    )
    read_items = [_to_leave_read(item) for item in items]
    return PaginatedResponse[LeaveRead](items=read_items, total=total, limit=limit, offset=offset)


@router.post("", response_model=LeaveRead, status_code=status.HTTP_201_CREATED)
def create_leave(
    data: LeaveCreate,
    db: Annotated[Session, Depends(get_db)],
) -> LeaveRead:
    """Submit a leave request."""
    service = LeaveService(db)
    leave = service.create_leave(data)
    db.commit()
    db.refresh(leave)
    return _to_leave_read(leave)


@router.get("/{leave_id}", response_model=LeaveRead)
def get_leave(
    leave_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> LeaveRead:
    """Get leave details by ID."""
    service = LeaveService(db)
    leave = service.get_leave(leave_id)
    return _to_leave_read(leave)


@router.put("/{leave_id}", response_model=LeaveRead)
def update_leave(
    leave_id: uuid.UUID,
    data: LeaveUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> LeaveRead:
    """Update leave dates or notes."""
    service = LeaveService(db)
    leave = service.update_leave(leave_id, data)
    db.commit()
    db.refresh(leave)
    return _to_leave_read(leave)


@router.post("/{leave_id}/approve", response_model=LeaveRead)
def approve_leave(
    leave_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> LeaveRead:
    """Approve a requested leave."""
    service = LeaveService(db)
    leave = service.set_leave_status(leave_id, LeaveStatus.APPROVED)
    db.commit()
    db.refresh(leave)
    return _to_leave_read(leave)


@router.post("/{leave_id}/reject", response_model=LeaveRead)
def reject_leave(
    leave_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> LeaveRead:
    """Reject a requested leave."""
    service = LeaveService(db)
    leave = service.set_leave_status(leave_id, LeaveStatus.REJECTED)
    db.commit()
    db.refresh(leave)
    return _to_leave_read(leave)


@router.post("/{leave_id}/cancel", response_model=LeaveRead)
def cancel_leave(
    leave_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> LeaveRead:
    """Cancel a requested or approved leave."""
    service = LeaveService(db)
    leave = service.set_leave_status(leave_id, LeaveStatus.CANCELLED)
    db.commit()
    db.refresh(leave)
    return _to_leave_read(leave)


@router.delete("/{leave_id}", response_model=MessageResponse)
def delete_leave(
    leave_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    """Delete a leave request."""
    service = LeaveService(db)
    service.delete_leave(leave_id)
    db.commit()
    return MessageResponse(message=f"Leave '{leave_id}' deleted successfully")
