"""Generic SQLAlchemy 2.0 repository base class."""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.db.base import Base


class BaseRepository[ModelType: Base]:
    """Generic base repository providing CRUD and pagination operations."""

    def __init__(self, model: type[ModelType], session: Session) -> None:
        self.model = model
        self.session = session

    def get_by_id(self, entity_id: uuid.UUID) -> ModelType | None:
        """Fetch a single record by its UUID primary key."""
        return self.session.get(self.model, entity_id)

    def list(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        is_active: bool | None = None,
        query_modifier: Any | None = None,
    ) -> tuple[Sequence[ModelType], int]:
        """Fetch a paginated list of records and the total matching count."""
        stmt: Select[Any] = select(self.model)

        if is_active is not None and hasattr(self.model, "is_active"):
            is_active_col = getattr(self.model, "is_active")  # noqa: B009
            stmt = stmt.where(is_active_col == is_active)

        if query_modifier is not None:
            stmt = query_modifier(stmt)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.session.scalar(count_stmt) or 0

        paged_stmt = stmt.offset(offset).limit(limit)
        items = self.session.scalars(paged_stmt).all()

        return items, total

    def create(self, entity: ModelType) -> ModelType:
        """Persist a new entity and flush."""
        self.session.add(entity)
        self.session.flush()
        return entity

    def update(self, entity: ModelType) -> ModelType:
        """Merge/update an entity and flush."""
        self.session.flush()
        return entity

    def delete(self, entity: ModelType) -> None:
        """Delete an entity from the database."""
        self.session.delete(entity)
        self.session.flush()
