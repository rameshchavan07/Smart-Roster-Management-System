"""SQLAlchemy 2.0 repositories for rules, availability, leaves, comp-off, and holidays."""

import datetime as dt
import uuid
from collections.abc import Sequence

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.rules import (
    CompOffKind,
    CompOffLedger,
    CoverageRule,
    EmployeePreference,
    Holiday,
    Leave,
    LeaveStatus,
    WeeklyOffRule,
)
from app.repositories.base import BaseRepository


class CoverageRuleRepository(BaseRepository[CoverageRule]):
    """Data access for CoverageRule entities."""

    def __init__(self, session: Session) -> None:
        super().__init__(CoverageRule, session)

    def list_by_brand_process(
        self, brand_process_id: uuid.UUID, is_active: bool | None = None
    ) -> Sequence[CoverageRule]:
        stmt = select(CoverageRule).where(CoverageRule.brand_process_id == brand_process_id)
        if is_active is not None:
            stmt = stmt.where(CoverageRule.is_active == is_active)
        return self.session.scalars(stmt).all()


class HolidayRepository(BaseRepository[Holiday]):
    """Data access for Holiday entities."""

    def __init__(self, session: Session) -> None:
        super().__init__(Holiday, session)

    def get_by_date_and_brand(
        self, date_val: dt.date, brand_id: uuid.UUID | None
    ) -> Holiday | None:
        stmt = select(Holiday).where(Holiday.date == date_val, Holiday.brand_id == brand_id)
        return self.session.scalars(stmt).first()

    def list_holidays(
        self,
        *,
        brand_id: uuid.UUID | None = None,
        year: int | None = None,
        is_active: bool | None = None,
    ) -> Sequence[Holiday]:
        stmt = select(Holiday)
        if brand_id is not None:
            stmt = stmt.where((Holiday.brand_id == brand_id) | (Holiday.brand_id.is_(None)))
        if year is not None:
            start_year = dt.date(year, 1, 1)
            end_year = dt.date(year, 12, 31)
            stmt = stmt.where(Holiday.date.between(start_year, end_year))
        if is_active is not None:
            stmt = stmt.where(Holiday.is_active == is_active)
        return self.session.scalars(stmt.order_by(Holiday.date)).all()


class LeaveRepository(BaseRepository[Leave]):
    """Data access for Leave entities."""

    def __init__(self, session: Session) -> None:
        super().__init__(Leave, session)

    def list_by_employee(
        self,
        employee_id: uuid.UUID,
        status: LeaveStatus | None = None,
    ) -> Sequence[Leave]:
        stmt = select(Leave).where(Leave.employee_id == employee_id)
        if status is not None:
            stmt = stmt.where(Leave.status == status)
        return self.session.scalars(stmt.order_by(Leave.start_date)).all()

    def find_overlapping_leaves(
        self,
        employee_id: uuid.UUID,
        start_date: dt.date,
        end_date: dt.date,
        exclude_leave_id: uuid.UUID | None = None,
        statuses: Sequence[LeaveStatus] = (LeaveStatus.APPROVED, LeaveStatus.REQUESTED),
    ) -> Sequence[Leave]:
        """Check for active leave dates overlapping the target range [start_date, end_date]."""
        stmt = select(Leave).where(
            Leave.employee_id == employee_id,
            Leave.status.in_(statuses),
            and_(Leave.start_date <= end_date, Leave.end_date >= start_date),
        )
        if exclude_leave_id is not None:
            stmt = stmt.where(Leave.id != exclude_leave_id)
        return self.session.scalars(stmt).all()


class CompOffLedgerRepository(BaseRepository[CompOffLedger]):
    """Data access for CompOffLedger transactions."""

    def __init__(self, session: Session) -> None:
        super().__init__(CompOffLedger, session)

    def list_by_employee(self, employee_id: uuid.UUID) -> Sequence[CompOffLedger]:
        stmt = (
            select(CompOffLedger)
            .where(CompOffLedger.employee_id == employee_id)
            .order_by(CompOffLedger.entry_date)
        )
        return self.session.scalars(stmt).all()

    def get_balance(self, employee_id: uuid.UUID) -> tuple[int, int, int]:
        """Compute (earned, redeemed, available) comp-off count for employee."""
        earned_stmt = select(func.count()).where(
            CompOffLedger.employee_id == employee_id,
            CompOffLedger.kind == CompOffKind.EARNED,
        )
        redeemed_stmt = select(func.count()).where(
            CompOffLedger.employee_id == employee_id,
            CompOffLedger.kind == CompOffKind.REDEEMED,
        )
        earned = self.session.scalar(earned_stmt) or 0
        redeemed = self.session.scalar(redeemed_stmt) or 0
        available = max(0, earned - redeemed)
        return earned, redeemed, available


class WeeklyOffRuleRepository(BaseRepository[WeeklyOffRule]):
    """Data access for WeeklyOffRule entities."""

    def __init__(self, session: Session) -> None:
        super().__init__(WeeklyOffRule, session)

    def list_by_employee(self, employee_id: uuid.UUID) -> Sequence[WeeklyOffRule]:
        stmt = select(WeeklyOffRule).where(WeeklyOffRule.employee_id == employee_id)
        return self.session.scalars(stmt).all()


class EmployeePreferenceRepository(BaseRepository[EmployeePreference]):
    """Data access for EmployeePreference entities."""

    def __init__(self, session: Session) -> None:
        super().__init__(EmployeePreference, session)

    def list_by_employee(self, employee_id: uuid.UUID) -> Sequence[EmployeePreference]:
        stmt = select(EmployeePreference).where(EmployeePreference.employee_id == employee_id)
        return self.session.scalars(stmt).all()
