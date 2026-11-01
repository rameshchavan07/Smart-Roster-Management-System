"""Master data endpoints for Brands."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
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
) -> BrandRead:
    """Create a new brand."""
    service = BrandService(db)
    brand = service.create_brand(data)
    db.commit()
    db.refresh(brand)
    return _to_brand_read(brand)


@router.get("/{brand_id}", response_model=BrandRead)
def get_brand(
    brand_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
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
) -> BrandRead:
    """Update brand details."""
    service = BrandService(db)
    brand = service.update_brand(brand_id, data)
    db.commit()
    db.refresh(brand)
    return _to_brand_read(brand)


@router.delete("/{brand_id}", response_model=MessageResponse)
def delete_brand(
    brand_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    """Delete a brand if no processes are configured for it."""
    service = BrandService(db)
    service.delete_brand(brand_id)
    db.commit()
    return MessageResponse(message=f"Brand '{brand_id}' deleted successfully")
