"""SQLAlchemy 2.0 ORM models for rules, availability, leaves, and holidays.

Implements tables: coverage_rules, holidays, leaves, comp_off_ledger, weekly_off_rules, employee_preferences.
Strictly conforms to DATABASE_DESIGN.md §3 and Alembic migration conventions.
"""

from __future__ import annotations

import uuid
from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Index,
    SmallInteger,
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
    from app.models.core import Brand, BrandProcess, Employee


class LeaveType(StrEnum):
    """Employee leave classification."""

    PLANNED = "PLANNED"
    SICK = "SICK"
    UNPAID = "UNPAID"
    COMP_OFF = "COMP_OFF"


class LeaveStatus(StrEnum):
    """Leave approval workflow status."""

    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class CompOffKind(StrEnum):
    """Comp-off ledger transaction type."""

    EARNED = "EARNED"
    REDEEMED = "REDEEMED"


class WeeklyOffMode(StrEnum):
    """Weekly off scheduling policy."""

    FIXED_MANDATORY = "FIXED_MANDATORY"
    FIXED_PREFERRED = "FIXED_PREFERRED"
    ROTATING = "ROTATING"
    ANY = "ANY"


class PreferenceKind(StrEnum):
    """Employee preference categories."""

    PREFERRED_OFF_WEEKDAY = "PREFERRED_OFF_WEEKDAY"
    PREFERRED_OFF_DATE = "PREFERRED_OFF_DATE"
    AVOID_WEEKEND_WORK = "AVOID_WEEKEND_WORK"


class CoverageRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Date or weekday coverage headcount rule for a brand-process."""

    __tablename__ = "coverage_rules"
    __table_args__ = (
        CheckConstraint(
            "((weekday IS NOT NULL AND specific_date IS NULL) OR (weekday IS NULL AND specific_date IS NOT NULL))",
            name="ck_coverage_rules_weekday_or_date",
        ),
        CheckConstraint(
            "(weekday IS NULL OR (weekday >= 0 AND weekday <= 6))",
            name="ck_coverage_rules_weekday_range",
        ),
        CheckConstraint("min_staff >= 0", name="ck_coverage_rules_min_staff_non_negative"),
    )

    brand_process_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        ForeignKey("brand_processes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    weekday: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)  # 0=Mon ... 6=Sun
    specific_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    min_staff: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    brand_process: Mapped[BrandProcess] = relationship(
        "BrandProcess",
        back_populates="coverage_rules",
    )


class Holiday(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Public holiday definition (global or brand-specific)."""

    __tablename__ = "holidays"
    __table_args__ = (UniqueConstraint("date", "brand_id", name="uq_holidays_date_brand"),)

    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        ForeignKey("brands.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    brand: Mapped[Brand | None] = relationship(
        "Brand",
        back_populates="holidays",
    )


class Leave(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Approved or requested employee leave duration."""

    __tablename__ = "leaves"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_leaves_date_range"),
        Index("ix_leaves_emp_dates_approved", "employee_id", "start_date", "end_date"),
    )

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    type: Mapped[LeaveType] = mapped_column(
        Enum(LeaveType, native_enum=False, validate_strings=True),
        default=LeaveType.PLANNED,
        nullable=False,
    )
    status: Mapped[LeaveStatus] = mapped_column(
        Enum(LeaveStatus, native_enum=False, validate_strings=True),
        default=LeaveStatus.REQUESTED,
        nullable=False,
        index=True,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    employee: Mapped[Employee] = relationship(
        "Employee",
        back_populates="leaves",
    )


class CompOffLedger(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Comp-off credit ledger tracking earned and redeemed credits."""

    __tablename__ = "comp_off_ledger"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    kind: Mapped[CompOffKind] = mapped_column(
        Enum(CompOffKind, native_enum=False, validate_strings=True),
        nullable=False,
    )
    source_roster_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False)
    expires_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    employee: Mapped[Employee] = relationship(
        "Employee",
        back_populates="comp_off_entries",
    )


class WeeklyOffRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Employee weekly off allocation rules and mandatory/preferred weekdays."""

    __tablename__ = "weekly_off_rules"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mode: Mapped[WeeklyOffMode] = mapped_column(
        Enum(WeeklyOffMode, native_enum=False, validate_strings=True),
        default=WeeklyOffMode.ANY,
        nullable=False,
    )
    weekdays: Mapped[list[int]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=list,
        nullable=False,
    )
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Relationships
    employee: Mapped[Employee] = relationship(
        "Employee",
        back_populates="weekly_off_rules",
    )


class EmployeePreference(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Soft scheduling preferences stated by employees."""

    __tablename__ = "employee_preferences"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[PreferenceKind] = mapped_column(
        Enum(PreferenceKind, native_enum=False, validate_strings=True),
        nullable=False,
    )
    value: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
    )
    weight: Mapped[int] = mapped_column(SmallInteger, default=5, nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Relationships
    employee: Mapped[Employee] = relationship(
        "Employee",
        back_populates="preferences",
    )
