"""Coverage rules REST endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    check_pod_scope,
    get_current_user,
    get_db,
    require_pod_lead_or_manager,
)
from app.models.auth import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.rules import (
    CoverageRuleCreate,
    CoverageRuleRead,
    CoverageRuleUpdate,
)
from app.services.master_data import BrandProcessService
from app.services.rules import CoverageRuleService

router = APIRouter(prefix="/coverage-rules", tags=["CoverageRules"])


def _check_bp_pod_scope(user: User, bp_id: uuid.UUID, db: Session) -> None:
    bp_service = BrandProcessService(db)
    bp = bp_service.get_brand_process(bp_id)
    if bp.brand and bp.brand.pod_id is not None:
        check_pod_scope(user, bp.brand.pod_id, db)


@router.get("", response_model=PaginatedResponse[CoverageRuleRead])
def list_coverage_rules(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    brand_process_id: uuid.UUID | None = None,
    is_active: bool | None = None,
) -> PaginatedResponse[CoverageRuleRead]:
    """List coverage rules with optional brand_process filter."""
    service = CoverageRuleService(db)
    items, total = service.list_coverage_rules(
        offset=offset,
        limit=limit,
        brand_process_id=brand_process_id,
        is_active=is_active,
    )
    read_items = [CoverageRuleRead.model_validate(item) for item in items]
    return PaginatedResponse[CoverageRuleRead](
        items=read_items, total=total, limit=limit, offset=offset
    )


@router.post("", response_model=CoverageRuleRead, status_code=status.HTTP_201_CREATED)
def create_coverage_rule(
    data: CoverageRuleCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_pod_lead_or_manager)],
) -> CoverageRuleRead:
    """Create a new coverage requirement rule."""
    _check_bp_pod_scope(current_user, data.brand_process_id, db)
    service = CoverageRuleService(db)
    rule = service.create_coverage_rule(data)
    db.commit()
    db.refresh(rule)
    return CoverageRuleRead.model_validate(rule)


@router.get("/{rule_id}", response_model=CoverageRuleRead)
def get_coverage_rule(
    rule_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CoverageRuleRead:
    """Get coverage rule by ID."""
    service = CoverageRuleService(db)
    rule = service.get_coverage_rule(rule_id)
    return CoverageRuleRead.model_validate(rule)


@router.put("/{rule_id}", response_model=CoverageRuleRead)
def update_coverage_rule(
    rule_id: uuid.UUID,
    data: CoverageRuleUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_pod_lead_or_manager)],
) -> CoverageRuleRead:
    """Update coverage rule attributes."""
    service = CoverageRuleService(db)
    rule = service.get_coverage_rule(rule_id)
    _check_bp_pod_scope(current_user, rule.brand_process_id, db)

    updated_rule = service.update_coverage_rule(rule_id, data)
    db.commit()
    db.refresh(updated_rule)
    return CoverageRuleRead.model_validate(updated_rule)


@router.delete("/{rule_id}", response_model=MessageResponse)
def delete_coverage_rule(
    rule_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_pod_lead_or_manager)],
) -> MessageResponse:
    """Delete a coverage rule."""
    service = CoverageRuleService(db)
    rule = service.get_coverage_rule(rule_id)
    _check_bp_pod_scope(current_user, rule.brand_process_id, db)

    service.delete_coverage_rule(rule_id)
    db.commit()
    return MessageResponse(message=f"CoverageRule '{rule_id}' deleted successfully")
