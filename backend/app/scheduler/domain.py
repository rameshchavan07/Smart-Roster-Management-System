"""Pure-Python domain dataclasses and enums for the scheduling engine.

Non-negotiable architectural rule:
Zero external framework dependencies (no FastAPI, Pydantic, SQLAlchemy, or DB imports).
This module operates exclusively with standard library types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CalendarType(StrEnum):
    """Brand operating calendar model."""

    ALL_365 = "ALL_365"
    ALL_EXCEPT_HOLIDAYS = "ALL_EXCEPT_HOLIDAYS"
    EXCLUDE_SUNDAY_AND_HOLIDAYS = "EXCLUDE_SUNDAY_AND_HOLIDAYS"


class AssignmentType(StrEnum):
    """Staffing assignment role."""

    PRIMARY = "PRIMARY"
    BACKUP = "BACKUP"


class RosterStatus(StrEnum):
    """Day-level scheduled status code for an employee."""

    WORK = "WORK"
    WEEKLY_OFF = "WEEKLY_OFF"
    HOLIDAY_OFF = "HOLIDAY_OFF"
    HOLIDAY_WORK = "HOLIDAY_WORK"
    LEAVE = "LEAVE"
    COMP_OFF = "COMP_OFF"


class SupplyAvailability(StrEnum):
    """Pre-solver availability classification for an employee on a given date."""

    AVAILABLE = "AVAILABLE"
    LEAVE = "LEAVE"
    COMP_OFF = "COMP_OFF"
    HOLIDAY_OFF = "HOLIDAY_OFF"
    LOCKED = "LOCKED"


class WeeklyOffMode(StrEnum):
    """Weekly off allocation preference / mandate mode."""

    FIXED_MANDATORY = "FIXED_MANDATORY"
    FIXED_PREFERRED = "FIXED_PREFERRED"
    ROTATING = "ROTATING"
    ANY = "ANY"


class LeaveType(StrEnum):
    """Approved employee leave categorization."""

    PLANNED = "PLANNED"
    SICK = "SICK"
    UNPAID = "UNPAID"
    COMP_OFF = "COMP_OFF"


class ConflictSeverity(StrEnum):
    """Severity tier for validation conflicts."""

    BLOCKING = "BLOCKING"
    WARNING = "WARNING"
    INFO = "INFO"


class ConflictCode(StrEnum):
    """Catalog of conflict and notification codes per SCHEDULING_ENGINE.md."""

    # Primary coverage gap codes
    E001 = "E001"  # NO_COVERAGE: Required day, 0 employees assigned
    E002 = "E002"  # UNDER_STAFFED: Coverage < demand but > 0
    # Root-cause tags attached to E001/E002
    E003 = "E003"  # WEEKLY_OFF_BREAKS_COVERAGE
    E004 = "E004"  # LEAVE_BREAKS_COVERAGE
    # Schedule integrity codes
    E005 = "E005"  # MAX_CONSECUTIVE_EXCEEDED: Exceeded max consecutive work days
    E006 = "E006"  # WEEKLY_OFF_MISSING: Fewer weekly offs than required
    E007 = "E007"  # INVALID_CELL: Work on leave day, or weekly off on invalid day
    E008 = "E008"  # OVERLOAD: Employee on > max_concurrent_processes
    E009 = "E009"  # COMPOFF_BALANCE: Redeemed comp-off exceeds earned balance
    # Warning and informational codes
    W001 = "W001"  # PREFERENCE_VIOLATED: Preferred off not honoured
    W002 = "W002"  # UNFAIR_DISTRIBUTION: Weekend-off imbalance beyond threshold
    W003 = "W003"  # SINGLE_POINT_OF_FAILURE: Single eligible employee without backup
    W004 = "W004"  # STALE_ROSTER: Underlying inputs changed after generation


class SolverStatus(StrEnum):
    """Status returned by the constraint optimizer."""

    OPTIMAL = "OPTIMAL"
    FEASIBLE = "FEASIBLE"
    FALLBACK = "FALLBACK"
    INFEASIBLE = "INFEASIBLE"


class SuggestionType(StrEnum):
    """Resolution strategy recommended for a gap."""

    ASSIGN_BACKUP = "ASSIGN_BACKUP"
    SWAP_WEEKLY_OFF = "SWAP_WEEKLY_OFF"
    SHIFT_LEAVE = "SHIFT_LEAVE"
    OVERRIDE_LOCK = "OVERRIDE_LOCK"


# ---------------------------------------------------------------------------
# Core Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Holiday:
    """Public holiday definition."""

    date: date
    name: str
    brand_id: str | None = None  # None indicates a global holiday applying to all brands


@dataclass(frozen=True)
class CoverageRule:
    """Explicit coverage rule override (weekday or specific date)."""

    brand_process_id: str
    min_staff: int
    weekday: int | None = None  # 0 = Monday ... 6 = Sunday
    specific_date: date | None = None
    reason: str = ""

    def __post_init__(self) -> None:
        if (self.weekday is None and self.specific_date is None) or (
            self.weekday is not None and self.specific_date is not None
        ):
            raise ValueError(
                "CoverageRule requires exactly one of 'weekday' or 'specific_date' to be set."
            )
        if self.weekday is not None and not (0 <= self.weekday <= 6):
            raise ValueError(f"Weekday must be between 0 (Mon) and 6 (Sun), got {self.weekday}")


@dataclass(frozen=True)
class BrandProcess:
    """Operational unit combining a brand, process, and operating calendar."""

    id: str
    brand_id: str
    brand_name: str
    process_id: str
    process_name: str
    calendar_type: CalendarType
    min_coverage_default: int = 1
    pod_id: str | None = None


@dataclass(frozen=True)
class Assignment:
    """Staffing assignment linking an employee to a brand-process."""

    employee_id: str
    brand_process_id: str
    type: AssignmentType = AssignmentType.PRIMARY
    allocation_pct: int = 100


@dataclass(frozen=True)
class Employee:
    """Worker entity with scheduling preferences and constraints."""

    id: str
    code: str
    full_name: str
    pod_id: str
    is_floater: bool = False
    weekly_off_count: int = 1
    max_consecutive_days: int = 6
    max_concurrent_processes: int = 3
    weekly_off_mode: WeeklyOffMode = WeeklyOffMode.ANY
    fixed_weekly_off_weekdays: tuple[int, ...] = ()
    preferred_weekly_off_weekdays: tuple[int, ...] = ()
    preferred_off_dates: tuple[date, ...] = ()


@dataclass(frozen=True)
class EmployeeLeave:
    """Approved employee leave or comp-off redemption window."""

    employee_id: str
    start_date: date
    end_date: date
    type: LeaveType = LeaveType.PLANNED
    note: str = ""

    def __post_init__(self) -> None:
        if self.start_date > self.end_date:
            raise ValueError(
                f"start_date ({self.start_date}) cannot be after end_date ({self.end_date})"
            )

    def covers(self, target_date: date) -> bool:
        """Check if target_date falls within the inclusive leave interval."""
        return self.start_date <= target_date <= self.end_date


@dataclass(frozen=True)
class DemandCell:
    """Calculated headcount demand for a brand-process on a specific date."""

    brand_process_id: str
    brand_id: str
    brand_name: str
    process_id: str
    process_name: str
    date: date
    is_operating_day: bool
    required_headcount: int  # 0 on non-operating days
    reason: str = "default"


@dataclass(frozen=True)
class SupplyCell:
    """Calculated availability for an employee on a specific date before solving."""

    employee_id: str
    employee_code: str
    employee_name: str
    date: date
    availability: SupplyAvailability
    locked_status: RosterStatus | None = None
    is_locked: bool = False
    reason: str = ""


@dataclass(frozen=True)
class RosterCell:
    """Final or in-progress scheduled assignment for an employee on a date."""

    employee_id: str
    date: date
    status: RosterStatus
    is_locked: bool = False
    is_manual: bool = False
    note: str | None = None


@dataclass(frozen=True)
class CoverageCell:
    """Evaluated staffing coverage for a brand-process on a specific date."""

    brand_process_id: str
    date: date
    required: int
    covered: int
    shortfall: int
    assigned_employee_ids: tuple[str, ...] = ()

    @property
    def is_fully_covered(self) -> bool:
        return self.shortfall == 0


@dataclass(frozen=True)
class Suggestion:
    """Actionable recommendation to resolve a detected gap."""

    type: SuggestionType
    action: str
    description: str
    employee_id: str | None = None
    brand_process_id: str | None = None
    target_date: date | None = None
    source_date: date | None = None
    net_impact: str = ""
    score: float = 0.0
    fixes: int = 1
    opens: int = 0


@dataclass(frozen=True)
class Conflict:
    """Conflict or warning detected by the independent validator."""

    code: ConflictCode
    severity: ConflictSeverity
    brand_process_id: str | None = None
    employee_id: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    root_causes: tuple[str, ...] = ()
    message: str = ""
    suggestions: tuple[Suggestion, ...] = ()


@dataclass(frozen=True)
class ValidationResult:
    """Result of independent roster validation."""

    is_valid: bool
    conflicts: tuple[Conflict, ...] = ()
    blocking_count: int = 0
    warning_count: int = 0
    info_count: int = 0

    @classmethod
    def from_conflicts(cls, conflicts: tuple[Conflict, ...]) -> ValidationResult:
        blocking = sum(1 for c in conflicts if c.severity == ConflictSeverity.BLOCKING)
        warning = sum(1 for c in conflicts if c.severity == ConflictSeverity.WARNING)
        info = sum(1 for c in conflicts if c.severity == ConflictSeverity.INFO)
        return cls(
            is_valid=(blocking == 0),
            conflicts=conflicts,
            blocking_count=blocking,
            warning_count=warning,
            info_count=info,
        )


@dataclass(frozen=True)
class GenerationInput:
    """Complete inputs provided to the scheduling engine."""

    month_start: date
    month_end: date
    employees: tuple[Employee, ...]
    brand_processes: tuple[BrandProcess, ...]
    assignments: tuple[Assignment, ...]
    coverage_rules: tuple[CoverageRule, ...]
    holidays: tuple[Holiday, ...]
    leaves: tuple[EmployeeLeave, ...] = ()
    locked_cells: tuple[RosterCell, ...] = ()
    supply_matrix: tuple[SupplyCell, ...] = ()
    demand_matrix: tuple[DemandCell, ...] = ()
    random_seed: int = 42
    time_limit_seconds: float = 20.0
    previous_tail_work_days: dict[str, int] = field(default_factory=dict)
    initial_compoff_balances: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class GenerationOutput:
    """Output produced by the CP-SAT engine."""

    roster_cells: tuple[RosterCell, ...]
    coverage_cells: tuple[CoverageCell, ...]
    validation_result: ValidationResult
    solver_status: SolverStatus
    solve_time_seconds: float
    objective_value: float = 0.0
    slack_shortfall_total: int = 0


@dataclass(frozen=True)
class RepairInput:
    """Input parameters for local repair around an impacted window."""

    gen_input: GenerationInput
    current_roster_cells: tuple[RosterCell, ...]
    repair_dates: tuple[date, ...]
    repair_employee_ids: tuple[str, ...] | None = None
    use_fallback: bool = False


@dataclass(frozen=True)
class RepairOutput:
    """Result of local repair containing diff and validated result."""

    repaired_cells: tuple[RosterCell, ...]
    all_roster_cells: tuple[RosterCell, ...]
    coverage_cells: tuple[CoverageCell, ...]
    validation_result: ValidationResult
    solver_status: SolverStatus
    solve_time_seconds: float
    changed_cells_count: int
