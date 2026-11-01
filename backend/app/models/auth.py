"""SQLAlchemy 2.0 ORM models for authentication, users, and audit logs.

Implements tables: users, audit_logs.
Conforms to DATABASE_DESIGN.md §3 and SECURITY.md §2.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UUID

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.core import Employee
    from app.models.roster import RosterPeriod


class UserRole(StrEnum):
    """RBAC role tiers per SECURITY.md §2."""

    OPS_MANAGER = "OPS_MANAGER"
    POD_LEAD = "POD_LEAD"
    EMPLOYEE = "EMPLOYEE"


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Application user account with RBAC role."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, validate_strings=True),
        default=UserRole.EMPLOYEE,
        nullable=False,
    )
    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        ForeignKey("employees.id", ondelete="SET NULL"),
        unique=True,
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    employee: Mapped[Employee | None] = relationship("Employee", foreign_keys=[employee_id])
    audit_logs: Mapped[list[AuditLog]] = relationship("AuditLog", back_populates="user")
    created_periods: Mapped[list[RosterPeriod]] = relationship(
        "RosterPeriod",
        back_populates="creator",
        foreign_keys="[RosterPeriod.created_by_id]",
    )


class AuditLog(Base, UUIDPrimaryKeyMixin):
    """Immutable audit entry tracking data mutations and user actions."""

    __tablename__ = "audit_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    before: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    after: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped[User | None] = relationship("User", back_populates="audit_logs")

    @property
    def user_email(self) -> str | None:
        """Convenience property for user's email address."""
        return self.user.email if self.user else None
