"""Rules, availability, leaves, comp-off, and holiday domain services with audit hooks.

Conforms to DATABASE_DESIGN.md §3, §5, SCHEDULING_ENGINE.md §§3–4, and API_DOCUMENTATION.md §4.
"""

import datetime as dt
import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models.rules import (
    CompOffKind,
    CompOffLedger,
    CoverageRule,
    EmployeePreference,
    Holiday,
    Leave,
    LeaveStatus,
    LeaveType,
    WeeklyOffRule,
)
from app.repositories.core import (
    AuditLogRepository,
    BrandProcessRepository,
    BrandRepository,
    EmployeeRepository,
)
from app.repositories.rules import (
    CompOffLedgerRepository,
    CoverageRuleRepository,
    EmployeePreferenceRepository,
    HolidayRepository,
    LeaveRepository,
    WeeklyOffRuleRepository,
)
from app.schemas.rules import (
    CompOffBalanceRead,
    CompOffLedgerCreate,
    CompOffRedeemRequest,
    CoverageRuleCreate,
    CoverageRuleUpdate,
    EmployeePreferenceCreate,
    EmployeePreferenceUpdate,
    HolidayCreate,
    HolidayUpdate,
    LeaveCreate,
    LeaveUpdate,
    WeeklyOffRuleCreate,
    WeeklyOffRuleUpdate,
)


class CoverageRuleService:
    """Service for BrandProcess minimum coverage requirements."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = CoverageRuleRepository(session)
        self.bp_repo = BrandProcessRepository(session)
        self.audit_repo = AuditLogRepository(session)

    def get_coverage_rule(self, rule_id: uuid.UUID) -> CoverageRule:
        rule = self.repo.get_by_id(rule_id)
        if not rule:
            raise NotFoundError(f"CoverageRule with id '{rule_id}' not found")
        return rule

    def list_coverage_rules(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        brand_process_id: uuid.UUID | None = None,
        is_active: bool | None = None,
    ) -> tuple[Sequence[CoverageRule], int]:
        def query_filter(stmt: Any) -> Any:
            if brand_process_id is not None:
                stmt = stmt.where(CoverageRule.brand_process_id == brand_process_id)
            return stmt

        return self.repo.list(
            offset=offset, limit=limit, is_active=is_active, query_modifier=query_filter
        )

    def create_coverage_rule(
        self, data: CoverageRuleCreate, actor_id: uuid.UUID | None = None
    ) -> CoverageRule:
        if not self.bp_repo.get_by_id(data.brand_process_id):
            raise NotFoundError(f"BrandProcess '{data.brand_process_id}' not found")

        rule = CoverageRule(
            brand_process_id=data.brand_process_id,
            weekday=data.weekday,
            specific_date=data.specific_date,
            min_staff=data.min_staff,
            reason=data.reason,
        )
        self.repo.create(rule)

        self.audit_repo.log_mutation(
            action="coverage_rule.create",
            entity_type="CoverageRule",
            entity_id=str(rule.id),
            user_id=actor_id,
            before=None,
            after={
                "brand_process_id": str(rule.brand_process_id),
                "min_staff": rule.min_staff,
                "weekday": rule.weekday,
                "specific_date": str(rule.specific_date) if rule.specific_date else None,
            },
        )
        return rule

    def update_coverage_rule(
        self,
        rule_id: uuid.UUID,
        data: CoverageRuleUpdate,
        actor_id: uuid.UUID | None = None,
    ) -> CoverageRule:
        rule = self.get_coverage_rule(rule_id)
        before_state = {
            "min_staff": rule.min_staff,
            "weekday": rule.weekday,
            "specific_date": str(rule.specific_date) if rule.specific_date else None,
            "is_active": rule.is_active,
        }

        if data.weekday is not None:
            rule.weekday = data.weekday
        if data.specific_date is not None:
            rule.specific_date = data.specific_date
        if data.min_staff is not None:
            rule.min_staff = data.min_staff
        if data.reason is not None:
            rule.reason = data.reason
        if data.is_active is not None:
            rule.is_active = data.is_active

        self.repo.update(rule)

        after_state = {
            "min_staff": rule.min_staff,
            "weekday": rule.weekday,
            "specific_date": str(rule.specific_date) if rule.specific_date else None,
            "is_active": rule.is_active,
        }
        self.audit_repo.log_mutation(
            action="coverage_rule.update",
            entity_type="CoverageRule",
            entity_id=str(rule.id),
            user_id=actor_id,
            before=before_state,
            after=after_state,
        )
        return rule

    def delete_coverage_rule(self, rule_id: uuid.UUID, actor_id: uuid.UUID | None = None) -> None:
        rule = self.get_coverage_rule(rule_id)
        before_state = {"id": str(rule.id), "min_staff": rule.min_staff}
        self.repo.delete(rule)

        self.audit_repo.log_mutation(
            action="coverage_rule.delete",
            entity_type="CoverageRule",
            entity_id=str(rule_id),
            user_id=actor_id,
            before=before_state,
            after=None,
        )


class HolidayService:
    """Service for public and brand-specific holiday calendars."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = HolidayRepository(session)
        self.brand_repo = BrandRepository(session)
        self.audit_repo = AuditLogRepository(session)

    def get_holiday(self, holiday_id: uuid.UUID) -> Holiday:
        holiday = self.repo.get_by_id(holiday_id)
        if not holiday:
            raise NotFoundError(f"Holiday with id '{holiday_id}' not found")
        return holiday

    def list_holidays(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        brand_id: uuid.UUID | None = None,
        year: int | None = None,
        is_active: bool | None = None,
    ) -> tuple[Sequence[Holiday], int]:
        def query_filter(stmt: Any) -> Any:
            if brand_id is not None:
                stmt = stmt.where((Holiday.brand_id == brand_id) | (Holiday.brand_id.is_(None)))
            if year is not None:
                stmt = stmt.where(Holiday.date.between(dt.date(year, 1, 1), dt.date(year, 12, 31)))
            return stmt.order_by(Holiday.date)

        return self.repo.list(
            offset=offset, limit=limit, is_active=is_active, query_modifier=query_filter
        )

    def create_holiday(self, data: HolidayCreate, actor_id: uuid.UUID | None = None) -> Holiday:
        if data.brand_id and not self.brand_repo.get_by_id(data.brand_id):
            raise NotFoundError(f"Brand '{data.brand_id}' not found")

        if self.repo.get_by_date_and_brand(data.date, data.brand_id):
            raise ConflictError(f"Holiday already configured for date {data.date} and target brand")

        holiday = Holiday(date=data.date, name=data.name, brand_id=data.brand_id)
        self.repo.create(holiday)

        self.audit_repo.log_mutation(
            action="holiday.create",
            entity_type="Holiday",
            entity_id=str(holiday.id),
            user_id=actor_id,
            before=None,
            after={"date": str(holiday.date), "name": holiday.name},
        )
        return holiday

    def update_holiday(
        self,
        holiday_id: uuid.UUID,
        data: HolidayUpdate,
        actor_id: uuid.UUID | None = None,
    ) -> Holiday:
        holiday = self.get_holiday(holiday_id)
        before_state = {
            "date": str(holiday.date),
            "name": holiday.name,
            "brand_id": str(holiday.brand_id) if holiday.brand_id else None,
            "is_active": holiday.is_active,
        }

        target_date = data.date if data.date is not None else holiday.date
        target_brand_id = data.brand_id if data.brand_id is not None else holiday.brand_id

        if (target_date != holiday.date or target_brand_id != holiday.brand_id) and (
            self.repo.get_by_date_and_brand(target_date, target_brand_id)
        ):
            raise ConflictError(f"Holiday already configured for date {target_date}")

        if data.date is not None:
            holiday.date = data.date
        if data.name is not None:
            holiday.name = data.name
        if data.brand_id is not None:
            if data.brand_id and not self.brand_repo.get_by_id(data.brand_id):
                raise NotFoundError(f"Brand '{data.brand_id}' not found")
            holiday.brand_id = data.brand_id
        if data.is_active is not None:
            holiday.is_active = data.is_active

        self.repo.update(holiday)

        after_state = {
            "date": str(holiday.date),
            "name": holiday.name,
            "brand_id": str(holiday.brand_id) if holiday.brand_id else None,
            "is_active": holiday.is_active,
        }
        self.audit_repo.log_mutation(
            action="holiday.update",
            entity_type="Holiday",
            entity_id=str(holiday.id),
            user_id=actor_id,
            before=before_state,
            after=after_state,
        )
        return holiday

    def delete_holiday(self, holiday_id: uuid.UUID, actor_id: uuid.UUID | None = None) -> None:
        holiday = self.get_holiday(holiday_id)
        before_state = {"date": str(holiday.date), "name": holiday.name, "id": str(holiday.id)}
        self.repo.delete(holiday)

        self.audit_repo.log_mutation(
            action="holiday.delete",
            entity_type="Holiday",
            entity_id=str(holiday_id),
            user_id=actor_id,
            before=before_state,
            after=None,
        )


class WeeklyOffRuleService:
    """Service for configuring employee weekly-off patterns."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = WeeklyOffRuleRepository(session)
        self.emp_repo = EmployeeRepository(session)
        self.audit_repo = AuditLogRepository(session)

    def get_weekly_off_rule(self, rule_id: uuid.UUID) -> WeeklyOffRule:
        rule = self.repo.get_by_id(rule_id)
        if not rule:
            raise NotFoundError(f"WeeklyOffRule '{rule_id}' not found")
        return rule

    def list_weekly_off_rules(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        employee_id: uuid.UUID | None = None,
    ) -> tuple[Sequence[WeeklyOffRule], int]:
        def query_filter(stmt: Any) -> Any:
            if employee_id is not None:
                stmt = stmt.where(WeeklyOffRule.employee_id == employee_id)
            return stmt

        return self.repo.list(offset=offset, limit=limit, query_modifier=query_filter)

    def create_weekly_off_rule(
        self, data: WeeklyOffRuleCreate, actor_id: uuid.UUID | None = None
    ) -> WeeklyOffRule:
        if not self.emp_repo.get_by_id(data.employee_id):
            raise NotFoundError(f"Employee '{data.employee_id}' not found")

        rule = WeeklyOffRule(
            employee_id=data.employee_id,
            mode=data.mode,
            weekdays=data.weekdays,
            valid_from=data.valid_from,
            valid_to=data.valid_to,
        )
        self.repo.create(rule)

        self.audit_repo.log_mutation(
            action="weekly_off_rule.create",
            entity_type="WeeklyOffRule",
            entity_id=str(rule.id),
            user_id=actor_id,
            before=None,
            after={
                "employee_id": str(rule.employee_id),
                "mode": rule.mode.value,
                "weekdays": rule.weekdays,
            },
        )
        return rule

    def update_weekly_off_rule(
        self,
        rule_id: uuid.UUID,
        data: WeeklyOffRuleUpdate,
        actor_id: uuid.UUID | None = None,
    ) -> WeeklyOffRule:
        rule = self.get_weekly_off_rule(rule_id)
        before_state = {
            "mode": rule.mode.value,
            "weekdays": rule.weekdays,
            "valid_from": str(rule.valid_from) if rule.valid_from else None,
            "valid_to": str(rule.valid_to) if rule.valid_to else None,
        }

        if data.mode is not None:
            rule.mode = data.mode
        if data.weekdays is not None:
            rule.weekdays = data.weekdays
        if data.valid_from is not None:
            rule.valid_from = data.valid_from
        if data.valid_to is not None:
            rule.valid_to = data.valid_to

        self.repo.update(rule)

        after_state = {
            "mode": rule.mode.value,
            "weekdays": rule.weekdays,
            "valid_from": str(rule.valid_from) if rule.valid_from else None,
            "valid_to": str(rule.valid_to) if rule.valid_to else None,
        }
        self.audit_repo.log_mutation(
            action="weekly_off_rule.update",
            entity_type="WeeklyOffRule",
            entity_id=str(rule.id),
            user_id=actor_id,
            before=before_state,
            after=after_state,
        )
        return rule

    def delete_weekly_off_rule(self, rule_id: uuid.UUID, actor_id: uuid.UUID | None = None) -> None:
        rule = self.get_weekly_off_rule(rule_id)
        before_state = {"employee_id": str(rule.employee_id), "id": str(rule.id)}
        self.repo.delete(rule)

        self.audit_repo.log_mutation(
            action="weekly_off_rule.delete",
            entity_type="WeeklyOffRule",
            entity_id=str(rule_id),
            user_id=actor_id,
            before=before_state,
            after=None,
        )


class EmployeePreferenceService:
    """Service for soft scheduling preferences."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = EmployeePreferenceRepository(session)
        self.emp_repo = EmployeeRepository(session)
        self.audit_repo = AuditLogRepository(session)

    def get_preference(self, pref_id: uuid.UUID) -> EmployeePreference:
        pref = self.repo.get_by_id(pref_id)
        if not pref:
            raise NotFoundError(f"EmployeePreference '{pref_id}' not found")
        return pref

    def list_preferences(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        employee_id: uuid.UUID | None = None,
    ) -> tuple[Sequence[EmployeePreference], int]:
        def query_filter(stmt: Any) -> Any:
            if employee_id is not None:
                stmt = stmt.where(EmployeePreference.employee_id == employee_id)
            return stmt

        return self.repo.list(offset=offset, limit=limit, query_modifier=query_filter)

    def create_preference(
        self, data: EmployeePreferenceCreate, actor_id: uuid.UUID | None = None
    ) -> EmployeePreference:
        if not self.emp_repo.get_by_id(data.employee_id):
            raise NotFoundError(f"Employee '{data.employee_id}' not found")

        pref = EmployeePreference(
            employee_id=data.employee_id,
            kind=data.kind,
            value=data.value,
            weight=data.weight,
            valid_from=data.valid_from,
            valid_to=data.valid_to,
        )
        self.repo.create(pref)

        self.audit_repo.log_mutation(
            action="preference.create",
            entity_type="EmployeePreference",
            entity_id=str(pref.id),
            user_id=actor_id,
            before=None,
            after={
                "employee_id": str(pref.employee_id),
                "kind": pref.kind.value,
                "weight": pref.weight,
            },
        )
        return pref

    def update_preference(
        self,
        pref_id: uuid.UUID,
        data: EmployeePreferenceUpdate,
        actor_id: uuid.UUID | None = None,
    ) -> EmployeePreference:
        pref = self.get_preference(pref_id)
        before_state = {
            "kind": pref.kind.value,
            "value": pref.value,
            "weight": pref.weight,
        }

        if data.kind is not None:
            pref.kind = data.kind
        if data.value is not None:
            pref.value = data.value
        if data.weight is not None:
            pref.weight = data.weight
        if data.valid_from is not None:
            pref.valid_from = data.valid_from
        if data.valid_to is not None:
            pref.valid_to = data.valid_to

        self.repo.update(pref)

        after_state = {
            "kind": pref.kind.value,
            "value": pref.value,
            "weight": pref.weight,
        }
        self.audit_repo.log_mutation(
            action="preference.update",
            entity_type="EmployeePreference",
            entity_id=str(pref.id),
            user_id=actor_id,
            before=before_state,
            after=after_state,
        )
        return pref

    def delete_preference(self, pref_id: uuid.UUID, actor_id: uuid.UUID | None = None) -> None:
        pref = self.get_preference(pref_id)
        before_state = {"employee_id": str(pref.employee_id), "id": str(pref.id)}
        self.repo.delete(pref)

        self.audit_repo.log_mutation(
            action="preference.delete",
            entity_type="EmployeePreference",
            entity_id=str(pref_id),
            user_id=actor_id,
            before=before_state,
            after=None,
        )


class LeaveService:
    """Service for employee leaves with overlap prevention."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = LeaveRepository(session)
        self.emp_repo = EmployeeRepository(session)
        self.audit_repo = AuditLogRepository(session)

    def get_leave(self, leave_id: uuid.UUID) -> Leave:
        leave = self.repo.get_by_id(leave_id)
        if not leave:
            raise NotFoundError(f"Leave with id '{leave_id}' not found")
        return leave

    def list_leaves(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        employee_id: uuid.UUID | None = None,
        status: LeaveStatus | None = None,
    ) -> tuple[Sequence[Leave], int]:
        def query_filter(stmt: Any) -> Any:
            if employee_id is not None:
                stmt = stmt.where(Leave.employee_id == employee_id)
            if status is not None:
                stmt = stmt.where(Leave.status == status)
            return stmt.order_by(Leave.start_date.desc())

        return self.repo.list(offset=offset, limit=limit, query_modifier=query_filter)

    def create_leave(self, data: LeaveCreate, actor_id: uuid.UUID | None = None) -> Leave:
        if not self.emp_repo.get_by_id(data.employee_id):
            raise NotFoundError(f"Employee '{data.employee_id}' not found")

        # Overlap check conforming to DATABASE_DESIGN.md §5
        overlaps = self.repo.find_overlapping_leaves(
            data.employee_id, data.start_date, data.end_date
        )
        if overlaps:
            raise ConflictError(
                f"Leave request conflicts with existing leave from {overlaps[0].start_date} to {overlaps[0].end_date}"
            )

        leave = Leave(
            employee_id=data.employee_id,
            start_date=data.start_date,
            end_date=data.end_date,
            type=data.type,
            status=data.status,
            note=data.note,
        )
        self.repo.create(leave)

        self.audit_repo.log_mutation(
            action="leave.create",
            entity_type="Leave",
            entity_id=str(leave.id),
            user_id=actor_id,
            before=None,
            after={
                "employee_id": str(leave.employee_id),
                "start_date": str(leave.start_date),
                "end_date": str(leave.end_date),
                "status": leave.status.value,
            },
        )
        return leave

    def update_leave(
        self, leave_id: uuid.UUID, data: LeaveUpdate, actor_id: uuid.UUID | None = None
    ) -> Leave:
        leave = self.get_leave(leave_id)
        before_state = {
            "start_date": str(leave.start_date),
            "end_date": str(leave.end_date),
            "type": leave.type.value,
            "status": leave.status.value,
        }

        target_start = data.start_date if data.start_date is not None else leave.start_date
        target_end = data.end_date if data.end_date is not None else leave.end_date

        if data.start_date is not None or data.end_date is not None:
            overlaps = self.repo.find_overlapping_leaves(
                leave.employee_id,
                target_start,
                target_end,
                exclude_leave_id=leave.id,
            )
            if overlaps:
                raise ConflictError(
                    f"Updated dates conflict with existing leave from {overlaps[0].start_date} to {overlaps[0].end_date}"
                )

        if data.start_date is not None:
            leave.start_date = data.start_date
        if data.end_date is not None:
            leave.end_date = data.end_date
        if data.type is not None:
            leave.type = data.type
        if data.note is not None:
            leave.note = data.note

        self.repo.update(leave)

        after_state = {
            "start_date": str(leave.start_date),
            "end_date": str(leave.end_date),
            "type": leave.type.value,
            "status": leave.status.value,
        }
        self.audit_repo.log_mutation(
            action="leave.update",
            entity_type="Leave",
            entity_id=str(leave.id),
            user_id=actor_id,
            before=before_state,
            after=after_state,
        )
        return leave

    def set_leave_status(
        self,
        leave_id: uuid.UUID,
        new_status: LeaveStatus,
        actor_id: uuid.UUID | None = None,
    ) -> Leave:
        leave = self.get_leave(leave_id)
        before_status = leave.status.value

        leave.status = new_status
        self.repo.update(leave)

        self.audit_repo.log_mutation(
            action=f"leave.{new_status.value.lower()}",
            entity_type="Leave",
            entity_id=str(leave.id),
            user_id=actor_id,
            before={"status": before_status},
            after={"status": new_status.value},
        )
        return leave

    def delete_leave(self, leave_id: uuid.UUID, actor_id: uuid.UUID | None = None) -> None:
        leave = self.get_leave(leave_id)
        before_state = {
            "employee_id": str(leave.employee_id),
            "start_date": str(leave.start_date),
            "id": str(leave.id),
        }
        self.repo.delete(leave)

        self.audit_repo.log_mutation(
            action="leave.delete",
            entity_type="Leave",
            entity_id=str(leave_id),
            user_id=actor_id,
            before=before_state,
            after=None,
        )


class CompOffService:
    """Service for CompOff ledger management and redemptions."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = CompOffLedgerRepository(session)
        self.emp_repo = EmployeeRepository(session)
        self.leave_service = LeaveService(session)
        self.audit_repo = AuditLogRepository(session)

    def get_balance(self, employee_id: uuid.UUID) -> CompOffBalanceRead:
        if not self.emp_repo.get_by_id(employee_id):
            raise NotFoundError(f"Employee '{employee_id}' not found")
        earned, redeemed, available = self.repo.get_balance(employee_id)
        return CompOffBalanceRead(
            employee_id=employee_id,
            earned=earned,
            redeemed=redeemed,
            available=available,
        )

    def list_entries(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        employee_id: uuid.UUID | None = None,
    ) -> tuple[Sequence[CompOffLedger], int]:
        def query_filter(stmt: Any) -> Any:
            if employee_id is not None:
                stmt = stmt.where(CompOffLedger.employee_id == employee_id)
            return stmt.order_by(CompOffLedger.entry_date.desc())

        return self.repo.list(offset=offset, limit=limit, query_modifier=query_filter)

    def create_entry(
        self, data: CompOffLedgerCreate, actor_id: uuid.UUID | None = None
    ) -> CompOffLedger:
        if not self.emp_repo.get_by_id(data.employee_id):
            raise NotFoundError(f"Employee '{data.employee_id}' not found")

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

        # 2. Automatically generate approved COMP_OFF leave for the day
        self.leave_service.create_leave(
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

        self.audit_repo.log_mutation(
            action="compoff.redeem",
            entity_type="CompOffLedger",
            entity_id=str(redeemed_entry.id),
            user_id=actor_id,
            before={"available": balance.available},
            after={"available": balance.available - 1, "date": str(data.date)},
        )
        return redeemed_entry
