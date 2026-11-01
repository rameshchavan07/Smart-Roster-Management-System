"""Master data endpoints for Processes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_ops_manager
from app.models.auth import User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.core import ProcessCreate, ProcessRead, ProcessUpdate
from app.services.master_data import ProcessService

router = APIRouter(prefix="/processes", tags=["Processes"])


@router.get("", response_model=PaginatedResponse[ProcessRead])
def list_processes(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    is_active: bool | None = None,
) -> PaginatedResponse[ProcessRead]:
    """List operational processes with pagination."""
    service = ProcessService(db)
    items, total = service.list_processes(offset=offset, limit=limit, is_active=is_active)
    read_items = [ProcessRead.model_validate(item) for item in items]
    return PaginatedResponse[ProcessRead](items=read_items, total=total, limit=limit, offset=offset)


@router.post("", response_model=ProcessRead, status_code=status.HTTP_201_CREATED)
def create_process(
    data: ProcessCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_ops_manager)],
) -> ProcessRead:
    """Create a new process (Ops Manager only)."""
    service = ProcessService(db)
    proc = service.create_process(data, actor_id=current_user.id)
    db.commit()
    db.refresh(proc)
    return ProcessRead.model_validate(proc)


@router.get("/{process_id}", response_model=ProcessRead)
def get_process(
    process_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProcessRead:
    """Get process by ID."""
    service = ProcessService(db)
    proc = service.get_process(process_id)
    return ProcessRead.model_validate(proc)


@router.put("/{process_id}", response_model=ProcessRead)
def update_process(
    process_id: uuid.UUID,
    data: ProcessUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_ops_manager)],
) -> ProcessRead:
    """Update process details (Ops Manager only)."""
    service = ProcessService(db)
    proc = service.update_process(process_id, data, actor_id=current_user.id)
    db.commit()
    db.refresh(proc)
    return ProcessRead.model_validate(proc)


@router.delete("/{process_id}", response_model=MessageResponse)
def delete_process(
    process_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_ops_manager)],
) -> MessageResponse:
    """Delete a process if not associated with active brands (Ops Manager only)."""
    service = ProcessService(db)
    service.delete_process(process_id, actor_id=current_user.id)
    db.commit()
    return MessageResponse(message=f"Process '{process_id}' deleted successfully")
