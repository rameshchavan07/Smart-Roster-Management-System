"""SQLAlchemy models package.

All ORM models are registered here so that Alembic and repository layers can discover them.
"""

from app.models.auth import (
    AuditLog,
    User,
    UserRole,
)
from app.models.core import (
    Assignment,
    AssignmentType,
    Brand,
    BrandProcess,
    CalendarType,
    Employee,
    Pod,
    Process,
)
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.roster import (
    ConflictSeverity,
    EntrySource,
    RosterConflict,
    RosterEntry,
    RosterEntryStatus,
    RosterPeriod,
    RosterPeriodStatus,
)
from app.models.rules import (
    CompOffKind,
    CompOffLedger,
    CoverageRule,
    EmployeePreference,
    Holiday,
    Leave,
    LeaveStatus,
    LeaveType,
    PreferenceKind,
    WeeklyOffMode,
    WeeklyOffRule,
)

__all__ = [
    "Assignment",
    "AssignmentType",
    "AuditLog",
    "Brand",
    "BrandProcess",
    "CalendarType",
    "CompOffKind",
    "CompOffLedger",
    "ConflictSeverity",
    "CoverageRule",
    "Employee",
    "EmployeePreference",
    "EntrySource",
    "Holiday",
    "Leave",
    "LeaveStatus",
    "LeaveType",
    "Pod",
    "PreferenceKind",
    "Process",
    "RosterConflict",
    "RosterEntry",
    "RosterEntryStatus",
    "RosterPeriod",
    "RosterPeriodStatus",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    "User",
    "UserRole",
    "WeeklyOffMode",
    "WeeklyOffRule",
]
