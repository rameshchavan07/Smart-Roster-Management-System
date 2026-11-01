"""SQLAlchemy 2.0 ORM models for rosters, shift entries, and conflicts.

Implements tables: roster_periods, roster_entries, roster_conflicts.
Strictly conforms to DATABASE_DESIGN.md §3 and SCHEDULING_ENGINE.md §7.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UUID

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.auth import User
    from app.models.core import BrandProcess, Employee


class RosterPeriodStatus(StrEnum):
    """Lifecycle state of a roster period."""

    GENERATING = "GENERATING"
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class RosterEntryStatus(StrEnum):
    """Daily operational status assigned to an employee."""

    WORK = "WORK"
    WEEKLY_OFF = "WEEKLY_OFF"
    HOLIDAY_OFF = "HOLIDAY_OFF"
    HOLIDAY_WORK = "HOLIDAY_WORK"
    LEAVE = "LEAVE"
    COMP_OFF = "COMP_OFF"


class EntrySource(StrEnum):
    """Origin of a roster assignment."""

    AUTO = "AUTO"
    MANUAL = "MANUAL"
    LOCKED_FIXED = "LOCKED_FIXED"


class ConflictSeverity(StrEnum):
    """Validation conflict severity classification."""

    BLOCKING = "BLOCKING"
    WARNING = "WARNING"
    INFO = "INFO"


class RosterPeriod(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Monthly roster version container."""

    __tablename__ = "roster_periods"
    __table_args__ = (
        UniqueConstraint("month", "version", name="uq_roster_periods_month_version"),
        Index("ix_roster_periods_month", "month"),
    )

    month: Mapped[date] = mapped_column(Date, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[RosterPeriodStatus] = mapped_column(
        Enum(RosterPeriodStatus, native_enum=False, validate_strings=True),
        default=RosterPeriodStatus.DRAFT,
        nullable=False,
    )
    solver_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    generation_params: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )
    parent_period_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        ForeignKey("roster_periods.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    creator: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[created_by_id],
        back_populates="created_periods",
    )
    parent_period: Mapped[RosterPeriod | None] = relationship(
        "RosterPeriod",
        remote_side="RosterPeriod.id",
        back_populates="child_periods",
    )
    child_periods: Mapped[list[RosterPeriod]] = relationship(
        "RosterPeriod",
        back_populates="parent_period",
    )
    entries: Mapped[list[RosterEntry]] = relationship(
        "RosterEntry",
        back_populates="roster_period",
        cascade="all, delete-orphan",
    )
    conflicts: Mapped[list[RosterConflict]] = relationship(
        "RosterConflict",
        back_populates="roster_period",
        cascade="all, delete-orphan",
    )


class RosterEntry(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Daily schedule assignment cell for an employee."""

    __tablename__ = "roster_entries"
    __table_args__ = (
        UniqueConstraint(
            "roster_period_id", "employee_id", "date", name="uq_roster_entry_period_emp_date"
        ),
        Index("ix_roster_entries_period_date", "roster_period_id", "date"),
        Index("ix_roster_entries_period_emp", "roster_period_id", "employee_id"),
    )

    roster_period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        ForeignKey("roster_periods.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    shift_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        nullable=True,
    )
    status: Mapped[RosterEntryStatus] = mapped_column(
        Enum(RosterEntryStatus, native_enum=False, validate_strings=True),
        nullable=False,
    )
    source: Mapped[EntrySource] = mapped_column(
        Enum(EntrySource, native_enum=False, validate_strings=True),
        default=EntrySource.AUTO,
        nullable=False,
    )
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    roster_period: Mapped[RosterPeriod] = relationship(
        "RosterPeriod",
        back_populates="entries",
    )
    employee: Mapped[Employee] = relationship(
        "Employee",
        foreign_keys=[employee_id],
    )


class RosterConflict(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Validation conflict or warning identified in a roster version."""

    __tablename__ = "roster_conflicts"
    __table_args__ = (Index("ix_roster_conflicts_period_severity", "roster_period_id", "severity"),)

    roster_period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        ForeignKey("roster_periods.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    severity: Mapped[ConflictSeverity] = mapped_column(
        Enum(ConflictSeverity, native_enum=False, validate_strings=True),
        nullable=False,
        index=True,
    )
    brand_process_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        ForeignKey("brand_processes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    date_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    root_causes: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    suggestions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    is_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    acknowledged_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    acknowledged_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    roster_period: Mapped[RosterPeriod] = relationship(
        "RosterPeriod",
        back_populates="conflicts",
    )
    brand_process: Mapped[BrandProcess | None] = relationship(
        "BrandProcess",
        foreign_keys=[brand_process_id],
    )
    employee: Mapped[Employee | None] = relationship(
        "Employee",
        foreign_keys=[employee_id],
    )
    acknowledged_by: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[acknowledged_by_id],
    )
