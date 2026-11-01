"""Repositories for RosterPeriod, RosterEntry, and RosterConflict persistence.

Conforms to DATABASE_DESIGN.md §3 and SCHEDULING_ENGINE.md §§6–8.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.core import BrandProcess
from app.models.roster import RosterConflict, RosterEntry, RosterPeriod, RosterPeriodStatus
from app.repositories.base import BaseRepository


class RosterPeriodRepository(BaseRepository[RosterPeriod]):
    """Data access layer for RosterPeriod records."""

    def __init__(self, session: Session) -> None:
        super().__init__(RosterPeriod, session)

    def get_by_id(self, period_id: uuid.UUID) -> RosterPeriod | None:
        """Fetch a roster period by UUID."""
        stmt = select(RosterPeriod).where(RosterPeriod.id == period_id)
        return self.session.scalars(stmt).first()

    def get_by_month_and_version(self, month: date, version: int) -> RosterPeriod | None:
        """Fetch a specific version for a target month."""
        stmt = select(RosterPeriod).where(
            RosterPeriod.month == month,
            RosterPeriod.version == version,
        )
        return self.session.scalars(stmt).first()

    def get_latest_version(self, month: date) -> int:
        """Return the highest version number created for the target month, or 0 if none exist."""
        stmt = select(func.max(RosterPeriod.version)).where(RosterPeriod.month == month)
        latest = self.session.scalar(stmt)
        return latest or 0

    def get_published_period(self, month: date) -> RosterPeriod | None:
        """Fetch the single published roster period for a month if one exists."""
        stmt = select(RosterPeriod).where(
            RosterPeriod.month == month,
            RosterPeriod.status == RosterPeriodStatus.PUBLISHED,
        )
        return self.session.scalars(stmt).first()

    def list_by_month(self, month: date) -> Sequence[RosterPeriod]:
        """List all versions of a monthly roster, newest first."""
        stmt = (
            select(RosterPeriod)
            .where(RosterPeriod.month == month)
            .order_by(desc(RosterPeriod.version))
        )
        return self.session.scalars(stmt).all()

    def list_periods(self, month: date | None = None) -> Sequence[RosterPeriod]:
        """List roster periods, optionally filtered by month, ordered by month desc, version desc."""
        stmt = select(RosterPeriod)
        if month is not None:
            stmt = stmt.where(RosterPeriod.month == month)
        stmt = stmt.order_by(desc(RosterPeriod.month), desc(RosterPeriod.version))
        return self.session.scalars(stmt).all()


class RosterEntryRepository(BaseRepository[RosterEntry]):
    """Data access layer for daily RosterEntry cell records."""

    def __init__(self, session: Session) -> None:
        super().__init__(RosterEntry, session)

    def bulk_create(self, entries: list[RosterEntry]) -> None:
        """Persist a collection of roster entries in bulk."""
        self.session.add_all(entries)
        self.session.flush()

    def get_by_period(
        self,
        period_id: uuid.UUID,
        employee_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> Sequence[RosterEntry]:
        """Fetch schedule entries for a period with optional employee and date range filters."""
        stmt = (
            select(RosterEntry)
            .where(RosterEntry.roster_period_id == period_id)
            .options(joinedload(RosterEntry.employee))
            .order_by(RosterEntry.date, RosterEntry.employee_id)
        )
        if employee_id:
            stmt = stmt.where(RosterEntry.employee_id == employee_id)
        if date_from:
            stmt = stmt.where(RosterEntry.date >= date_from)
        if date_to:
            stmt = stmt.where(RosterEntry.date <= date_to)
        return self.session.scalars(stmt).all()

    def get_period_entry(
        self, period_id: uuid.UUID, employee_id: uuid.UUID, target_date: date
    ) -> RosterEntry | None:
        """Retrieve a specific single employee cell for a period."""
        stmt = select(RosterEntry).where(
            RosterEntry.roster_period_id == period_id,
            RosterEntry.employee_id == employee_id,
            RosterEntry.date == target_date,
        )
        return self.session.scalars(stmt).first()


class RosterConflictRepository(BaseRepository[RosterConflict]):
    """Data access layer for RosterConflict validation results."""

    def __init__(self, session: Session) -> None:
        super().__init__(RosterConflict, session)

    def bulk_create(self, conflicts: list[RosterConflict]) -> None:
        """Persist a collection of validation conflicts in bulk."""
        self.session.add_all(conflicts)
        self.session.flush()

    def get_by_period(
        self,
        period_id: uuid.UUID,
        severity: str | None = None,
        brand_process_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        employee_id: uuid.UUID | None = None,
        brand_id: uuid.UUID | None = None,
        target_date: date | None = None,
    ) -> Sequence[RosterConflict]:
        """Fetch validation conflicts for a period with optional severity and entity filters."""
        stmt = (
            select(RosterConflict)
            .where(RosterConflict.roster_period_id == period_id)
            .options(
                joinedload(RosterConflict.employee),
                joinedload(RosterConflict.brand_process).joinedload(BrandProcess.brand),
                joinedload(RosterConflict.brand_process).joinedload(BrandProcess.process),
            )
            .order_by(desc(RosterConflict.severity), RosterConflict.date_from, RosterConflict.code)
        )
        if severity:
            stmt = stmt.where(RosterConflict.severity == severity)
        if brand_process_id:
            stmt = stmt.where(RosterConflict.brand_process_id == brand_process_id)
        if employee_id:
            stmt = stmt.where(RosterConflict.employee_id == employee_id)
        if brand_id:
            stmt = stmt.join(RosterConflict.brand_process).where(BrandProcess.brand_id == brand_id)
        if target_date:
            stmt = stmt.where(
                RosterConflict.date_from <= target_date,
                (RosterConflict.date_to.is_(None) | (RosterConflict.date_to >= target_date)),
            )
        if date_from:
            stmt = stmt.where(RosterConflict.date_from >= date_from)
        if date_to:
            stmt = stmt.where(RosterConflict.date_to <= date_to)
        return self.session.scalars(stmt).all()
