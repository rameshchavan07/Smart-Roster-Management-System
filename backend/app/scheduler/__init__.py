"""Pure Python scheduling engine module.

Layers: api -> services -> (repositories, scheduler, domain).
This module has zero dependencies on api, db, models, fastapi, or sqlalchemy.
"""

from app.scheduler.domain import (
    Assignment,
    AssignmentType,
    BrandProcess,
    CalendarType,
    Conflict,
    ConflictCode,
    ConflictSeverity,
    CoverageCell,
    CoverageRule,
    DemandCell,
    Employee,
    GenerationInput,
    GenerationOutput,
    Holiday,
    LeaveType,
    RosterCell,
    RosterStatus,
    SolverStatus,
    Suggestion,
    SuggestionType,
    SupplyAvailability,
    SupplyCell,
    ValidationResult,
    WeeklyOffMode,
)

__all__ = [
    "Assignment",
    "AssignmentType",
    "BrandProcess",
    "CalendarType",
    "Conflict",
    "ConflictCode",
    "ConflictSeverity",
    "CoverageCell",
    "CoverageRule",
    "DemandCell",
    "Employee",
    "GenerationInput",
    "GenerationOutput",
    "Holiday",
    "LeaveType",
    "RosterCell",
    "RosterStatus",
    "SolverStatus",
    "Suggestion",
    "SuggestionType",
    "SupplyAvailability",
    "SupplyCell",
    "ValidationResult",
    "WeeklyOffMode",
]
