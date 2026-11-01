"""Master data endpoints for Pods."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.core import PodCreate, PodRead, PodUpdate
from app.services.master_data import PodService

router = APIRouter(prefix="/pods", tags=["Pods"])


def _to_pod_read(pod: Any) -> PodRead:
    res = PodRead.model_validate(pod)
    if hasattr(pod, "members") and pod.members is not None:
        res.member_count = len(pod.members)
    return res


@router.get("", response_model=PaginatedResponse[PodRead])
def list_pods(
    db: Annotated[Session, Depends(get_db)],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    is_active: bool | None = None,
) -> PaginatedResponse[PodRead]:
    """List pods with pagination and optional active filter."""
    service = PodService(db)
    items, total = service.list_pods(offset=offset, limit=limit, is_active=is_active)
    read_items = [_to_pod_read(item) for item in items]
    return PaginatedResponse[PodRead](items=read_items, total=total, limit=limit, offset=offset)


@router.post("", response_model=PodRead, status_code=status.HTTP_201_CREATED)
def create_pod(
    data: PodCreate,
    db: Annotated[Session, Depends(get_db)],
) -> PodRead:
    """Create a new pod."""
    service = PodService(db)
    pod = service.create_pod(data)
    db.commit()
    db.refresh(pod)
    return _to_pod_read(pod)


@router.get("/{pod_id}", response_model=PodRead)
def get_pod(
    pod_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> PodRead:
    """Get pod details by ID."""
    service = PodService(db)
    pod = service.get_pod(pod_id)
    return _to_pod_read(pod)


@router.put("/{pod_id}", response_model=PodRead)
def update_pod(
    pod_id: uuid.UUID,
    data: PodUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> PodRead:
    """Update pod details."""
    service = PodService(db)
    pod = service.update_pod(pod_id, data)
    db.commit()
    db.refresh(pod)
    return _to_pod_read(pod)


@router.delete("/{pod_id}", response_model=MessageResponse)
def delete_pod(
    pod_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    """Delete a pod if it has no associated members or brands."""
    service = PodService(db)
    service.delete_pod(pod_id)
    db.commit()
    return MessageResponse(message=f"Pod '{pod_id}' deleted successfully")
