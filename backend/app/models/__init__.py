"""SQLAlchemy models package.

All ORM models are registered here so that Alembic and repository layers can discover them.
"""

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
    "Brand",
    "BrandProcess",
    "CalendarType",
    "CompOffKind",
    "CompOffLedger",
    "CoverageRule",
    "Employee",
    "EmployeePreference",
    "Holiday",
    "Leave",
    "LeaveStatus",
    "LeaveType",
    "Pod",
    "PreferenceKind",
    "Process",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    "WeeklyOffMode",
    "WeeklyOffRule",
]
