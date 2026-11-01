"""Leaves REST endpoints."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    check_employee_scope,
    get_current_user,
    get_db,
    require_pod_lead_or_manager,
)
from app.core.errors import ForbiddenError
from app.models.auth import User, UserRole
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
    current_user: Annotated[User, Depends(get_current_user)],
) -> LeaveRead:
    """Submit a leave request (scoped to employee or pod lead/manager)."""
    check_employee_scope(current_user, data.employee_id, db)
    if current_user.role == UserRole.EMPLOYEE and data.status == LeaveStatus.APPROVED:
        raise ForbiddenError("Employees cannot directly approve leaves")

    service = LeaveService(db)
    leave = service.create_leave(data, actor_id=current_user.id)
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
    current_user: Annotated[User, Depends(get_current_user)],
) -> LeaveRead:
    """Update leave dates or notes."""
    service = LeaveService(db)
    leave = service.get_leave(leave_id)
    check_employee_scope(current_user, leave.employee_id, db)

    updated = service.update_leave(leave_id, data, actor_id=current_user.id)
    db.commit()
    db.refresh(updated)
    return _to_leave_read(updated)


@router.post("/{leave_id}/approve", response_model=LeaveRead)
def approve_leave(
    leave_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_pod_lead_or_manager)],
) -> LeaveRead:
    """Approve a requested leave (Ops Manager or scoped Pod Lead)."""
    service = LeaveService(db)
    leave = service.get_leave(leave_id)
    check_employee_scope(current_user, leave.employee_id, db)

    approved = service.set_leave_status(leave_id, LeaveStatus.APPROVED, actor_id=current_user.id)
    db.commit()
    db.refresh(approved)
    return _to_leave_read(approved)


@router.post("/{leave_id}/reject", response_model=LeaveRead)
def reject_leave(
    leave_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_pod_lead_or_manager)],
) -> LeaveRead:
    """Reject a requested leave (Ops Manager or scoped Pod Lead)."""
    service = LeaveService(db)
    leave = service.get_leave(leave_id)
    check_employee_scope(current_user, leave.employee_id, db)

    rejected = service.set_leave_status(leave_id, LeaveStatus.REJECTED, actor_id=current_user.id)
    db.commit()
    db.refresh(rejected)
    return _to_leave_read(rejected)


@router.post("/{leave_id}/cancel", response_model=LeaveRead)
def cancel_leave(
    leave_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LeaveRead:
    """Cancel a requested or approved leave."""
    service = LeaveService(db)
    leave = service.get_leave(leave_id)
    check_employee_scope(current_user, leave.employee_id, db)

    cancelled = service.set_leave_status(leave_id, LeaveStatus.CANCELLED, actor_id=current_user.id)
    db.commit()
    db.refresh(cancelled)
    return _to_leave_read(cancelled)


@router.delete("/{leave_id}", response_model=MessageResponse)
def delete_leave(
    leave_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_pod_lead_or_manager)],
) -> MessageResponse:
    """Delete a leave request (Manager or scoped Pod Lead)."""
    service = LeaveService(db)
    leave = service.get_leave(leave_id)
    check_employee_scope(current_user, leave.employee_id, db)

    service.delete_leave(leave_id, actor_id=current_user.id)
    db.commit()
    return MessageResponse(message=f"Leave '{leave_id}' deleted successfully")
