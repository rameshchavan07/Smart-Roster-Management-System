"""Comp-off ledger and redemption REST endpoints."""

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
from app.schemas.common import PaginatedResponse
from app.schemas.rules import (
    CompOffBalanceRead,
    CompOffLedgerCreate,
    CompOffLedgerRead,
    CompOffRedeemRequest,
)
from app.services.rules import CompOffService

router = APIRouter(prefix="/comp-offs", tags=["CompOffs"])


@router.get("/balance", response_model=CompOffBalanceRead)
def get_comp_off_balance(
    employee_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CompOffBalanceRead:
    """Get earned, redeemed, and available comp-off balances for an employee."""
    check_employee_scope(current_user, employee_id, db)
    service = CompOffService(db)
    return service.get_balance(employee_id)


@router.get("", response_model=PaginatedResponse[CompOffLedgerRead])
def list_comp_off_entries(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    employee_id: uuid.UUID | None = None,
) -> PaginatedResponse[CompOffLedgerRead]:
    """List comp-off ledger transactions."""
    if current_user.role == UserRole.EMPLOYEE:
        if employee_id is not None and employee_id != current_user.employee_id:
            raise ForbiddenError("Employees can only view their own comp-offs")
        employee_id = current_user.employee_id
    elif employee_id is not None:
        check_employee_scope(current_user, employee_id, db)

    service = CompOffService(db)
    items, total = service.list_entries(offset=offset, limit=limit, employee_id=employee_id)
    read_items = [CompOffLedgerRead.model_validate(item) for item in items]
    return PaginatedResponse[CompOffLedgerRead](
        items=read_items, total=total, limit=limit, offset=offset
    )


@router.post("", response_model=CompOffLedgerRead, status_code=status.HTTP_201_CREATED)
def credit_comp_off(
    data: CompOffLedgerCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_pod_lead_or_manager)],
) -> CompOffLedgerRead:
    """Manually record a comp-off credit or deduction entry."""
    check_employee_scope(current_user, data.employee_id, db)
    service = CompOffService(db)
    entry = service.create_entry(data)
    db.commit()
    db.refresh(entry)
    return CompOffLedgerRead.model_validate(entry)


@router.post("/redeem", response_model=CompOffLedgerRead, status_code=status.HTTP_201_CREATED)
def redeem_comp_off(
    data: CompOffRedeemRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CompOffLedgerRead:
    """Redeem an available comp-off credit for a specific date (creates approved COMP_OFF leave)."""
    check_employee_scope(current_user, data.employee_id, db)
    service = CompOffService(db)
    entry = service.redeem_compoff(data)
    db.commit()
    db.refresh(entry)
    return CompOffLedgerRead.model_validate(entry)
