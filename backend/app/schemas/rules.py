"""Pydantic v2 schemas for rules, availability, leaves, comp-off, and preferences.

Conforms to DATABASE_DESIGN.md §3 and SCHEDULING_ENGINE.md §§3–4.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.rules import (
    CompOffKind,
    LeaveStatus,
    LeaveType,
    PreferenceKind,
    WeeklyOffMode,
)


# -----------------------------------------------------------------------------
# CoverageRule Schemas
# -----------------------------------------------------------------------------
class CoverageRuleBase(BaseModel):
    brand_process_id: uuid.UUID
    weekday: int | None = Field(default=None, ge=0, le=6, description="0=Mon, 6=Sun")
    specific_date: dt.date | None = Field(default=None, description="One-off date override")
    min_staff: int = Field(default=1, ge=0, description="Minimum staff required")
    reason: str | None = None

    @model_validator(mode="after")
    def validate_weekday_or_date(self) -> CoverageRuleBase:
        has_weekday = self.weekday is not None
        has_date = self.specific_date is not None
        if has_weekday == has_date:
            raise ValueError("Exactly one of 'weekday' or 'specific_date' must be provided.")
        return self


class CoverageRuleCreate(CoverageRuleBase):
    pass


class CoverageRuleUpdate(BaseModel):
    weekday: int | None = Field(default=None, ge=0, le=6)
    specific_date: dt.date | None = None
    min_staff: int | None = Field(default=None, ge=0)
    reason: str | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_weekday_or_date_update(self) -> CoverageRuleUpdate:
        if self.weekday is not None and self.specific_date is not None:
            raise ValueError("Cannot set both 'weekday' and 'specific_date'.")
        return self


class CoverageRuleRead(CoverageRuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    created_at: dt.datetime
    updated_at: dt.datetime


# -----------------------------------------------------------------------------
# Holiday Schemas
# -----------------------------------------------------------------------------
class HolidayBase(BaseModel):
    date: dt.date
    name: str = Field(min_length=1, max_length=255)
    brand_id: uuid.UUID | None = Field(default=None, description="Null for global holiday")


class HolidayCreate(HolidayBase):
    pass


class HolidayUpdate(BaseModel):
    date: dt.date | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    brand_id: uuid.UUID | None = None
    is_active: bool | None = None


class HolidayRead(HolidayBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    created_at: dt.datetime
    updated_at: dt.datetime
    brand_name: str | None = None


# -----------------------------------------------------------------------------
# Leave Schemas
# -----------------------------------------------------------------------------
class LeaveBase(BaseModel):
    employee_id: uuid.UUID
    start_date: dt.date
    end_date: dt.date
    type: LeaveType = LeaveType.PLANNED
    note: str | None = None

    @model_validator(mode="after")
    def validate_date_range(self) -> LeaveBase:
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date.")
        return self


class LeaveCreate(LeaveBase):
    status: LeaveStatus = LeaveStatus.REQUESTED


class LeaveUpdate(BaseModel):
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    type: LeaveType | None = None
    note: str | None = None

    @model_validator(mode="after")
    def validate_date_range_update(self) -> LeaveUpdate:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date.")
        return self


class LeaveStatusUpdate(BaseModel):
    status: LeaveStatus


class LeaveRead(LeaveBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: LeaveStatus
    created_at: dt.datetime
    updated_at: dt.datetime
    employee_name: str | None = None
    employee_code: str | None = None


class LeaveImpactResponse(BaseModel):
    leave: LeaveRead
    affected_roster_periods: list[str] = Field(default_factory=list)
    conflicts_generated: int = 0


# -----------------------------------------------------------------------------
# Comp-off Schemas
# -----------------------------------------------------------------------------
class CompOffLedgerBase(BaseModel):
    employee_id: uuid.UUID
    entry_date: dt.date
    kind: CompOffKind
    source_roster_entry_id: uuid.UUID | None = None
    status: str = "CONFIRMED"
    expires_on: dt.date | None = None
    note: str | None = None


class CompOffLedgerCreate(CompOffLedgerBase):
    pass


class CompOffLedgerRead(CompOffLedgerBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: dt.datetime
    updated_at: dt.datetime


class CompOffBalanceRead(BaseModel):
    employee_id: uuid.UUID
    earned: int = Field(ge=0)
    redeemed: int = Field(ge=0)
    available: int = Field(ge=0)


class CompOffRedeemRequest(BaseModel):
    employee_id: uuid.UUID
    date: dt.date
    note: str | None = None


# -----------------------------------------------------------------------------
# WeeklyOffRule Schemas
# -----------------------------------------------------------------------------
class WeeklyOffRuleBase(BaseModel):
    employee_id: uuid.UUID
    mode: WeeklyOffMode = WeeklyOffMode.FIXED_MANDATORY
    weekdays: list[int] = Field(default_factory=list, description="0=Mon, 6=Sun")
    valid_from: dt.date | None = None
    valid_to: dt.date | None = None


class WeeklyOffRuleCreate(WeeklyOffRuleBase):
    pass


class WeeklyOffRuleUpdate(BaseModel):
    mode: WeeklyOffMode | None = None
    weekdays: list[int] | None = None
    valid_from: dt.date | None = None
    valid_to: dt.date | None = None


class WeeklyOffRuleRead(WeeklyOffRuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: dt.datetime
    updated_at: dt.datetime


# -----------------------------------------------------------------------------
# EmployeePreference Schemas
# -----------------------------------------------------------------------------
class EmployeePreferenceBase(BaseModel):
    employee_id: uuid.UUID
    kind: PreferenceKind
    value: dict[str, Any] = Field(default_factory=dict)
    weight: int = Field(default=5, ge=1, le=10, description="Preference penalty weight")
    valid_from: dt.date | None = None
    valid_to: dt.date | None = None


class EmployeePreferenceCreate(EmployeePreferenceBase):
    pass


class EmployeePreferenceUpdate(BaseModel):
    kind: PreferenceKind | None = None
    value: dict[str, Any] | None = None
    weight: int | None = Field(default=None, ge=1, le=10)
    valid_from: dt.date | None = None
    valid_to: dt.date | None = None


class EmployeePreferenceRead(EmployeePreferenceBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: dt.datetime
    updated_at: dt.datetime
