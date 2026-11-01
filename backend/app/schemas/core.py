"""Pydantic v2 schemas for core master data entities.

Covers pods, employees, processes, brands, brand_processes, and assignments.
Conforms to DATABASE_DESIGN.md §3 and API_DOCUMENTATION.md §4.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.core import AssignmentType, CalendarType
from app.schemas.common import EMAIL_REGEX


# -----------------------------------------------------------------------------
# Pod Schemas
# -----------------------------------------------------------------------------
class PodBase(BaseModel):
    name: str = Field(min_length=1, max_length=100, description="Pod identifier name")


class PodCreate(PodBase):
    lead_employee_id: uuid.UUID | None = None


class PodUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    lead_employee_id: uuid.UUID | None = None
    is_active: bool | None = None


class PodRead(PodBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lead_employee_id: uuid.UUID | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    member_count: int | None = None


# -----------------------------------------------------------------------------
# Process Schemas
# -----------------------------------------------------------------------------
class ProcessBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=50)
    description: str | None = None


class ProcessCreate(ProcessBase):
    pass


class ProcessUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    code: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = None
    is_active: bool | None = None


class ProcessRead(ProcessBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


# -----------------------------------------------------------------------------
# Brand Schemas
# -----------------------------------------------------------------------------
class BrandBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=50)
    pod_id: uuid.UUID | None = None


class BrandCreate(BrandBase):
    pass


class BrandUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    code: str | None = Field(default=None, min_length=1, max_length=50)
    pod_id: uuid.UUID | None = None
    is_active: bool | None = None


class BrandRead(BrandBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    pod_name: str | None = None


# -----------------------------------------------------------------------------
# Employee Schemas
# -----------------------------------------------------------------------------
class EmployeeBase(BaseModel):
    code: str = Field(min_length=1, max_length=50, description="e.g. EMP-001")
    full_name: str = Field(min_length=1, max_length=255)
    email: str | None = Field(default=None, pattern=EMAIL_REGEX, max_length=255)
    pod_id: uuid.UUID
    is_floater: bool = False
    weekly_off_count: int = Field(default=1, ge=0, le=7)
    max_consecutive_days: int = Field(default=6, ge=1, le=14)
    max_concurrent_processes: int = Field(default=3, ge=1, le=10)
    joined_on: date | None = None
    left_on: date | None = None


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: str | None = Field(default=None, pattern=EMAIL_REGEX, max_length=255)
    pod_id: uuid.UUID | None = None
    is_floater: bool | None = None
    weekly_off_count: int | None = Field(default=None, ge=0, le=7)
    max_consecutive_days: int | None = Field(default=None, ge=1, le=14)
    max_concurrent_processes: int | None = Field(default=None, ge=1, le=10)
    joined_on: date | None = None
    left_on: date | None = None
    is_active: bool | None = None


class EmployeeRead(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    pod_name: str | None = None


# -----------------------------------------------------------------------------
# BrandProcess Schemas
# -----------------------------------------------------------------------------
class BrandProcessBase(BaseModel):
    brand_id: uuid.UUID
    process_id: uuid.UUID
    calendar_type: CalendarType = CalendarType.ALL_365
    min_coverage_default: int = Field(default=1, ge=0)
    valid_from: date | None = None
    valid_to: date | None = None


class BrandProcessCreate(BrandProcessBase):
    pass


class BrandProcessUpdate(BaseModel):
    calendar_type: CalendarType | None = None
    min_coverage_default: int | None = Field(default=None, ge=0)
    valid_from: date | None = None
    valid_to: date | None = None
    is_active: bool | None = None


class BrandProcessRead(BrandProcessBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    brand_name: str | None = None
    brand_code: str | None = None
    process_name: str | None = None
    process_code: str | None = None


# -----------------------------------------------------------------------------
# Assignment Schemas
# -----------------------------------------------------------------------------
class AssignmentBase(BaseModel):
    employee_id: uuid.UUID
    brand_process_id: uuid.UUID
    type: AssignmentType = AssignmentType.PRIMARY
    allocation_pct: int | None = Field(default=None, ge=0, le=100)
    valid_from: date | None = None
    valid_to: date | None = None


class AssignmentCreate(AssignmentBase):
    pass


class AssignmentUpdate(BaseModel):
    type: AssignmentType | None = None
    allocation_pct: int | None = Field(default=None, ge=0, le=100)
    valid_from: date | None = None
    valid_to: date | None = None


class AssignmentRead(AssignmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    employee_name: str | None = None
    employee_code: str | None = None
