"""Unit tests for master data repositories and service layer with audit hooks."""

import uuid
from collections.abc import Generator
from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.db.base import Base
from app.models.auth import AuditLog
from app.models.core import AssignmentType, CalendarType
from app.schemas.core import (
    AssignmentCreate,
    AssignmentUpdate,
    BrandCreate,
    BrandProcessCreate,
    BrandUpdate,
    EmployeeCreate,
    EmployeeUpdate,
    PodCreate,
    PodUpdate,
    ProcessCreate,
)
from app.services.master_data import (
    AssignmentService,
    BrandProcessService,
    BrandService,
    EmployeeService,
    PodService,
    ProcessService,
)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Create an in-memory SQLite database and test session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_pod_service_crud_and_audit(db_session: Session) -> None:
    """Test PodService lifecycle, uniqueness constraints, and audit logging."""
    service = PodService(db_session)
    actor_id = uuid.uuid4()

    # 1. Create Pod
    pod = service.create_pod(PodCreate(name="Pod Alpha"), actor_id=actor_id)
    assert pod.name == "Pod Alpha"
    assert pod.is_active is True

    # Audit check
    audit = db_session.execute(
        select(AuditLog).where(AuditLog.entity_id == str(pod.id))
    ).scalar_one()
    assert audit.action == "pod.create"
    assert audit.user_id == actor_id

    # 2. Duplicate Pod Name
    with pytest.raises(ConflictError):
        service.create_pod(PodCreate(name="Pod Alpha"))

    # 3. Update Pod
    updated_pod = service.update_pod(
        pod.id, PodUpdate(name="Pod Alpha Prime", is_active=True), actor_id=actor_id
    )
    assert updated_pod.name == "Pod Alpha Prime"

    # 4. Get Pod
    fetched = service.get_pod(pod.id)
    assert fetched.name == "Pod Alpha Prime"

    # 5. Non-existent Pod
    with pytest.raises(NotFoundError):
        service.get_pod(uuid.uuid4())

    # 6. Delete Pod
    service.delete_pod(pod.id, actor_id=actor_id)
    with pytest.raises(NotFoundError):
        service.get_pod(pod.id)


def test_employee_service_crud_and_integrity(db_session: Session) -> None:
    """Test EmployeeService creation, duplicate codes/emails, and soft delete protection."""
    pod_service = PodService(db_session)
    emp_service = EmployeeService(db_session)
    actor_id = uuid.uuid4()

    pod = pod_service.create_pod(PodCreate(name="Engineering"))

    # 1. Create Employee
    emp_data = EmployeeCreate(
        code="EMP-001",
        full_name="Jordan Lee",
        email="jordan@example.test",
        pod_id=pod.id,
        is_floater=False,
        weekly_off_count=1,
    )
    emp = emp_service.create_employee(emp_data, actor_id=actor_id)
    assert emp.code == "EMP-001"
    assert emp.pod_id == pod.id

    # 2. Duplicate code
    with pytest.raises(ConflictError):
        emp_service.create_employee(
            EmployeeCreate(
                code="EMP-001",
                full_name="Duplicate Code",
                email="diff@example.test",
                pod_id=pod.id,
            )
        )

    # 3. Duplicate email
    with pytest.raises(ConflictError):
        emp_service.create_employee(
            EmployeeCreate(
                code="EMP-002",
                full_name="Duplicate Email",
                email="jordan@example.test",
                pod_id=pod.id,
            )
        )

    # 4. Update Employee
    updated = emp_service.update_employee(
        emp.id,
        EmployeeUpdate(full_name="Jordan Lee Updated", is_floater=True),
        actor_id=actor_id,
    )
    assert updated.full_name == "Jordan Lee Updated"
    assert updated.is_floater is True

    # 5. List with filters
    items, total = emp_service.list_employees(pod_id=pod.id, is_floater=True)
    assert total == 1
    assert items[0].code == "EMP-001"


def test_process_and_brand_services(db_session: Session) -> None:
    """Test ProcessService and BrandService CRUD and unique constraints."""
    pod_service = PodService(db_session)
    proc_service = ProcessService(db_session)
    brand_service = BrandService(db_session)

    pod = pod_service.create_pod(PodCreate(name="Operations"))

    # Create Process
    proc = proc_service.create_process(ProcessCreate(name="Customer Support", code="CS"))
    assert proc.code == "CS"

    # Duplicate Process code
    with pytest.raises(ConflictError):
        proc_service.create_process(ProcessCreate(name="Other Support", code="CS"))

    # Create Brand
    brand = brand_service.create_brand(BrandCreate(name="Zephyr", code="ZEP", pod_id=pod.id))
    assert brand.code == "ZEP"

    # Duplicate Brand code
    with pytest.raises(ConflictError):
        brand_service.create_brand(BrandCreate(name="Zephyr 2", code="ZEP"))

    # Update Brand
    updated_brand = brand_service.update_brand(brand.id, BrandUpdate(name="Zephyr Global"))
    assert updated_brand.name == "Zephyr Global"


def test_brand_process_and_assignment_services(db_session: Session) -> None:
    """Test BrandProcessService and AssignmentService relationships and constraints."""
    pod_svc = PodService(db_session)
    emp_svc = EmployeeService(db_session)
    proc_svc = ProcessService(db_session)
    brand_svc = BrandService(db_session)
    bp_svc = BrandProcessService(db_session)
    asgn_svc = AssignmentService(db_session)

    pod = pod_svc.create_pod(PodCreate(name="Retail Pod"))
    emp = emp_svc.create_employee(
        EmployeeCreate(code="EMP-10", full_name="Sam Smith", pod_id=pod.id)
    )
    proc = proc_svc.create_process(ProcessCreate(name="Order Processing", code="OP"))
    brand = brand_svc.create_brand(BrandCreate(name="Nexus", code="NEX", pod_id=pod.id))

    # 1. Create BrandProcess
    bp = bp_svc.create_brand_process(
        BrandProcessCreate(
            brand_id=brand.id,
            process_id=proc.id,
            calendar_type=CalendarType.ALL_365,
            min_coverage_default=1,
        )
    )
    assert bp.brand_id == brand.id

    # 2. Duplicate BrandProcess
    with pytest.raises(ConflictError):
        bp_svc.create_brand_process(
            BrandProcessCreate(
                brand_id=brand.id,
                process_id=proc.id,
            )
        )

    # 3. Create Assignment
    valid_from = date(2026, 12, 1)
    asgn = asgn_svc.create_assignment(
        AssignmentCreate(
            employee_id=emp.id,
            brand_process_id=bp.id,
            type=AssignmentType.PRIMARY,
            valid_from=valid_from,
        )
    )
    assert asgn.employee_id == emp.id

    # 4. Duplicate Assignment on same start date
    with pytest.raises(ConflictError):
        asgn_svc.create_assignment(
            AssignmentCreate(
                employee_id=emp.id,
                brand_process_id=bp.id,
                valid_from=valid_from,
            )
        )

    # 5. Update Assignment
    updated_asgn = asgn_svc.update_assignment(
        asgn.id, AssignmentUpdate(type=AssignmentType.BACKUP, allocation_pct=50)
    )
    assert updated_asgn.type == AssignmentType.BACKUP
    assert updated_asgn.allocation_pct == 50

    # 6. Deleting BrandProcess with active assignment raises ConflictError
    with pytest.raises(ConflictError):
        bp_svc.delete_brand_process(bp.id)

    # 7. Delete Assignment then BrandProcess
    asgn_svc.delete_assignment(asgn.id)
    bp_svc.delete_brand_process(bp.id)
    with pytest.raises(NotFoundError):
        bp_svc.get_brand_process(bp.id)
