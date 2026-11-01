"""Audit log query service.

Conforms to API_DOCUMENTATION.md §3 and AGENTS.md architecture rules (services layer).
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy.orm import Session

from app.repositories.core import AuditLogRepository
from app.schemas.auth import AuditLogRead
from app.schemas.common import PaginatedResponse


class AuditLogService:
    """Service for querying system and data audit logs."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = AuditLogRepository(session)

    def list_audit_logs(
        self,
        *,
        action: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        user_id: uuid.UUID | None = None,
        date_from: dt.datetime | dt.date | None = None,
        date_to: dt.datetime | dt.date | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> PaginatedResponse[AuditLogRead]:
        """Query paginated audit logs with optional filters."""
        items, total = self.repo.list_audit_logs(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
            offset=offset,
            limit=limit,
        )
        return PaginatedResponse[AuditLogRead](
            items=[AuditLogRead.model_validate(log) for log in items],
            total=total,
            offset=offset,
            limit=limit,
        )
