"""Master data endpoints for Brand-Processes (instantiated capabilities)."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    check_pod_scope,
    get_current_user,
    get_db,
    require_ops_manager,
    require_pod_lead_or_manager,
)
from app.models.auth import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.core import (
    BrandProcessCreate,
    BrandProcessRead,
    BrandProcessUpdate,
)
from app.services.master_data import BrandProcessService, BrandService

router = APIRouter(prefix="/brand-processes", tags=["BrandProcesses"])


def _to_bp_read(bp: Any) -> BrandProcessRead:
    res = BrandProcessRead.model_validate(bp)
    if hasattr(bp, "brand") and bp.brand is not None:
        res.brand_name = bp.brand.name
        res.brand_code = bp.brand.code
    if hasattr(bp, "process") and bp.process is not None:
        res.process_name = bp.process.name
        res.process_code = bp.process.code
    return res


@router.get("", response_model=PaginatedResponse[BrandProcessRead])
def list_brand_processes(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    brand_id: uuid.UUID | None = None,
    process_id: uuid.UUID | None = None,
    is_active: bool | None = None,
) -> PaginatedResponse[BrandProcessRead]:
    """List brand-process configurations with optional filters."""
    service = BrandProcessService(db)
    items, total = service.list_brand_processes(
        offset=offset,
        limit=limit,
        brand_id=brand_id,
        process_id=process_id,
        is_active=is_active,
    )
    read_items = [_to_bp_read(item) for item in items]
    return PaginatedResponse[BrandProcessRead](
        items=read_items, total=total, limit=limit, offset=offset
    )


@router.post("", response_model=BrandProcessRead, status_code=status.HTTP_201_CREATED)
def create_brand_process(
    data: BrandProcessCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_pod_lead_or_manager)],
) -> BrandProcessRead:
    """Instantiate a process for a brand."""
    brand_service = BrandService(db)
    brand = brand_service.get_brand(data.brand_id)
    if brand.pod_id is not None:
        check_pod_scope(current_user, brand.pod_id, db)

    service = BrandProcessService(db)
    bp = service.create_brand_process(data, actor_id=current_user.id)
    db.commit()
    db.refresh(bp)
    return _to_bp_read(bp)


@router.get("/{bp_id}", response_model=BrandProcessRead)
def get_brand_process(
    bp_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BrandProcessRead:
    """Get brand-process configuration by ID."""
    service = BrandProcessService(db)
    bp = service.get_brand_process(bp_id)
    return _to_bp_read(bp)


@router.put("/{bp_id}", response_model=BrandProcessRead)
def update_brand_process(
    bp_id: uuid.UUID,
    data: BrandProcessUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_pod_lead_or_manager)],
) -> BrandProcessRead:
    """Update brand-process configuration (e.g. calendar_type, min_coverage)."""
    service = BrandProcessService(db)
    bp = service.get_brand_process(bp_id)
    if bp.brand and bp.brand.pod_id is not None:
        check_pod_scope(current_user, bp.brand.pod_id, db)

    updated_bp = service.update_brand_process(bp_id, data, actor_id=current_user.id)
    db.commit()
    db.refresh(updated_bp)
    return _to_bp_read(updated_bp)


@router.delete("/{bp_id}", response_model=MessageResponse)
def delete_brand_process(
    bp_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_ops_manager)],
) -> MessageResponse:
    """Delete a brand-process if no staff assignments or coverage rules exist (Ops Manager only)."""
    service = BrandProcessService(db)
    service.delete_brand_process(bp_id, actor_id=current_user.id)
    db.commit()
    return MessageResponse(message=f"BrandProcess '{bp_id}' deleted successfully")
