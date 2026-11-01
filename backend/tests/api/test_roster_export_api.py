"""Integration tests for Roster CSV/XLSX Export API (Task T-517)."""

import datetime as dt
import io
import uuid
from collections.abc import Generator

import openpyxl
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.auth import User, UserRole
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
from app.models.roster import (
    ConflictSeverity,
    EntrySource,
    RosterConflict,
    RosterEntry,
    RosterEntryStatus,
    RosterPeriod,
    RosterPeriodStatus,
)


@pytest.fixture
def test_setup() -> Generator[
    tuple[TestClient, sessionmaker[Session], User, uuid.UUID], None, None
]:
    """Test client and session factory with pre-populated roster data."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    import app.models  # noqa: F401

    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    ops_user = User(
        id=uuid.uuid4(),
        email="ops.manager@example.com",
        password_hash="test_hash",
        role=UserRole.OPS_MANAGER,
        is_active=True,
    )

    def override_get_current_user() -> User:
        return ops_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    # Seed master data & roster period
    db: Session = testing_session_local()
    pod = Pod(name="Export Pod")
    db.add(pod)
    db.flush()

    proc = Process(name="Export Process", code="EXP_PR")
    brand = Brand(name="Export Brand", code="EXP_BR", pod_id=pod.id)
    db.add_all([proc, brand])
    db.flush()

    bp = BrandProcess(
        brand_id=brand.id,
        process_id=proc.id,
        calendar_type=CalendarType.ALL_365,
        min_coverage_default=1,
    )
    db.add(bp)
    db.flush()

    emp1 = Employee(code="EMP-E1", full_name="Export Alice", pod_id=pod.id, weekly_off_count=1)
    emp2 = Employee(code="EMP-E2", full_name="Export Bob", pod_id=pod.id, weekly_off_count=1)
    db.add_all([emp1, emp2])
    db.flush()

    a1 = Assignment(employee_id=emp1.id, brand_process_id=bp.id, type=AssignmentType.PRIMARY)
    a2 = Assignment(employee_id=emp2.id, brand_process_id=bp.id, type=AssignmentType.PRIMARY)
    db.add_all([a1, a2])

    period = RosterPeriod(
        month=dt.date(2026, 12, 1),
        version=1,
        status=RosterPeriodStatus.DRAFT,
        is_stale=False,
    )
    db.add(period)
    db.flush()

    # Add entries for Dec 1-7
    for day in range(1, 8):
        cur_d = dt.date(2026, 12, day)
        st1 = RosterEntryStatus.WORK if day != 4 else RosterEntryStatus.WEEKLY_OFF
        st2 = RosterEntryStatus.WORK if day != 5 else RosterEntryStatus.WEEKLY_OFF
        db.add(
            RosterEntry(
                roster_period_id=period.id,
                employee_id=emp1.id,
                date=cur_d,
                status=st1,
                source=EntrySource.AUTO,
            )
        )
        db.add(
            RosterEntry(
                roster_period_id=period.id,
                employee_id=emp2.id,
                date=cur_d,
                status=st2,
                source=EntrySource.AUTO,
            )
        )

    # Add a conflict
    conflict = RosterConflict(
        roster_period_id=period.id,
        code="W001",
        severity=ConflictSeverity.WARNING,
        brand_process_id=bp.id,
        employee_id=emp1.id,
        date_from=dt.date(2026, 12, 4),
        date_to=dt.date(2026, 12, 4),
        root_causes=["PREFERENCE_VIOLATED"],
        message="Preferred off day violated",
    )
    db.add(conflict)
    db.commit()
    period_id = period.id
    db.close()

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client, testing_session_local, ops_user, period_id

    Base.metadata.drop_all(engine)
    app.dependency_overrides.clear()


def test_export_grid_csv(
    test_setup: tuple[TestClient, sessionmaker[Session], User, uuid.UUID],
) -> None:
    """Test exporting monthly roster grid as CSV."""
    client, _, _, period_id = test_setup
    res = client.get(f"/api/v1/rosters/{period_id}/export?format=csv&view=grid")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "Content-Disposition" in res.headers
    assert "roster_2026-12_v1_grid.csv" in res.headers["Content-Disposition"]

    content = res.content.decode("utf-8-sig")
    assert "Employee Code,Employee Name,Pod,Primary Assignments" in content
    assert "EMP-E1,Export Alice,Export Pod" in content
    assert "EMP-E2,Export Bob,Export Pod" in content
    # Status letter code checks
    assert "W" in content
    assert "WO" in content


def test_export_grid_xlsx(
    test_setup: tuple[TestClient, sessionmaker[Session], User, uuid.UUID],
) -> None:
    """Test exporting monthly roster grid as XLSX."""
    client, _, _, period_id = test_setup
    res = client.get(f"/api/v1/rosters/{period_id}/export?format=xlsx&view=grid")
    assert res.status_code == 200
    assert (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        in res.headers["content-type"]
    )
    assert "roster_2026-12_v1_grid.xlsx" in res.headers["Content-Disposition"]

    wb = openpyxl.load_workbook(io.BytesIO(res.content))
    assert "Monthly Roster" in wb.sheetnames
    ws = wb["Monthly Roster"]
    assert ws.cell(row=1, column=1).value == "Employee Code"
    assert ws.cell(row=2, column=1).value in ("EMP-E1", "EMP-E2")


def test_export_day_csv_and_xlsx(
    test_setup: tuple[TestClient, sessionmaker[Session], User, uuid.UUID],
) -> None:
    """Test exporting day view in CSV and XLSX."""
    client, _, _, period_id = test_setup

    # CSV
    res_csv = client.get(f"/api/v1/rosters/{period_id}/export?format=csv&view=day&date=2026-12-01")
    assert res_csv.status_code == 200
    assert "Date,Brand,Process" in res_csv.content.decode("utf-8-sig")
    assert "Export Brand,Export Process" in res_csv.content.decode("utf-8-sig")

    # XLSX
    res_xlsx = client.get(
        f"/api/v1/rosters/{period_id}/export?format=xlsx&view=day&date=2026-12-01"
    )
    assert res_xlsx.status_code == 200
    wb = openpyxl.load_workbook(io.BytesIO(res_xlsx.content))
    assert "Day 2026-12-01" in wb.sheetnames


def test_export_coverage_csv_and_xlsx(
    test_setup: tuple[TestClient, sessionmaker[Session], User, uuid.UUID],
) -> None:
    """Test exporting coverage view in CSV and XLSX."""
    client, _, _, period_id = test_setup

    # CSV
    res_csv = client.get(f"/api/v1/rosters/{period_id}/export?format=csv&view=coverage")
    assert res_csv.status_code == 200
    assert "Required Headcount,Actual Headcount,Shortfall" in res_csv.content.decode("utf-8-sig")

    # XLSX
    res_xlsx = client.get(f"/api/v1/rosters/{period_id}/export?format=xlsx&view=coverage")
    assert res_xlsx.status_code == 200
    wb = openpyxl.load_workbook(io.BytesIO(res_xlsx.content))
    assert "Coverage Summary" in wb.sheetnames


def test_export_conflicts_csv_and_xlsx(
    test_setup: tuple[TestClient, sessionmaker[Session], User, uuid.UUID],
) -> None:
    """Test exporting conflicts report in CSV and XLSX."""
    client, _, _, period_id = test_setup

    # CSV
    res_csv = client.get(f"/api/v1/rosters/{period_id}/export?format=csv&view=conflicts")
    assert res_csv.status_code == 200
    content = res_csv.content.decode("utf-8-sig")
    assert "W001,WARNING" in content
    assert "Preferred off day violated" in content

    # XLSX
    res_xlsx = client.get(f"/api/v1/rosters/{period_id}/export?format=xlsx&view=conflicts")
    assert res_xlsx.status_code == 200
    wb = openpyxl.load_workbook(io.BytesIO(res_xlsx.content))
    assert "Conflicts Report" in wb.sheetnames


def test_export_validation_errors(
    test_setup: tuple[TestClient, sessionmaker[Session], User, uuid.UUID],
) -> None:
    """Test negative cases: invalid format, invalid view, non-existent roster."""
    client, _, _, period_id = test_setup

    # Invalid format
    res_fmt = client.get(f"/api/v1/rosters/{period_id}/export?format=pdf&view=grid")
    assert res_fmt.status_code == 422

    # Invalid view
    res_vw = client.get(f"/api/v1/rosters/{period_id}/export?format=csv&view=nonexistent")
    assert res_vw.status_code == 422

    # Non-existent period
    fake_id = uuid.uuid4()
    res_404 = client.get(f"/api/v1/rosters/{fake_id}/export?format=csv&view=grid")
    assert res_404.status_code == 404
