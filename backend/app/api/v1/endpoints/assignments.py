"""Master data endpoints for Staffing Assignments."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.core import (
    AssignmentCreate,
    AssignmentRead,
    AssignmentUpdate,
)
from app.services.master_data import AssignmentService

router = APIRouter(prefix="/assignments", tags=["Assignments"])


def _to_asgn_read(asgn: Any) -> AssignmentRead:
    res = AssignmentRead.model_validate(asgn)
    if hasattr(asgn, "employee") and asgn.employee is not None:
        res.employee_name = asgn.employee.full_name
        res.employee_code = asgn.employee.code
    return res


@router.get("", response_model=PaginatedResponse[AssignmentRead])
def list_assignments(
    db: Annotated[Session, Depends(get_db)],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    employee_id: uuid.UUID | None = None,
    brand_process_id: uuid.UUID | None = None,
) -> PaginatedResponse[AssignmentRead]:
    """List staffing assignments with pagination and optional filters."""
    service = AssignmentService(db)
    items, total = service.list_assignments(
        offset=offset,
        limit=limit,
        employee_id=employee_id,
        brand_process_id=brand_process_id,
    )
    read_items = [_to_asgn_read(item) for item in items]
    return PaginatedResponse[AssignmentRead](
        items=read_items, total=total, limit=limit, offset=offset
    )


@router.post("", response_model=AssignmentRead, status_code=status.HTTP_201_CREATED)
def create_assignment(
    data: AssignmentCreate,
    db: Annotated[Session, Depends(get_db)],
) -> AssignmentRead:
    """Create a new staffing assignment (PRIMARY or BACKUP)."""
    service = AssignmentService(db)
    assignment = service.create_assignment(data)
    db.commit()
    db.refresh(assignment)
    return _to_asgn_read(assignment)


@router.get("/{assignment_id}", response_model=AssignmentRead)
def get_assignment(
    assignment_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> AssignmentRead:
    """Get assignment details by ID."""
    service = AssignmentService(db)
    assignment = service.get_assignment(assignment_id)
    return _to_asgn_read(assignment)


@router.put("/{assignment_id}", response_model=AssignmentRead)
def update_assignment(
    assignment_id: uuid.UUID,
    data: AssignmentUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> AssignmentRead:
    """Update assignment attributes."""
    service = AssignmentService(db)
    assignment = service.update_assignment(assignment_id, data)
    db.commit()
    db.refresh(assignment)
    return _to_asgn_read(assignment)


@router.delete("/{assignment_id}", response_model=MessageResponse)
def delete_assignment(
    assignment_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    """Delete a staffing assignment."""
    service = AssignmentService(db)
    service.delete_assignment(assignment_id)
    db.commit()
    return MessageResponse(message=f"Assignment '{assignment_id}' deleted successfully")
