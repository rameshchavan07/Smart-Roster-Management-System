"""Integration tests for Roster Compare API (Task T-518)."""

import datetime as dt
import uuid
from collections.abc import Generator

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
    tuple[TestClient, sessionmaker[Session], User, uuid.UUID, uuid.UUID], None, None
]:
    """Test client and session factory with two roster versions seeded for comparison."""
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

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: ops_user

    # Setup master data
    db: Session = testing_session_local()
    pod = Pod(name="Compare Pod")
    db.add(pod)
    db.flush()

    proc = Process(name="Process CS", code="CS")
    brand = Brand(name="Brand Alpha", code="ALP", pod_id=pod.id)
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

    emp1 = Employee(code="EMP-C1", full_name="Compare Charlie", pod_id=pod.id, weekly_off_count=1)
    emp2 = Employee(code="EMP-C2", full_name="Compare Dave", pod_id=pod.id, weekly_off_count=1)
    db.add_all([emp1, emp2])
    db.flush()

    a1 = Assignment(employee_id=emp1.id, brand_process_id=bp.id, type=AssignmentType.PRIMARY)
    a2 = Assignment(employee_id=emp2.id, brand_process_id=bp.id, type=AssignmentType.PRIMARY)
    db.add_all([a1, a2])

    # Version 1 (Baseline A)
    period_a = RosterPeriod(
        month=dt.date(2026, 12, 1),
        version=1,
        status=RosterPeriodStatus.DRAFT,
    )
    # Version 2 (Alternate B)
    period_b = RosterPeriod(
        month=dt.date(2026, 12, 1),
        version=2,
        status=RosterPeriodStatus.DRAFT,
        parent_period_id=period_a.id,
    )
    db.add_all([period_a, period_b])
    db.flush()

    # Dates: Dec 5 (Sat) and Dec 6 (Sun)
    dates = [dt.date(2026, 12, d) for d in range(1, 8)]
    for d in dates:
        # In Version A: emp1 off on Dec 5 (Sat), emp2 off on Dec 5 (Sat) -> gap on Dec 5!
        st1_a = (
            RosterEntryStatus.WEEKLY_OFF if d == dt.date(2026, 12, 5) else RosterEntryStatus.WORK
        )
        st2_a = (
            RosterEntryStatus.WEEKLY_OFF if d == dt.date(2026, 12, 5) else RosterEntryStatus.WORK
        )
        db.add(
            RosterEntry(
                roster_period_id=period_a.id,
                employee_id=emp1.id,
                date=d,
                status=st1_a,
                source=EntrySource.AUTO,
            )
        )
        db.add(
            RosterEntry(
                roster_period_id=period_a.id,
                employee_id=emp2.id,
                date=d,
                status=st2_a,
                source=EntrySource.AUTO,
            )
        )

        # In Version B: emp2 shifted weekly off to Dec 6 (Sun) -> gap resolved!
        st1_b = st1_a
        st2_b = (
            RosterEntryStatus.WEEKLY_OFF if d == dt.date(2026, 12, 6) else RosterEntryStatus.WORK
        )
        db.add(
            RosterEntry(
                roster_period_id=period_b.id,
                employee_id=emp1.id,
                date=d,
                status=st1_b,
                source=EntrySource.AUTO,
            )
        )
        db.add(
            RosterEntry(
                roster_period_id=period_b.id,
                employee_id=emp2.id,
                date=d,
                status=st2_b,
                source=EntrySource.AUTO,
            )
        )

    # Conflict in A (gap on Dec 5)
    conf_gap = RosterConflict(
        roster_period_id=period_a.id,
        code="E001",
        severity=ConflictSeverity.BLOCKING,
        brand_process_id=bp.id,
        date_from=dt.date(2026, 12, 5),
        date_to=dt.date(2026, 12, 5),
        root_causes=["NO_COVERAGE"],
        message="No coverage on 2026-12-05",
    )
    # Common warning in both A and B
    conf_common_a = RosterConflict(
        roster_period_id=period_a.id,
        code="W001",
        severity=ConflictSeverity.WARNING,
        brand_process_id=bp.id,
        employee_id=emp1.id,
        date_from=dt.date(2026, 12, 5),
        date_to=dt.date(2026, 12, 5),
        root_causes=["PREFERENCE_VIOLATED"],
        message="Preference violated",
    )
    conf_common_b = RosterConflict(
        roster_period_id=period_b.id,
        code="W001",
        severity=ConflictSeverity.WARNING,
        brand_process_id=bp.id,
        employee_id=emp1.id,
        date_from=dt.date(2026, 12, 5),
        date_to=dt.date(2026, 12, 5),
        root_causes=["PREFERENCE_VIOLATED"],
        message="Preference violated",
    )
    db.add_all([conf_gap, conf_common_a, conf_common_b])
    db.commit()

    id_a = period_a.id
    id_b = period_b.id
    db.close()

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client, testing_session_local, ops_user, id_a, id_b

    Base.metadata.drop_all(engine)
    app.dependency_overrides.clear()


def test_roster_compare_versions(
    test_setup: tuple[TestClient, sessionmaker[Session], User, uuid.UUID, uuid.UUID],
) -> None:
    """Test GET /api/v1/rosters/compare comparing Version A vs Version B."""
    client, _, _, id_a, id_b = test_setup

    res = client.get(f"/api/v1/rosters/compare?a={id_a}&b={id_b}")
    assert res.status_code == 200
    data = res.json()

    # 1. Period metadata
    assert data["period_a"]["id"] == str(id_a)
    assert data["period_b"]["id"] == str(id_b)
    assert data["period_a"]["version"] == 1
    assert data["period_b"]["version"] == 2

    # 2. Side-by-side metrics
    metrics_a = data["metrics_a"]
    metrics_b = data["metrics_b"]
    assert metrics_a["blocking_conflicts"] == 1
    assert metrics_b["blocking_conflicts"] == 0
    assert metrics_a["warning_conflicts"] == 1
    assert metrics_b["warning_conflicts"] == 1
    assert metrics_b["fairness_spread"] >= 0

    # 3. Delta
    delta = data["delta"]
    assert delta["blocking_delta"] == -1  # 0 - 1 = -1 (blocking resolved in B!)
    assert delta["total_cells_changed"] == 2  # Dec 5 and Dec 6 for emp2

    # 4. Cell diffs
    diffs = data["cell_diffs"]
    assert len(diffs) == 2
    dates_changed = {d["date"] for d in diffs}
    assert "2026-12-05" in dates_changed
    assert "2026-12-06" in dates_changed
    for item in diffs:
        assert item["employee_code"] == "EMP-C2"

    # 5. Conflict diff
    c_diff = data["conflict_diff"]
    resolved_codes = [c["code"] for c in c_diff["resolved_in_b"]]
    assert "E001" in resolved_codes
    common_codes = [c["code"] for c in c_diff["common"]]
    assert "W001" in common_codes
    assert len(c_diff["new_in_b"]) == 0


def test_roster_compare_self(
    test_setup: tuple[TestClient, sessionmaker[Session], User, uuid.UUID, uuid.UUID],
) -> None:
    """Test comparing a version with itself yields zero deltas."""
    client, _, _, id_a, _ = test_setup

    res = client.get(f"/api/v1/rosters/compare?a={id_a}&b={id_a}")
    assert res.status_code == 200
    data = res.json()
    assert data["delta"]["total_cells_changed"] == 0
    assert data["delta"]["blocking_delta"] == 0
    assert len(data["cell_diffs"]) == 0
    assert len(data["conflict_diff"]["resolved_in_b"]) == 0
    assert len(data["conflict_diff"]["new_in_b"]) == 0


def test_roster_compare_errors(
    test_setup: tuple[TestClient, sessionmaker[Session], User, uuid.UUID, uuid.UUID],
) -> None:
    """Test error handling: non-existent period, different months."""
    client, session_factory, _, id_a, _ = test_setup

    # 1. 404 on non-existent period
    fake_id = uuid.uuid4()
    res_404 = client.get(f"/api/v1/rosters/compare?a={id_a}&b={fake_id}")
    assert res_404.status_code == 404

    # 2. 422 when comparing different months
    db = session_factory()
    nov_period = RosterPeriod(
        month=dt.date(2026, 11, 1),
        version=1,
        status=RosterPeriodStatus.DRAFT,
    )
    db.add(nov_period)
    db.commit()
    nov_id = nov_period.id
    db.close()

    res_diff_month = client.get(f"/api/v1/rosters/compare?a={id_a}&b={nov_id}")
    assert res_diff_month.status_code == 422
    assert "different months" in res_diff_month.json()["error"]["message"]
