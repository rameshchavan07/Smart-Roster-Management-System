"""Master data endpoints for Brands."""

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
from app.schemas.core import BrandCreate, BrandRead, BrandUpdate
from app.services.master_data import BrandService

router = APIRouter(prefix="/brands", tags=["Brands"])


def _to_brand_read(brand: Any) -> BrandRead:
    res = BrandRead.model_validate(brand)
    if hasattr(brand, "pod") and brand.pod is not None:
        res.pod_name = brand.pod.name
    return res


@router.get("", response_model=PaginatedResponse[BrandRead])
def list_brands(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    pod_id: uuid.UUID | None = None,
    is_active: bool | None = None,
) -> PaginatedResponse[BrandRead]:
    """List brands with pagination and optional filters."""
    service = BrandService(db)
    items, total = service.list_brands(
        offset=offset, limit=limit, pod_id=pod_id, is_active=is_active
    )
    read_items = [_to_brand_read(item) for item in items]
    return PaginatedResponse[BrandRead](items=read_items, total=total, limit=limit, offset=offset)


@router.post("", response_model=BrandRead, status_code=status.HTTP_201_CREATED)
def create_brand(
    data: BrandCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_pod_lead_or_manager)],
) -> BrandRead:
    """Create a new brand."""
    if data.pod_id is not None:
        check_pod_scope(current_user, data.pod_id, db)
    service = BrandService(db)
    brand = service.create_brand(data, actor_id=current_user.id)
    db.commit()
    db.refresh(brand)
    return _to_brand_read(brand)


@router.get("/{brand_id}", response_model=BrandRead)
def get_brand(
    brand_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BrandRead:
    """Get brand by ID."""
    service = BrandService(db)
    brand = service.get_brand(brand_id)
    return _to_brand_read(brand)


@router.put("/{brand_id}", response_model=BrandRead)
def update_brand(
    brand_id: uuid.UUID,
    data: BrandUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_pod_lead_or_manager)],
) -> BrandRead:
    """Update brand details."""
    service = BrandService(db)
    existing_brand = service.get_brand(brand_id)
    if existing_brand.pod_id is not None:
        check_pod_scope(current_user, existing_brand.pod_id, db)
    if data.pod_id is not None:
        check_pod_scope(current_user, data.pod_id, db)

    brand = service.update_brand(brand_id, data, actor_id=current_user.id)
    db.commit()
    db.refresh(brand)
    return _to_brand_read(brand)


@router.delete("/{brand_id}", response_model=MessageResponse)
def delete_brand(
    brand_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_ops_manager)],
) -> MessageResponse:
    """Delete a brand if no processes are configured for it (Ops Manager only)."""
    service = BrandService(db)
    service.delete_brand(brand_id, actor_id=current_user.id)
    db.commit()
    return MessageResponse(message=f"Brand '{brand_id}' deleted successfully")
