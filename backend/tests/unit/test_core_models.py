"""Unit tests for core SQLAlchemy 2.0 ORM models and relationships."""

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
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


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Create an in-memory SQLite database and provide a test session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_core_table_metadata() -> None:
    """Verify that all core tables are registered on Base.metadata."""
    table_names = set(Base.metadata.tables.keys())
    expected = {"pods", "employees", "processes", "brands", "brand_processes", "assignments"}
    assert expected.issubset(table_names)


def test_core_model_relationships(db_session: Session) -> None:
    """Test full CRUD and bidirectional relationship navigation across core models."""
    # 1. Create Pod
    pod = Pod(name="Pod Alpha")
    db_session.add(pod)
    db_session.flush()

    # 2. Create Employee
    emp = Employee(
        code="EMP-001",
        full_name="Riya Shah",
        email="riya@example.test",
        pod_id=pod.id,
        is_floater=False,
    )
    db_session.add(emp)
    db_session.flush()

    # 3. Assign lead
    pod.lead_employee_id = emp.id
    db_session.flush()

    # 4. Create Process
    proc = Process(name="Customer Support", code="CS")
    db_session.add(proc)

    # 5. Create Brand
    brand = Brand(name="Aurora", code="AURORA", pod_id=pod.id)
    db_session.add(brand)
    db_session.flush()

    # 6. Create BrandProcess
    bp = BrandProcess(
        brand_id=brand.id,
        process_id=proc.id,
        calendar_type=CalendarType.ALL_365,
        min_coverage_default=1,
    )
    db_session.add(bp)
    db_session.flush()

    # 7. Create Assignment
    assignment = Assignment(
        employee_id=emp.id,
        brand_process_id=bp.id,
        type=AssignmentType.PRIMARY,
    )
    db_session.add(assignment)
    db_session.commit()

    # Test relationship navigation
    queried_pod = db_session.execute(select(Pod).where(Pod.name == "Pod Alpha")).scalar_one()
    assert len(queried_pod.members) == 1
    assert queried_pod.members[0].full_name == "Riya Shah"
    assert queried_pod.lead is not None
    assert queried_pod.lead.code == "EMP-001"
    assert len(queried_pod.brands) == 1
    assert queried_pod.brands[0].name == "Aurora"

    queried_emp = db_session.execute(
        select(Employee).where(Employee.code == "EMP-001")
    ).scalar_one()
    assert queried_emp.pod.name == "Pod Alpha"
    assert len(queried_emp.assignments) == 1
    assert queried_emp.assignments[0].brand_process.brand.name == "Aurora"
    assert queried_emp.assignments[0].brand_process.process.code == "CS"


def test_unique_constraints(db_session: Session) -> None:
    """Verify unique constraints on employee code and (brand_id, process_id)."""
    pod = Pod(name="Pod Beta")
    db_session.add(pod)
    db_session.flush()

    emp1 = Employee(code="EMP-DUP", full_name="User 1", pod_id=pod.id)
    db_session.add(emp1)
    db_session.commit()

    # Duplicate employee code
    emp2 = Employee(code="EMP-DUP", full_name="User 2", pod_id=pod.id)
    db_session.add(emp2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Duplicate brand_process (brand_id, process_id)
    brand = Brand(name="Brand X", code="BX")
    proc = Process(name="Returns", code="RET")
    db_session.add_all([brand, proc])
    db_session.flush()

    bp1 = BrandProcess(brand_id=brand.id, process_id=proc.id)
    db_session.add(bp1)
    db_session.commit()

    bp2 = BrandProcess(brand_id=brand.id, process_id=proc.id)
    db_session.add(bp2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
