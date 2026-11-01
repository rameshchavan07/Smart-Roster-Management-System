"""Master data endpoints for Employees."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    check_employee_scope,
    check_pod_scope,
    get_db,
    require_ops_manager,
    require_pod_lead_or_manager,
)
from app.models.auth import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.core import EmployeeCreate, EmployeeRead, EmployeeUpdate
from app.services.master_data import EmployeeService

router = APIRouter(prefix="/employees", tags=["Employees"])


def _to_emp_read(emp: Any) -> EmployeeRead:
    res = EmployeeRead.model_validate(emp)
    if hasattr(emp, "pod") and emp.pod is not None:
        res.pod_name = emp.pod.name
    return res


@router.get("", response_model=PaginatedResponse[EmployeeRead])
def list_employees(
    db: Annotated[Session, Depends(get_db)],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    pod_id: uuid.UUID | None = None,
    is_active: bool | None = None,
    is_floater: bool | None = None,
) -> PaginatedResponse[EmployeeRead]:
    """List employees with pagination and optional filters."""
    service = EmployeeService(db)
    items, total = service.list_employees(
        offset=offset,
        limit=limit,
        pod_id=pod_id,
        is_active=is_active,
        is_floater=is_floater,
    )
    read_items = [_to_emp_read(item) for item in items]
    return PaginatedResponse[EmployeeRead](
        items=read_items, total=total, limit=limit, offset=offset
    )


@router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
def create_employee(
    data: EmployeeCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_pod_lead_or_manager)],
) -> EmployeeRead:
    """Create a new employee (Ops Manager or scoped Pod Lead)."""
    check_pod_scope(current_user, data.pod_id, db)
    service = EmployeeService(db)
    emp = service.create_employee(data, actor_id=current_user.id)
    db.commit()
    db.refresh(emp)
    return _to_emp_read(emp)


@router.get("/{employee_id}", response_model=EmployeeRead)
def get_employee(
    employee_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> EmployeeRead:
    """Get employee by ID."""
    service = EmployeeService(db)
    emp = service.get_employee(employee_id)
    return _to_emp_read(emp)


@router.put("/{employee_id}", response_model=EmployeeRead)
def update_employee(
    employee_id: uuid.UUID,
    data: EmployeeUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_pod_lead_or_manager)],
) -> EmployeeRead:
    """Update employee details (Ops Manager or scoped Pod Lead)."""
    check_employee_scope(current_user, employee_id, db)
    if data.pod_id is not None:
        check_pod_scope(current_user, data.pod_id, db)
    service = EmployeeService(db)
    emp = service.update_employee(employee_id, data, actor_id=current_user.id)
    db.commit()
    db.refresh(emp)
    return _to_emp_read(emp)


@router.delete("/{employee_id}", response_model=MessageResponse)
def delete_employee(
    employee_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_ops_manager)],
) -> MessageResponse:
    """Delete an employee if they have no active assignments or history (Ops Manager only)."""
    service = EmployeeService(db)
    service.delete_employee(employee_id, actor_id=current_user.id)
    db.commit()
    return MessageResponse(message=f"Employee '{employee_id}' deleted successfully")
