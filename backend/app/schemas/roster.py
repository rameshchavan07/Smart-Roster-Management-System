"""Pydantic v2 schemas for roster generation, cell edits, views, and conflicts.

Conforms to API_DOCUMENTATION.md §4 and SCHEDULING_ENGINE.md §§7–9.
"""

from __future__ import annotations

import datetime as dt
import uuid
from enum import StrEnum
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
class RosterGenerateOptions(BaseModel):
    """Execution options for the scheduling solver."""

    seed: int = 42
    time_limit_s: int = 20
    base_roster_id: uuid.UUID | None = None
    use_fallback: bool = False


class RosterGenerateRequest(BaseModel):
    """Payload to trigger monthly roster generation."""

    month: str | dt.date = Field(description="Target month, e.g. '2026-12' or '2026-12-01'")
    pod_id: uuid.UUID | None = Field(default=None, description="Optional pod scope")
    options: RosterGenerateOptions | None = None
    seed: int | None = Field(default=None, description="RNG seed for solver determinism")
    time_limit_s: int | None = Field(default=None, ge=1, le=120, description="CP-SAT time limit")
    weights: dict[str, int] | None = Field(default=None, description="Custom objective weights")


class RosterSummary(BaseModel):
    """Validation conflict and coverage summary metrics."""

    blocking: int = 0
    warnings: int = 0
    info: int = 0
    coverage_pct: float = 100.0


class RosterGenerateResponse(BaseModel):
    """Response returned upon roster creation and generation."""

    id: uuid.UUID
    month: dt.date
    version: int
    status: RosterPeriodStatus
    solver_status: str | None = None
    summary: RosterSummary
    created_at: dt.datetime


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
    reason: str | None = None


class RosterEntriesBatchUpdateRequest(BaseModel):
    """Batch cell edit request."""

    entries: list[RosterEntryUpdateItem] = Field(min_length=1)
    acknowledge_blocking: bool = False


class RosterEntriesUpdateResponse(BaseModel):
    """Result of applying cell updates, including conflict diffs."""

    roster_period_id: uuid.UUID
    version: int
    status: RosterPeriodStatus
    updated_entries: list[RosterEntryRead]
    new_conflicts: list[dict[str, Any]] = Field(default_factory=list)
    resolved_conflicts: list[dict[str, Any]] = Field(default_factory=list)
    unchanged_conflicts: list[dict[str, Any]] = Field(default_factory=list)
    unchanged: int = 0
    net_conflict_change: int = 0
    affected_dates: list[str] = Field(default_factory=list)


class RosterCellLockItem(BaseModel):
    """Single cell lock specification."""

    employee_id: uuid.UUID
    date: dt.date
    is_locked: bool = True


class RosterEntriesLockRequest(BaseModel):
    """Lock or unlock schedule cells."""

    cells: list[RosterCellLockItem] = Field(default_factory=list)
    employee_ids: list[uuid.UUID] = Field(default_factory=list)
    dates: list[dt.date] = Field(default_factory=list)
    is_locked: bool = True


class RosterEntriesLockResponse(BaseModel):
    """Result of locking/unlocking cells."""

    roster_period_id: uuid.UUID
    version: int
    locked_count: int
    unlocked_count: int
    updated_entries: list[RosterEntryRead] = Field(default_factory=list)


# -----------------------------------------------------------------------------
# RosterConflict & Suggestion Schemas
# -----------------------------------------------------------------------------
class SuggestionNetEffect(BaseModel):
    """Impact of applying suggestion on total gaps."""

    fixes: int = 1
    opens: int = 0


class RosterSuggestionItem(BaseModel):
    """Ranked actionable resolution for a roster gap."""

    type: str
    kind: str
    action: str
    description: str
    employee_id: uuid.UUID | None = None
    employee_name: str | None = None
    employee_code: str | None = None
    brand_process_id: uuid.UUID | None = None
    brand_name: str | None = None
    process_name: str | None = None
    target_date: dt.date | None = None
    source_date: dt.date | None = None
    score: float = 0.0
    net_effect: SuggestionNetEffect = Field(default_factory=SuggestionNetEffect)
    net_impact: str = ""
    apply_payload: dict[str, Any] = Field(default_factory=dict)


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
    brand_name: str | None = None
    brand_code: str | None = None
    process_name: str | None = None
    process_code: str | None = None
    employee_name: str | None = None
    employee_code: str | None = None


class RosterConflictLLMExplanation(BaseModel):
    """Optional LLM-augmented executive rephrasing of a structured conflict (T-520)."""

    conflict_id: uuid.UUID
    deterministic_message: str
    executive_summary: str
    operational_impact: str
    recommended_action: str
    confidence_score: float = Field(default=0.98, ge=0.0, le=1.0)
    model_used: str = "domain-augmented-llm"


class RosterAcknowledgeRequest(BaseModel):
    """Acknowledge a BLOCKING conflict with required reason."""

    conflict_id: uuid.UUID
    reason: str = Field(min_length=5, description="Plain language explanation of override")


class RosterPublishRequest(BaseModel):
    """Publish a draft roster period."""

    period_id: uuid.UUID | None = None


class RosterCloneRequest(BaseModel):
    """Clone a roster period into a new working version."""

    parent_period_id: uuid.UUID | None = None
    note: str | None = None


class RosterRepairRequest(BaseModel):
    """Request for local repair around an impacted window."""

    dates: list[dt.date] = Field(default_factory=list, description="Specific dates to re-solve")
    date_from: dt.date | None = Field(default=None, description="Start date of impacted window")
    date_to: dt.date | None = Field(default=None, description="End date of impacted window")
    employee_ids: list[uuid.UUID] = Field(
        default_factory=list, description="Eligible employees for re-solving"
    )
    brand_process_ids: list[uuid.UUID] = Field(
        default_factory=list, description="Filter employees by brand-processes"
    )
    conflict_id: uuid.UUID | None = Field(
        default=None, description="Derive window from a specific conflict"
    )
    apply: bool = Field(
        default=False, description="Persist repaired entries directly to draft roster"
    )
    use_fallback: bool = Field(
        default=False, description="Use greedy heuristic instead of CP-SAT solver"
    )


class RosterRepairResponse(BaseModel):
    """Result of local repair diffing changes and conflicts."""

    is_feasible: bool
    repaired_cells_count: int
    repaired_cells: list[RosterEntryRead] = Field(default_factory=list)
    new_conflicts: list[dict[str, Any]] = Field(default_factory=list)
    resolved_conflicts: list[dict[str, Any]] = Field(default_factory=list)
    unchanged_conflicts: list[dict[str, Any]] = Field(default_factory=list)
    net_conflict_change: int
    solver_status: str
    solve_time_seconds: float
    applied: bool
    period: RosterPeriodRead | None = None


# -----------------------------------------------------------------------------
# Comparison Schemas
# -----------------------------------------------------------------------------
class RosterVersionMetrics(BaseModel):
    """Side-by-side quality and fairness metrics for a single roster version."""

    period_id: uuid.UUID
    version: int
    status: RosterPeriodStatus
    month: dt.date
    blocking_conflicts: int
    warning_conflicts: int
    info_conflicts: int
    total_conflicts: int
    coverage_pct: float
    total_shortfall: int
    shortfall_slots_count: int
    fairness_spread: int
    min_weekend_offs: int
    max_weekend_offs: int
    weekend_offs_by_employee: dict[str, int] = Field(default_factory=dict)


class RosterCellDiffItem(BaseModel):
    """Difference in cell assignment between two roster versions."""

    employee_id: uuid.UUID
    employee_code: str
    employee_name: str
    date: dt.date
    status_a: RosterEntryStatus | None = None
    status_b: RosterEntryStatus | None = None


class RosterCompareDelta(BaseModel):
    """Summary deltas comparing version B relative to version A (B - A)."""

    blocking_delta: int
    warnings_delta: int
    coverage_pct_delta: float
    fairness_spread_delta: int
    total_cells_changed: int


class RosterCompareResponse(BaseModel):
    """Side-by-side comparison of two roster periods."""

    period_a: RosterPeriodRead
    period_b: RosterPeriodRead
    metrics_a: RosterVersionMetrics
    metrics_b: RosterVersionMetrics
    delta: RosterCompareDelta
    conflict_diff: dict[str, list[dict[str, Any]]] = Field(
        default_factory=dict,
        description="Categorized conflicts: 'new_in_b', 'resolved_in_b', 'common'",
    )
    cell_diffs: list[RosterCellDiffItem] = Field(
        default_factory=list,
        description="Granular list of modified cells between version A and version B",
    )


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


class RosterDayEmployeeItem(BaseModel):
    """Employee representation in daily view."""

    employee_id: uuid.UUID
    employee_name: str
    employee_code: str
    assignment_type: str | None = None
    status: RosterEntryStatus
    is_locked: bool = False
    note: str | None = None


class RosterDayBrandProcessGroup(BaseModel):
    """Staffing and coverage state for a brand-process on a specific date."""

    brand_process_id: uuid.UUID
    brand_name: str
    process_name: str
    required: int
    actual: int
    shortfall: int
    is_operating_day: bool = True
    working_employees: list[RosterDayEmployeeItem] = Field(default_factory=list)
    off_employees: list[RosterDayEmployeeItem] = Field(default_factory=list)


class RosterDayViewResponse(BaseModel):
    """Who is working on a date, grouped by brand-process with coverage state."""

    period_id: uuid.UUID
    date: dt.date
    groups: list[RosterDayBrandProcessGroup]
    unassigned_working_employees: list[RosterDayEmployeeItem] = Field(default_factory=list)


# -----------------------------------------------------------------------------
# Impact (What-If) Simulator Schemas
# -----------------------------------------------------------------------------
class ImpactChangeType(StrEnum):
    """Change kinds accepted by what-if impact analysis."""

    ADD_LEAVE = "ADD_LEAVE"
    REMOVE_LEAVE = "REMOVE_LEAVE"
    CELL_EDIT = "CELL_EDIT"
    MARK_UNAVAILABLE = "MARK_UNAVAILABLE"


class RosterImpactChangeItem(BaseModel):
    """Single proposed modification to simulate."""

    type: ImpactChangeType | str
    employee_id: uuid.UUID | None = None
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    date: dt.date | None = None
    status: RosterEntryStatus | None = None
    brand_process_id: uuid.UUID | None = None


class RosterImpactRequest(BaseModel):
    """Simulate cell changes or leave additions without committing to database."""

    changes: list[RosterImpactChangeItem] = Field(default_factory=list)
    edits: list[RosterEntryUpdateItem] = Field(default_factory=list)


class RosterImpactResponse(BaseModel):
    """Simulation diff output."""

    is_feasible: bool
    new_conflicts: list[dict[str, Any]] = Field(default_factory=list)
    resolved_conflicts: list[dict[str, Any]] = Field(default_factory=list)
    unchanged_conflicts: list[dict[str, Any]] = Field(default_factory=list)
    unchanged: int = 0
    net_conflict_change: int = 0
    affected_dates: list[dt.date] = Field(default_factory=list)
