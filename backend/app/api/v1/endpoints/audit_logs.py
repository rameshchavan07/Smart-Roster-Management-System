"""Audit log query endpoints.

Conforms to API_DOCUMENTATION.md §3 and SECURITY.md §2.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_pod_lead_or_manager
from app.models.auth import User
from app.schemas.auth import AuditLogRead
from app.schemas.common import PaginatedResponse
from app.services.audit import AuditLogService

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get(
    "",
    response_model=PaginatedResponse[AuditLogRead],
    summary="Query audit log entries",
    description="Retrieve paginated audit entries tracking data mutations and user actions with flexible filtering. Pod Lead or Ops Manager.",
)
def list_audit_logs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_pod_lead_or_manager)],
    action: Annotated[str | None, Query(description="Filter by action name")] = None,
    entity_type: Annotated[str | None, Query(description="Filter by entity type")] = None,
    entity_id: Annotated[str | None, Query(description="Filter by entity ID")] = None,
    user_id: Annotated[uuid.UUID | None, Query(description="Filter by actor user UUID")] = None,
    date_from: Annotated[
        dt.date | None, Query(description="Filter events created on or after date")
    ] = None,
    date_to: Annotated[
        dt.date | None, Query(description="Filter events created on or before date")
    ] = None,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
    limit: Annotated[int, Query(ge=1, le=200, description="Page limit")] = 50,
) -> PaginatedResponse[AuditLogRead]:
    """List system audit log records."""
    service = AuditLogService(db)
    return service.list_audit_logs(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        offset=offset,
        limit=limit,
    )
