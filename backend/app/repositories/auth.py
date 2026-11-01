"""Repository for User accounts."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.auth import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Data access repository for User entities."""

    def __init__(self, session: Session) -> None:
        super().__init__(User, session)

    def get_by_email(self, email: str) -> User | None:
        """Find user by email address."""
        stmt = select(User).where(User.email == email)
        return self.session.scalars(stmt).first()

    def get_by_employee_id(self, employee_id: uuid.UUID) -> User | None:
        """Find user account linked to an employee."""
        stmt = select(User).where(User.employee_id == employee_id)
        return self.session.scalars(stmt).first()
