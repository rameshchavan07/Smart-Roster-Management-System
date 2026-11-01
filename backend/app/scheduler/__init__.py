"""Pure Python scheduling engine module.

Layers: api -> services -> (repositories, scheduler, domain).
This module has zero dependencies on api, db, models, fastapi, or sqlalchemy.
"""

from app.scheduler.calendar import (
    get_applicable_holidays,
    get_operating_dates,
    has_applicable_holiday,
    is_holiday_applicable,
    is_operating_day,
    resolve_calendar_matrix,
    resolve_operating_days,
)
from app.scheduler.demand import (
    build_demand_cell,
    build_demand_lookup,
    build_demand_matrix,
)
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
    EmployeeLeave,
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
from app.scheduler.explain import (
    enrich_conflicts,
    explain_conflict,
    rank_backup_candidates,
)
from app.scheduler.generator_cpsat import generate_cpsat
from app.scheduler.generator_greedy import generate_greedy
from app.scheduler.supply import (
    build_supply_cell,
    build_supply_lookup,
    build_supply_matrix,
)
from app.scheduler.validator import (
    partition_into_weeks,
    validate,
    validate_roster,
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
    "EmployeeLeave",
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
    # Calendar resolver
    "get_applicable_holidays",
    "get_operating_dates",
    "has_applicable_holiday",
    "is_holiday_applicable",
    "is_operating_day",
    "resolve_calendar_matrix",
    "resolve_operating_days",
    # Demand builder
    "build_demand_cell",
    "build_demand_lookup",
    "build_demand_matrix",
    # Supply builder
    "build_supply_cell",
    "build_supply_lookup",
    "build_supply_matrix",
    # Validator
    "partition_into_weeks",
    "validate",
    "validate_roster",
    # Explainer & suggestions
    "enrich_conflicts",
    "explain_conflict",
    "rank_backup_candidates",
    # Generator
    "generate_cpsat",
    "generate_greedy",
]
