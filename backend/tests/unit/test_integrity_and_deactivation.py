"""Unit tests for soft-delete, deactivation, and integrity rules (Task T-310).

Validates:
1. Deactivation: Inactive entities cannot be linked to new relations (Pod, Employee, Brand, Process, BrandProcess).
2. 409 on Delete with History: Pod, Employee, Brand, Process, BrandProcess, Approved Leave rejection.
3. Leave Overlap Rules: Start/end boundaries, exact match, subset/superset, touch, cancelled/rejected leaves, and approval collision.
"""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.errors import ConflictError
from app.db.base import Base
from app.models.core import AssignmentType, CalendarType
from app.models.rules import (
    CompOffKind,
    LeaveStatus,
    PreferenceKind,
    WeeklyOffMode,
)
from app.schemas.core import (
    AssignmentCreate,
    BrandCreate,
    BrandProcessCreate,
    BrandProcessUpdate,
    BrandUpdate,
    EmployeeCreate,
    EmployeeUpdate,
    PodCreate,
    PodUpdate,
    ProcessCreate,
    ProcessUpdate,
)
from app.schemas.rules import (
    CompOffLedgerCreate,
    CoverageRuleCreate,
    EmployeePreferenceCreate,
    HolidayCreate,
    LeaveCreate,
    LeaveUpdate,
    WeeklyOffRuleCreate,
)
from app.services.master_data import (
    AssignmentService,
    BrandProcessService,
    BrandService,
    EmployeeService,
    PodService,
    ProcessService,
)
from app.services.rules import (
    CompOffService,
    CoverageRuleService,
    EmployeePreferenceService,
    HolidayService,
    LeaveService,
    WeeklyOffRuleService,
)


@pytest.fixture
def db_session() -> Session:
    """Create an isolated in-memory SQLite database and session for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_deactivation_and_inactive_relation_guards(db_session: Session) -> None:
    """Verify that deactivated entities are rejected when referenced in new records."""
    pod_svc = PodService(db_session)
    emp_svc = EmployeeService(db_session)
    brand_svc = BrandService(db_session)
    proc_svc = ProcessService(db_session)
    bp_svc = BrandProcessService(db_session)
    asgn_svc = AssignmentService(db_session)
    leave_svc = LeaveService(db_session)
    wo_svc = WeeklyOffRuleService(db_session)
    pref_svc = EmployeePreferenceService(db_session)
    holiday_svc = HolidayService(db_session)
    cov_svc = CoverageRuleService(db_session)
    compoff_svc = CompOffService(db_session)

    # 1. Inactive Pod guards
    pod = pod_svc.create_pod(PodCreate(name="Inactive Pod"))
    pod_svc.update_pod(pod.id, PodUpdate(is_active=False))

    with pytest.raises(ConflictError, match="Cannot assign employee to inactive pod"):
        emp_svc.create_employee(EmployeeCreate(code="EMP-INACT", full_name="Ghost", pod_id=pod.id))

    with pytest.raises(ConflictError, match="Cannot assign brand to inactive pod"):
        brand_svc.create_brand(BrandCreate(code="BRD-INACT", name="Ghost Brand", pod_id=pod.id))

    # Create an active pod for remaining tests
    active_pod = pod_svc.create_pod(PodCreate(name="Active Pod"))

    # 2. Inactive Employee guards
    emp = emp_svc.create_employee(
        EmployeeCreate(code="EMP-ACTIVE", full_name="Active Person", pod_id=active_pod.id)
    )
    emp_svc.update_employee(emp.id, EmployeeUpdate(is_active=False))

    proc = proc_svc.create_process(ProcessCreate(code="CS", name="Customer Support"))
    brand = brand_svc.create_brand(
        BrandCreate(code="BRD-ACT", name="Active Brand", pod_id=active_pod.id)
    )
    bp = bp_svc.create_brand_process(
        BrandProcessCreate(
            brand_id=brand.id,
            process_id=proc.id,
            calendar_type=CalendarType.ALL_365,
        )
    )

    with pytest.raises(ConflictError, match="Cannot create assignment for inactive employee"):
        asgn_svc.create_assignment(
            AssignmentCreate(
                employee_id=emp.id,
                brand_process_id=bp.id,
                type=AssignmentType.PRIMARY,
            )
        )

    with pytest.raises(ConflictError, match="Cannot request leave for inactive employee"):
        leave_svc.create_leave(
            LeaveCreate(
                employee_id=emp.id,
                start_date=dt.date(2026, 12, 1),
                end_date=dt.date(2026, 12, 2),
            )
        )

    with pytest.raises(ConflictError, match="Cannot create weekly off rule for inactive employee"):
        wo_svc.create_weekly_off_rule(
            WeeklyOffRuleCreate(
                employee_id=emp.id,
                mode=WeeklyOffMode.FIXED_MANDATORY,
                weekdays=[0],
            )
        )

    with pytest.raises(ConflictError, match="Cannot create preference for inactive employee"):
        pref_svc.create_preference(
            EmployeePreferenceCreate(
                employee_id=emp.id,
                kind=PreferenceKind.PREFERRED_OFF_WEEKDAY,
                value={"weekday": 0},
            )
        )

    with pytest.raises(ConflictError, match="Cannot add comp-off entry for inactive employee"):
        compoff_svc.create_entry(
            CompOffLedgerCreate(
                employee_id=emp.id,
                entry_date=dt.date(2026, 12, 1),
                kind=CompOffKind.EARNED,
            )
        )

    # 3. Inactive Brand & Process guards
    proc_inact = proc_svc.create_process(ProcessCreate(code="RET", name="Retention"))
    proc_svc.update_process(proc_inact.id, ProcessUpdate(is_active=False))

    with pytest.raises(ConflictError, match="Cannot configure inactive process"):
        bp_svc.create_brand_process(
            BrandProcessCreate(
                brand_id=brand.id,
                process_id=proc_inact.id,
                calendar_type=CalendarType.ALL_365,
            )
        )

    brand_svc.update_brand(brand.id, BrandUpdate(is_active=False))
    with pytest.raises(ConflictError, match="Cannot configure process for inactive brand"):
        bp_svc.create_brand_process(
            BrandProcessCreate(
                brand_id=brand.id,
                process_id=proc.id,
                calendar_type=CalendarType.ALL_365,
            )
        )

    with pytest.raises(ConflictError, match="Cannot create holiday for inactive brand"):
        holiday_svc.create_holiday(
            HolidayCreate(
                name="Brand Anniversary",
                date=dt.date(2026, 12, 15),
                brand_id=brand.id,
            )
        )

    # 4. Inactive BrandProcess guards
    bp_svc.update_brand_process(bp.id, BrandProcessUpdate(is_active=False))

    active_emp = emp_svc.create_employee(
        EmployeeCreate(code="EMP-ALIVE", full_name="Alive Person", pod_id=active_pod.id)
    )

    with pytest.raises(ConflictError, match="Cannot create assignment for inactive brand process"):
        asgn_svc.create_assignment(
            AssignmentCreate(
                employee_id=active_emp.id,
                brand_process_id=bp.id,
                type=AssignmentType.PRIMARY,
            )
        )

    with pytest.raises(
        ConflictError, match="Cannot create coverage rule for inactive brand process"
    ):
        cov_svc.create_coverage_rule(
            CoverageRuleCreate(
                brand_process_id=bp.id,
                weekday=0,
                min_staff=2,
            )
        )


def test_409_on_delete_with_history(db_session: Session) -> None:
    """Verify that deleting an entity that has history returns 409 and offers deactivation."""
    pod_svc = PodService(db_session)
    emp_svc = EmployeeService(db_session)
    brand_svc = BrandService(db_session)
    proc_svc = ProcessService(db_session)
    bp_svc = BrandProcessService(db_session)
    asgn_svc = AssignmentService(db_session)
    leave_svc = LeaveService(db_session)
    compoff_svc = CompOffService(db_session)
    holiday_svc = HolidayService(db_session)

    pod = pod_svc.create_pod(PodCreate(name="Main Pod"))
    emp = emp_svc.create_employee(
        EmployeeCreate(code="EMP-HIST", full_name="Hist User", pod_id=pod.id)
    )
    brand = brand_svc.create_brand(BrandCreate(code="BRD-HIST", name="Hist Brand", pod_id=pod.id))
    proc = proc_svc.create_process(ProcessCreate(code="CS", name="Customer Support"))
    bp = bp_svc.create_brand_process(
        BrandProcessCreate(
            brand_id=brand.id,
            process_id=proc.id,
            calendar_type=CalendarType.ALL_365,
        )
    )
    asgn = asgn_svc.create_assignment(
        AssignmentCreate(
            employee_id=emp.id,
            brand_process_id=bp.id,
            type=AssignmentType.PRIMARY,
        )
    )

    # 1. Pod cannot be deleted with employees or brands
    with pytest.raises(
        ConflictError, match="Cannot delete pod with associated employees or brands"
    ):
        pod_svc.delete_pod(pod.id)

    # 2. Employee cannot be deleted with assignments
    with pytest.raises(
        ConflictError, match="Cannot delete employee with associated historical records"
    ):
        emp_svc.delete_employee(emp.id)

    # 3. Brand cannot be deleted with brand-processes
    with pytest.raises(
        ConflictError, match="Cannot delete brand with associated processes or holidays"
    ):
        brand_svc.delete_brand(brand.id)

    # 4. Process cannot be deleted with brand-processes
    with pytest.raises(ConflictError, match="Cannot delete process configured for active brands"):
        proc_svc.delete_process(proc.id)

    # 5. BrandProcess cannot be deleted with assignments
    with pytest.raises(
        ConflictError, match="Cannot delete brand process with active staff assignments"
    ):
        bp_svc.delete_brand_process(bp.id)

    # Delete assignment to free up the link
    asgn_svc.delete_assignment(asgn.id)

    # Add leave to employee -> still blocked
    leave = leave_svc.create_leave(
        LeaveCreate(
            employee_id=emp.id,
            start_date=dt.date(2026, 12, 5),
            end_date=dt.date(2026, 12, 6),
            status=LeaveStatus.APPROVED,
        )
    )
    with pytest.raises(
        ConflictError, match="Cannot delete employee with associated historical records"
    ):
        emp_svc.delete_employee(emp.id)

    # 6. Approved leave cannot be deleted directly
    with pytest.raises(
        ConflictError, match="Cannot delete an approved leave. Cancel the leave instead."
    ):
        leave_svc.delete_leave(leave.id)

    # Cancel leave -> deletion of cancelled leave succeeds
    leave_svc.set_leave_status(leave.id, LeaveStatus.CANCELLED)
    leave_svc.delete_leave(leave.id)

    # Add comp-off -> still blocked
    compoff = compoff_svc.create_entry(
        CompOffLedgerCreate(
            employee_id=emp.id,
            entry_date=dt.date(2026, 12, 25),
            kind=CompOffKind.EARNED,
        )
    )
    with pytest.raises(
        ConflictError, match="Cannot delete employee with associated historical records"
    ):
        emp_svc.delete_employee(emp.id)

    # Remove comp-off to clean employee
    db_session.delete(compoff)
    db_session.commit()

    # Now employee has no history and can be safely deleted
    emp_svc.delete_employee(emp.id)

    # Brand with holiday cannot be deleted
    bp_svc.delete_brand_process(bp.id)
    h = holiday_svc.create_holiday(
        HolidayCreate(name="Regional", date=dt.date(2026, 12, 10), brand_id=brand.id)
    )
    with pytest.raises(
        ConflictError, match="Cannot delete brand with associated processes or holidays"
    ):
        brand_svc.delete_brand(brand.id)

    holiday_svc.delete_holiday(h.id)
    brand_svc.delete_brand(brand.id)


def test_leave_overlap_boundary_and_state_rules(db_session: Session) -> None:
    """Verify leave overlap detection across boundary conditions and workflow state transitions."""
    pod_svc = PodService(db_session)
    emp_svc = EmployeeService(db_session)
    leave_svc = LeaveService(db_session)

    pod = pod_svc.create_pod(PodCreate(name="Leave Pod"))
    emp = emp_svc.create_employee(
        EmployeeCreate(code="EMP-LEAVE", full_name="Leave Tester", pod_id=pod.id)
    )

    # Base Leave: Dec 10 to Dec 15 (inclusive, 6 days)
    base_leave = leave_svc.create_leave(
        LeaveCreate(
            employee_id=emp.id,
            start_date=dt.date(2026, 12, 10),
            end_date=dt.date(2026, 12, 15),
            status=LeaveStatus.REQUESTED,
            note="Base Leave",
        )
    )

    # 1. Exact match overlap
    with pytest.raises(ConflictError, match="Leave request conflicts with existing leave"):
        leave_svc.create_leave(
            LeaveCreate(
                employee_id=emp.id,
                start_date=dt.date(2026, 12, 10),
                end_date=dt.date(2026, 12, 15),
            )
        )

    # 2. Subset range (Dec 12 - Dec 13)
    with pytest.raises(ConflictError, match="Leave request conflicts with existing leave"):
        leave_svc.create_leave(
            LeaveCreate(
                employee_id=emp.id,
                start_date=dt.date(2026, 12, 12),
                end_date=dt.date(2026, 12, 13),
            )
        )

    # 3. Superset range (Dec 8 - Dec 18)
    with pytest.raises(ConflictError, match="Leave request conflicts with existing leave"):
        leave_svc.create_leave(
            LeaveCreate(
                employee_id=emp.id,
                start_date=dt.date(2026, 12, 8),
                end_date=dt.date(2026, 12, 18),
            )
        )

    # 4. Start touch boundary (Dec 15 - Dec 18)
    with pytest.raises(ConflictError, match="Leave request conflicts with existing leave"):
        leave_svc.create_leave(
            LeaveCreate(
                employee_id=emp.id,
                start_date=dt.date(2026, 12, 15),
                end_date=dt.date(2026, 12, 18),
            )
        )

    # 5. End touch boundary (Dec 5 - Dec 10)
    with pytest.raises(ConflictError, match="Leave request conflicts with existing leave"):
        leave_svc.create_leave(
            LeaveCreate(
                employee_id=emp.id,
                start_date=dt.date(2026, 12, 5),
                end_date=dt.date(2026, 12, 10),
            )
        )

    # 6. Non-overlapping leaves before and after succeed
    before_leave = leave_svc.create_leave(
        LeaveCreate(
            employee_id=emp.id,
            start_date=dt.date(2026, 12, 1),
            end_date=dt.date(2026, 12, 9),
        )
    )
    after_leave = leave_svc.create_leave(
        LeaveCreate(
            employee_id=emp.id,
            start_date=dt.date(2026, 12, 16),
            end_date=dt.date(2026, 12, 20),
        )
    )
    assert before_leave.id is not None
    assert after_leave.id is not None

    # 7. Updating dates to overlap another leave raises 409 Conflict
    with pytest.raises(ConflictError, match="Updated dates conflict with existing leave"):
        leave_svc.update_leave(
            after_leave.id,
            LeaveUpdate(start_date=dt.date(2026, 12, 14)),  # overlaps base_leave end (Dec 15)
        )

    # Updating self within same dates succeeds
    updated_base = leave_svc.update_leave(
        base_leave.id,
        LeaveUpdate(note="Updated note without date changes"),
    )
    assert updated_base.note == "Updated note without date changes"

    # 8. Cancelled / Rejected leaves do not block new requests
    leave_svc.set_leave_status(base_leave.id, LeaveStatus.REJECTED)
    reapply_leave = leave_svc.create_leave(
        LeaveCreate(
            employee_id=emp.id,
            start_date=dt.date(2026, 12, 10),
            end_date=dt.date(2026, 12, 15),
            status=LeaveStatus.REQUESTED,
        )
    )
    assert reapply_leave.id is not None

    # 9. Approval Collision:
    # If reapply_leave is approved, and another request was made, approving the second raises 409
    leave_svc.set_leave_status(reapply_leave.id, LeaveStatus.APPROVED)
    second_request = leave_svc.create_leave(
        LeaveCreate(
            employee_id=emp.id,
            start_date=dt.date(2026, 12, 22),
            end_date=dt.date(2026, 12, 24),
            status=LeaveStatus.REQUESTED,
        )
    )
    # Manually shift second_request dates directly to overlap approved leave
    second_request.start_date = dt.date(2026, 12, 12)
    second_request.end_date = dt.date(2026, 12, 14)
    db_session.commit()

    with pytest.raises(ConflictError, match="Cannot approve leave: overlaps with approved leave"):
        leave_svc.set_leave_status(second_request.id, LeaveStatus.APPROVED)
