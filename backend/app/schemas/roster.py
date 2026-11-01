"""Pydantic v2 schemas for roster generation, cell edits, views, and conflicts.

Conforms to API_DOCUMENTATION.md §4 and SCHEDULING_ENGINE.md §§7–9.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.roster import (
    ConflictSeverity,
    EntrySource,
    RosterEntryStatus,
    RosterPeriodStatus,
)


# -----------------------------------------------------------------------------
# RosterPeriod Schemas
# -----------------------------------------------------------------------------
class RosterGenerateRequest(BaseModel):
    """Payload to trigger monthly roster generation."""

    month: dt.date = Field(description="First day of target month, e.g. 2026-12-01")
    pod_id: uuid.UUID | None = Field(default=None, description="Optional pod scope")
    seed: int = Field(default=42, description="RNG seed for solver determinism")
    time_limit_s: int = Field(default=20, ge=1, le=120, description="CP-SAT time limit")
    weights: dict[str, int] | None = Field(default=None, description="Custom objective weights")


class RosterPeriodRead(BaseModel):
    """Metadata for a roster version."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    month: dt.date
    version: int
    status: RosterPeriodStatus
    solver_status: str | None = None
    generation_params: dict[str, Any] = Field(default_factory=dict)
    parent_period_id: uuid.UUID | None = None
    is_stale: bool = False
    created_by_id: uuid.UUID | None = None
    published_at: dt.datetime | None = None
    created_at: dt.datetime
    entries_count: int | None = None
    conflicts_count: int | None = None


# -----------------------------------------------------------------------------
# RosterEntry Schemas
# -----------------------------------------------------------------------------
class RosterEntryRead(BaseModel):
    """Daily schedule cell for an employee."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    roster_period_id: uuid.UUID
    employee_id: uuid.UUID
    date: dt.date
    shift_id: uuid.UUID | None = None
    status: RosterEntryStatus
    source: EntrySource
    is_locked: bool
    note: str | None = None


class RosterEntryUpdateItem(BaseModel):
    """Single cell change payload."""

    employee_id: uuid.UUID
    date: dt.date
    status: RosterEntryStatus
    source: EntrySource = EntrySource.MANUAL
    is_locked: bool | None = None
    note: str | None = None


class RosterEntriesBatchUpdateRequest(BaseModel):
    """Batch cell edit request."""

    entries: list[RosterEntryUpdateItem] = Field(min_length=1)


class RosterEntriesLockRequest(BaseModel):
    """Lock or unlock schedule cells."""

    employee_ids: list[uuid.UUID] = Field(default_factory=list)
    dates: list[dt.date] = Field(default_factory=list)
    is_locked: bool = True


# -----------------------------------------------------------------------------
# RosterConflict Schemas
# -----------------------------------------------------------------------------
class RosterConflictRead(BaseModel):
    """Validation conflict representation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    roster_period_id: uuid.UUID
    code: str
    severity: ConflictSeverity
    brand_process_id: uuid.UUID | None = None
    employee_id: uuid.UUID | None = None
    date_from: dt.date | None = None
    date_to: dt.date | None = None
    root_causes: list[str] = Field(default_factory=list)
    message: str
    suggestions: list[dict[str, Any]] = Field(default_factory=list)
    is_acknowledged: bool = False
    acknowledged_by_id: uuid.UUID | None = None
    acknowledged_reason: str | None = None
    resolved_at: dt.datetime | None = None


class RosterAcknowledgeRequest(BaseModel):
    """Acknowledge a BLOCKING conflict with required reason."""

    conflict_id: uuid.UUID
    reason: str = Field(min_length=5, description="Plain language explanation of override")


class RosterPublishRequest(BaseModel):
    """Publish a draft roster period."""

    period_id: uuid.UUID


class RosterCloneRequest(BaseModel):
    """Clone a roster period into a new working version."""

    parent_period_id: uuid.UUID
    note: str | None = None


# -----------------------------------------------------------------------------
# Grid & View Schemas
# -----------------------------------------------------------------------------
class RosterGridCell(BaseModel):
    """Single cell rendered in the frontend matrix."""

    date: dt.date
    status: RosterEntryStatus
    source: EntrySource
    is_locked: bool
    note: str | None = None
    conflicts: list[str] = Field(default_factory=list)


class RosterGridRow(BaseModel):
    """Row in the roster grid corresponding to an employee."""

    employee_id: uuid.UUID
    employee_name: str
    employee_code: str
    pod_name: str | None = None
    primary_assignments: list[str] = Field(default_factory=list)
    cells: dict[str, RosterGridCell] = Field(description="ISO date string -> Cell data")


class RosterGridViewResponse(BaseModel):
    """Complete grid payload for Company, Pod, Brand, Process, or Employee view."""

    period: RosterPeriodRead
    view: str
    start_date: dt.date
    end_date: dt.date
    rows: list[RosterGridRow]


class RosterCoverageCell(BaseModel):
    """Coverage demand vs actual staffing cell."""

    date: dt.date
    brand_process_id: uuid.UUID
    brand_name: str | None = None
    process_name: str | None = None
    required: int
    actual: int
    shortfall: int


# -----------------------------------------------------------------------------
# Impact (What-If) Simulator Schemas
# -----------------------------------------------------------------------------
class RosterImpactRequest(BaseModel):
    """Simulate cell changes without committing to database."""

    edits: list[RosterEntryUpdateItem] = Field(min_length=1)


class RosterImpactResponse(BaseModel):
    """Simulation diff output."""

    is_feasible: bool
    new_conflicts: list[dict[str, Any]] = Field(default_factory=list)
    resolved_conflicts: list[dict[str, Any]] = Field(default_factory=list)
    unchanged_conflicts: list[dict[str, Any]] = Field(default_factory=list)
    net_conflict_change: int
    affected_dates: list[dt.date] = Field(default_factory=list)
