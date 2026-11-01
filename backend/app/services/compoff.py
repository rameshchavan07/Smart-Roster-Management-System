"""Comp-off ledger and credit service."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models.roster import (
    RosterEntry,
    RosterEntryStatus,
    RosterPeriod,
    RosterPeriodStatus,
)
from app.models.rules import (
    CompOffKind,
    CompOffLedger,
    LeaveStatus,
    LeaveType,
)
from app.repositories.core import AuditLogRepository, EmployeeRepository
from app.repositories.roster import RosterEntryRepository, RosterPeriodRepository
from app.repositories.rules import CompOffLedgerRepository
from app.schemas.rules import (
    CompOffBalanceRead,
    CompOffLedgerCreate,
    CompOffRedeemRequest,
    LeaveCreate,
)


class CompOffService:
    """Service for CompOff ledger management, holiday accrual, and redemptions."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = CompOffLedgerRepository(session)
        self.emp_repo = EmployeeRepository(session)
        self.audit_repo = AuditLogRepository(session)
        self.period_repo = RosterPeriodRepository(session)
        self.entry_repo = RosterEntryRepository(session)

    def get_balance(self, employee_id: uuid.UUID) -> CompOffBalanceRead:
        """Compute current earned, redeemed, and available comp-off balances."""
        if not self.emp_repo.get_by_id(employee_id):
            raise NotFoundError(f"Employee '{employee_id}' not found")
        earned, redeemed, available = self.repo.get_balance(employee_id)
        return CompOffBalanceRead(
            employee_id=employee_id,
            earned=earned,
            redeemed=redeemed,
            available=available,
        )

    def get_balances_for_employees(self, employee_ids: Sequence[uuid.UUID]) -> dict[str, int]:
        """Compute available comp-off balance for multiple employees in bulk."""
        return self.repo.get_balances_for_employees(employee_ids)

    def list_entries(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        employee_id: uuid.UUID | None = None,
    ) -> tuple[Sequence[CompOffLedger], int]:
        """List comp-off ledger transactions with optional employee filter."""

        def query_filter(stmt: Any) -> Any:
            if employee_id is not None:
                stmt = stmt.where(CompOffLedger.employee_id == employee_id)
            return stmt.order_by(CompOffLedger.entry_date.desc())

        return self.repo.list(offset=offset, limit=limit, query_modifier=query_filter)

    def create_entry(
        self, data: CompOffLedgerCreate, actor_id: uuid.UUID | None = None
    ) -> CompOffLedger:
        """Manually record a comp-off credit or deduction entry."""
        emp = self.emp_repo.get_by_id(data.employee_id)
        if not emp:
            raise NotFoundError(f"Employee '{data.employee_id}' not found")
        if not emp.is_active:
            raise ConflictError(f"Cannot add comp-off entry for inactive employee '{emp.code}'")

        entry = CompOffLedger(
            employee_id=data.employee_id,
            entry_date=data.entry_date,
            kind=data.kind,
            source_roster_entry_id=data.source_roster_entry_id,
            status=data.status,
            expires_on=data.expires_on,
            note=data.note,
        )
        self.repo.create(entry)

        self.audit_repo.log_mutation(
            action="compoff.create",
            entity_type="CompOffLedger",
            entity_id=str(entry.id),
            user_id=actor_id,
            before=None,
            after={
                "employee_id": str(entry.employee_id),
                "kind": entry.kind.value,
                "date": str(entry.entry_date),
            },
        )
        return entry

    def redeem_compoff(
        self, data: CompOffRedeemRequest, actor_id: uuid.UUID | None = None
    ) -> CompOffLedger:
        """Redeem an available comp-off credit for a date, creating an approved leave."""
        emp = self.emp_repo.get_by_id(data.employee_id)
        if not emp:
            raise NotFoundError(f"Employee '{data.employee_id}' not found")
        if not emp.is_active:
            raise ConflictError(f"Cannot redeem comp-off for inactive employee '{emp.code}'")

        balance = self.get_balance(data.employee_id)
        if balance.available < 1:
            raise ConflictError("No available comp-off balance to redeem")

        # 1. Create REDEEMED ledger record
        redeemed_entry = CompOffLedger(
            employee_id=data.employee_id,
            entry_date=data.date,
            kind=CompOffKind.REDEEMED,
            status="CONFIRMED",
            note=data.note or "Comp-off redemption",
        )
        self.repo.create(redeemed_entry)

        # 2. Automatically generate approved COMP_OFF leave for the day (enforces overlap checks)
        # Import lazily to break circular reference with LeaveService
        from app.services.rules import LeaveService

        leave_service = LeaveService(self.session)
        leave_service.create_leave(
            LeaveCreate(
                employee_id=data.employee_id,
                start_date=data.date,
                end_date=data.date,
                type=LeaveType.COMP_OFF,
                status=LeaveStatus.APPROVED,
                note=f"Redeemed comp-off credit on {data.date}",
            ),
            actor_id=actor_id,
        )

        # 3. Flag any draft or published rosters covering this date as stale
        month_start = data.date.replace(day=1)
        periods = self.session.scalars(
            select(RosterPeriod).where(
                RosterPeriod.month == month_start,
                RosterPeriod.status.in_([RosterPeriodStatus.DRAFT, RosterPeriodStatus.PUBLISHED]),
            )
        ).all()
        for p in periods:
            if not p.is_stale:
                p.is_stale = True
                self.session.add(p)

        self.audit_repo.log_mutation(
            action="compoff.redeem",
            entity_type="CompOffLedger",
            entity_id=str(redeemed_entry.id),
            user_id=actor_id,
            before={"available": balance.available},
            after={"available": balance.available - 1, "date": str(data.date)},
        )
        return redeemed_entry

    def accrue_holiday_work_credits(
        self, roster_period_id: uuid.UUID, actor_id: uuid.UUID | None = None
    ) -> list[CompOffLedger]:
        """Accrue 1 comp-off credit for every employee scheduled as HOLIDAY_WORK in the roster period."""
        period = self.period_repo.get_by_id(roster_period_id)
        if not period:
            raise NotFoundError(f"Roster period '{roster_period_id}' not found")

        stmt = (
            select(RosterEntry)
            .where(
                RosterEntry.roster_period_id == roster_period_id,
                RosterEntry.status == RosterEntryStatus.HOLIDAY_WORK,
            )
            .order_by(RosterEntry.date, RosterEntry.employee_id)
        )
        entries = self.session.scalars(stmt).all()

        created_entries: list[CompOffLedger] = []
        for entry in entries:
            # Idempotency check: don't double-credit for the same employee and date
            existing = self.session.scalars(
                select(CompOffLedger).where(
                    CompOffLedger.employee_id == entry.employee_id,
                    CompOffLedger.entry_date == entry.date,
                    CompOffLedger.kind == CompOffKind.EARNED,
                )
            ).first()
            if existing:
                continue

            emp = self.emp_repo.get_by_id(entry.employee_id)
            emp_code = emp.code if emp else str(entry.employee_id)
            ledger_entry = CompOffLedger(
                employee_id=entry.employee_id,
                entry_date=entry.date,
                kind=CompOffKind.EARNED,
                source_roster_entry_id=entry.id,
                status="ACTIVE",
                note=(
                    f"Holiday work credit for {entry.date} ({emp_code}) in "
                    f"roster {period.month} v{period.version}"
                ),
            )
            self.repo.create(ledger_entry)
            created_entries.append(ledger_entry)

            self.audit_repo.log_mutation(
                action="compoff.accrue_holiday_work",
                entity_type="CompOffLedger",
                entity_id=str(ledger_entry.id),
                user_id=actor_id,
                before=None,
                after={
                    "employee_id": str(entry.employee_id),
                    "date": str(entry.date),
                    "roster_period_id": str(roster_period_id),
                    "source_roster_entry_id": str(entry.id),
                },
            )

        return created_entries
