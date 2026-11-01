"""SQLAlchemy 2.0 Core ORM models for master data.

Implements tables: pods, employees, processes, brands, brand_processes, assignments.
Strictly conforms to DATABASE_DESIGN.md §3 and Alembic migration conventions.
"""

from __future__ import annotations

import uuid
from datetime import date
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    Date,
    Enum,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UUID

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class CalendarType(StrEnum):
    """Brand operating calendar types."""

    ALL_365 = "ALL_365"
    ALL_EXCEPT_HOLIDAYS = "ALL_EXCEPT_HOLIDAYS"
    EXCLUDE_SUNDAY_AND_HOLIDAYS = "EXCLUDE_SUNDAY_AND_HOLIDAYS"


class AssignmentType(StrEnum):
    """Staffing assignment types."""

    PRIMARY = "PRIMARY"
    BACKUP = "BACKUP"


class Pod(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Operational pod grouping employees and owning default brands."""

    __tablename__ = "pods"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    lead_employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        ForeignKey(
            "employees.id", use_alter=True, name="fk_pods_lead_employee_id", ondelete="SET NULL"
        ),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    members: Mapped[list[Employee]] = relationship(
        "Employee",
        foreign_keys="[Employee.pod_id]",
        back_populates="pod",
        cascade="all, delete-orphan",
    )
    lead: Mapped[Employee | None] = relationship(
        "Employee",
        foreign_keys=[lead_employee_id],
        post_update=True,
    )
    brands: Mapped[list[Brand]] = relationship(
        "Brand",
        back_populates="pod",
    )


class Employee(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Individual worker assigned to pods and brand-processes."""

    __tablename__ = "employees"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    pod_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        ForeignKey("pods.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    is_floater: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    weekly_off_count: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    max_consecutive_days: Mapped[int] = mapped_column(SmallInteger, default=6, nullable=False)
    max_concurrent_processes: Mapped[int] = mapped_column(SmallInteger, default=3, nullable=False)
    joined_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    left_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    pod: Mapped[Pod] = relationship(
        "Pod",
        foreign_keys=[pod_id],
        back_populates="members",
    )
    assignments: Mapped[list[Assignment]] = relationship(
        "Assignment",
        back_populates="employee",
        cascade="all, delete-orphan",
    )


class Process(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Operational capability definition (CS, ACC, RET, NDR)."""

    __tablename__ = "processes"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    brand_processes: Mapped[list[BrandProcess]] = relationship(
        "BrandProcess",
        back_populates="process",
        cascade="all, delete-orphan",
    )


class Brand(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """D2C brand with assigned default pod."""

    __tablename__ = "brands"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    pod_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        ForeignKey("pods.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    pod: Mapped[Pod | None] = relationship(
        "Pod",
        back_populates="brands",
    )
    brand_processes: Mapped[list[BrandProcess]] = relationship(
        "BrandProcess",
        back_populates="brand",
        cascade="all, delete-orphan",
    )


class BrandProcess(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Process instantiated for a specific brand with calendar and coverage rules."""

    __tablename__ = "brand_processes"
    __table_args__ = (UniqueConstraint("brand_id", "process_id", name="uq_brand_process"),)

    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        ForeignKey("brands.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    process_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        ForeignKey("processes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    calendar_type: Mapped[CalendarType] = mapped_column(
        Enum(CalendarType, native_enum=False, validate_strings=True),
        default=CalendarType.ALL_EXCEPT_HOLIDAYS,
        nullable=False,
    )
    min_coverage_default: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    brand: Mapped[Brand] = relationship(
        "Brand",
        back_populates="brand_processes",
    )
    process: Mapped[Process] = relationship(
        "Process",
        back_populates="brand_processes",
    )
    assignments: Mapped[list[Assignment]] = relationship(
        "Assignment",
        back_populates="brand_process",
        cascade="all, delete-orphan",
    )


class Assignment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Dated staffing assignment connecting an employee to a brand-process."""

    __tablename__ = "assignments"
    __table_args__ = (
        UniqueConstraint(
            "employee_id", "brand_process_id", "valid_from", name="uq_employee_bp_valid_from"
        ),
    )

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    brand_process_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True).with_variant(PG_UUID(as_uuid=True), "postgresql"),
        ForeignKey("brand_processes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[AssignmentType] = mapped_column(
        Enum(AssignmentType, native_enum=False, validate_strings=True),
        default=AssignmentType.PRIMARY,
        nullable=False,
    )
    allocation_pct: Mapped[int | None] = mapped_column(SmallInteger, default=100, nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Relationships
    employee: Mapped[Employee] = relationship(
        "Employee",
        back_populates="assignments",
    )
    brand_process: Mapped[BrandProcess] = relationship(
        "BrandProcess",
        back_populates="assignments",
    )
