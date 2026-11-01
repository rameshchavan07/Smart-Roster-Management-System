"""Weekly-off rules REST endpoints."""

import uuid
from typing import Annotated

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
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.rules import (
    WeeklyOffRuleCreate,
    WeeklyOffRuleRead,
    WeeklyOffRuleUpdate,
)
from app.services.rules import WeeklyOffRuleService

router = APIRouter(prefix="/weekly-off-rules", tags=["WeeklyOffRules"])


@router.get("", response_model=PaginatedResponse[WeeklyOffRuleRead])
def list_weekly_off_rules(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    employee_id: uuid.UUID | None = None,
) -> PaginatedResponse[WeeklyOffRuleRead]:
    """List weekly-off rules with optional employee filter."""
    if current_user.role == UserRole.EMPLOYEE:
        if employee_id is not None and employee_id != current_user.employee_id:
            raise ForbiddenError("Employees can only view their own weekly-off rules")
        employee_id = current_user.employee_id
    elif employee_id is not None:
        check_employee_scope(current_user, employee_id, db)

    service = WeeklyOffRuleService(db)
    items, total = service.list_weekly_off_rules(
        offset=offset, limit=limit, employee_id=employee_id
    )
    read_items = [WeeklyOffRuleRead.model_validate(item) for item in items]
    return PaginatedResponse[WeeklyOffRuleRead](
        items=read_items, total=total, limit=limit, offset=offset
    )


@router.post("", response_model=WeeklyOffRuleRead, status_code=status.HTTP_201_CREATED)
def create_weekly_off_rule(
    data: WeeklyOffRuleCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_pod_lead_or_manager)],
) -> WeeklyOffRuleRead:
    """Create a weekly-off rule for an employee."""
    check_employee_scope(current_user, data.employee_id, db)
    service = WeeklyOffRuleService(db)
    rule = service.create_weekly_off_rule(data)
    db.commit()
    db.refresh(rule)
    return WeeklyOffRuleRead.model_validate(rule)


@router.get("/{rule_id}", response_model=WeeklyOffRuleRead)
def get_weekly_off_rule(
    rule_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WeeklyOffRuleRead:
    """Get weekly-off rule by ID."""
    service = WeeklyOffRuleService(db)
    rule = service.get_weekly_off_rule(rule_id)
    check_employee_scope(current_user, rule.employee_id, db)
    return WeeklyOffRuleRead.model_validate(rule)


@router.put("/{rule_id}", response_model=WeeklyOffRuleRead)
def update_weekly_off_rule(
    rule_id: uuid.UUID,
    data: WeeklyOffRuleUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_pod_lead_or_manager)],
) -> WeeklyOffRuleRead:
    """Update weekly-off rule attributes."""
    service = WeeklyOffRuleService(db)
    rule = service.get_weekly_off_rule(rule_id)
    check_employee_scope(current_user, rule.employee_id, db)

    updated_rule = service.update_weekly_off_rule(rule_id, data)
    db.commit()
    db.refresh(updated_rule)
    return WeeklyOffRuleRead.model_validate(updated_rule)


@router.delete("/{rule_id}", response_model=MessageResponse)
def delete_weekly_off_rule(
    rule_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_pod_lead_or_manager)],
) -> MessageResponse:
    """Delete a weekly-off rule."""
    service = WeeklyOffRuleService(db)
    rule = service.get_weekly_off_rule(rule_id)
    check_employee_scope(current_user, rule.employee_id, db)

    service.delete_weekly_off_rule(rule_id)
    db.commit()
    return MessageResponse(message=f"WeeklyOffRule '{rule_id}' deleted successfully")
