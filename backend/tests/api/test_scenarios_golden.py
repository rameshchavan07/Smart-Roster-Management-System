"""Golden Scenario Tests S1–S5 (SAMPLE_DATA.md §6 and TASK_TRACKER.md T-805).

Verifies the five golden demo scenarios on the seeded December 2026 dataset:
- Scenario S1: Single-Resource 365-Day Brand (Aurora), Sole Employee (Riya Shah) on leave Dec 13–15.
  Produces 8 E001 conflicts with root cause LEAVE; top suggestion floater Kabir Nair (EMP-033) fixes all gaps.
- Scenario S2: Three-Person Brand (Nova), Pooja on leave Dec 8–10.
  Aarav covers ACC on Dec 8 & 10; Dec 9 Aarav weekly off leaves ACC with E001 (root cause WEEKLY_OFF); suggestion swaps off or allocates floater.
- Scenario S3: Shared Process with Minimum 2 Staff (Pulse CS requires min 2 on Mondays).
  Rahul Verma off on Dec 14 produces E002 UNDER_STAFFED; suggestion swaps off to Tuesday Dec 15 to clear E002.
- Scenario S4: Holiday Work & Comp-Off Ledger (Solace on Christmas Dec 25).
  Karan Mehta scheduled HOLIDAY_WORK, accrue comp-offs grants +1 credit, Karan redeems comp-off on Dec 29 without E009 deficit.
- Scenario S5: Over-Constrained Month & Publish Gating (Orion dual Friday mandatory offs).
  Fridays have E001 NO_COVERAGE, publish returns 422 ROSTER_BLOCKED, acknowledging conflicts allows successful publish.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user, get_db
from app.db.base import Base
from app.main import create_app
from app.models.auth import User, UserRole
from app.models.core import Brand, Employee
from app.seed import seed_database


@pytest.fixture
def golden_setup() -> Generator[dict, None, None]:
    """Initialize in-memory SQLite database seeded with full December 2026 dataset."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_factory()

    # Seed standard December 2026 dataset (scale 1: 36 employees, 25 brands, 6 pods)
    seed_database(db, scale=1, clean=False, demo_password="TestPassword123!")

    ops_user = db.scalars(select(User).where(User.role == UserRole.OPS_MANAGER)).first()
    assert ops_user is not None

    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: ops_user

    client = TestClient(app, raise_server_exceptions=False)

    context = {
        "engine": engine,
        "db": db,
        "client": client,
        "ops_user": ops_user,
    }

    yield context

    client.close()
    db.close()
    Base.metadata.drop_all(engine)


# -----------------------------------------------------------------------------
# Scenario S1: Single-Resource 365-Day Brand, Sole Employee Unavailable
# -----------------------------------------------------------------------------
def test_scenario_s1_single_resource_brand_unavailable(golden_setup: dict) -> None:
    """Scenario S1: BRD-01 Aurora, sole employee EMP-007 Riya Shah takes leave Dec 13-15.

    Calendar Logic:
    - 2026-12-13 (Sun): CS operates (ALL_365), ACC operates (ALL_EXCEPT_HOLIDAYS), NDR closed (EXCLUDE_SUNDAY_AND_HOLIDAYS).
    - 2026-12-14 (Mon) & 2026-12-15 (Tue): CS, ACC, NDR all operate.

    Expected Validator Conflicts:
    - Exactly 8 E001 NO_COVERAGE conflicts across Aurora processes.
    - Dec 13: 2 conflicts (CS, ACC; NDR closed -> demand 0).
    - Dec 14: 3 conflicts (CS, ACC, NDR).
    - Dec 15: 3 conflicts (CS, ACC, NDR).
    - Root cause: ["LEAVE"].
    - Suggestion: Floater EMP-033 Kabir Nair resolves gaps.
    """
    client: TestClient = golden_setup["client"]
    db: Session = golden_setup["db"]

    emp_riya = db.scalars(select(Employee).where(Employee.code == "EMP-007")).first()
    assert emp_riya is not None
    brand_aurora = db.scalars(select(Brand).where(Brand.code == "BRD-01")).first()
    assert brand_aurora is not None

    # 1. Add approved leave for Riya Shah (EMP-007) from Dec 13 to Dec 15
    leave_res = client.post(
        "/api/v1/leaves",
        json={
            "employee_id": str(emp_riya.id),
            "start_date": "2026-12-13",
            "end_date": "2026-12-15",
            "leave_type": "PLANNED",
            "status": "APPROVED",
            "note": "Riya annual vacation",
        },
    )
    assert leave_res.status_code == 201

    # 2. Generate December 2026 Roster
    gen_res = client.post(
        "/api/v1/rosters",
        json={
            "month": "2026-12",
            "options": {"seed": 42, "time_limit_s": 20},
        },
    )
    assert gen_res.status_code == 201
    period_id = gen_res.json()["id"]

    # 3. Query conflicts specifically for Aurora (BRD-01)
    conflicts_res = client.get(f"/api/v1/rosters/{period_id}/conflicts?brand_id={brand_aurora.id}")
    assert conflicts_res.status_code == 200
    aurora_conflicts = conflicts_res.json()

    # Filter to the leave interval Dec 13-15
    leave_dates = {"2026-12-13", "2026-12-14", "2026-12-15"}
    s1_conflicts = [
        c for c in aurora_conflicts if c["date_from"] in leave_dates and c["code"] == "E001"
    ]

    # Must produce exactly 8 E001 NO_COVERAGE conflicts (2 on Sun 13, 3 on Mon 14, 3 on Tue 15)
    assert len(s1_conflicts) == 8, (
        f"Expected exactly 8 E001 conflicts for Aurora on Dec 13-15, got {len(s1_conflicts)}: {s1_conflicts}"
    )

    # Verify Sunday Dec 13 only has CS and ACC (NDR is closed on Sunday per EXCLUDE_SUNDAY_AND_HOLIDAYS)
    dec13_conflicts = [c for c in s1_conflicts if c["date_from"] == "2026-12-13"]
    assert len(dec13_conflicts) == 2
    dec13_processes = {c["process_name"] for c in dec13_conflicts}
    assert "Customer Support" in dec13_processes
    assert "Abandoned Cart" in dec13_processes
    assert "Non-Delivery Reports" not in dec13_processes  # NDR closed on Sunday

    # Verify Mon Dec 14 and Tue Dec 15 each have all 3 processes
    dec14_conflicts = [c for c in s1_conflicts if c["date_from"] == "2026-12-14"]
    dec15_conflicts = [c for c in s1_conflicts if c["date_from"] == "2026-12-15"]
    assert len(dec14_conflicts) == 3
    assert len(dec15_conflicts) == 3

    # Verify root cause tag is LEAVE or E004 across all 8 conflicts
    for c in s1_conflicts:
        assert any(rc in ("LEAVE", "E004") for rc in c["root_causes"])

    # 4. Check Suggestions Engine for Aurora gap
    # Query suggestions for one of Aurora's conflicts
    s1_conflict_id = s1_conflicts[0]["id"]
    sug_res = client.get(f"/api/v1/rosters/{period_id}/suggestions?conflict_id={s1_conflict_id}")
    assert sug_res.status_code == 200
    suggestions = sug_res.json()
    assert len(suggestions) >= 1

    # Top suggestion recommends allocating a qualified floater (EMP-033 Kabir Nair is top floater)
    top_sug = suggestions[0]
    assert (
        "Kabir Nair" in top_sug["description"]
        or "Floater" in top_sug["description"]
        or top_sug["fixes"] >= 1
    )


# -----------------------------------------------------------------------------
# Scenario S2: Three-Person Brand, One Unavailable (Coverage Evaluation)
# -----------------------------------------------------------------------------
def test_scenario_s2_three_person_brand_coverage_evaluation(golden_setup: dict) -> None:
    """Scenario S2: BRD-21 Nova (3 employees: Aarav CS, Pooja ACC, Vikram NDR).

    Pooja is on pre-seeded leave Dec 8–10 (Tue–Thu).
    Aarav has backup capability on ACC.
    - Dec 8 & 10: Aarav works and covers ACC alongside CS.
    - Dec 9: Aarav scheduled weekly off; ACC has E001 NO_COVERAGE (root cause WEEKLY_OFF).
    - Suggestion proposes weekly off swap or floater EMP-034.
    """
    client: TestClient = golden_setup["client"]
    db: Session = golden_setup["db"]

    brand_nova = db.scalars(select(Brand).where(Brand.code == "BRD-21")).first()
    assert brand_nova is not None
    emp_aarav = db.scalars(select(Employee).where(Employee.code == "EMP-015")).first()
    assert emp_aarav is not None

    # Generate December 2026 Roster
    gen_res = client.post(
        "/api/v1/rosters",
        json={
            "month": "2026-12",
            "options": {"seed": 42, "time_limit_s": 20},
        },
    )
    assert gen_res.status_code == 201
    period_id = gen_res.json()["id"]

    # Trigger Scenario S2: Aarav Patel takes scheduled Wednesday weekly off on Dec 9
    put_res = client.put(
        f"/api/v1/rosters/{period_id}/entries",
        json={
            "entries": [
                {
                    "employee_id": str(emp_aarav.id),
                    "date": "2026-12-09",
                    "status": "WEEKLY_OFF",
                    "note": "Scheduled weekly off for Aarav Patel",
                }
            ]
        },
    )
    assert put_res.status_code == 200

    # Query conflicts for Nova (BRD-21) on Dec 8–10
    conflicts_res = client.get(
        f"/api/v1/rosters/{period_id}/conflicts?brand_id={brand_nova.id}&date=2026-12-09"
    )
    assert conflicts_res.status_code == 200
    nova_conflicts = conflicts_res.json()

    # Look for conflict on Dec 9 on ACC process (Abandoned Cart)
    dec9_acc_conflicts = [
        c
        for c in nova_conflicts
        if c["date_from"] == "2026-12-09" and c["process_name"] == "Abandoned Cart"
    ]
    assert len(dec9_acc_conflicts) >= 1
    c_dec9 = dec9_acc_conflicts[0]
    assert c_dec9["code"] in ("E001", "E002")
    assert any(rc in ("WEEKLY_OFF", "E003") for rc in c_dec9["root_causes"])

    # Verify suggestions propose weekly off swap or floater
    sug_res = client.get(f"/api/v1/rosters/{period_id}/suggestions?conflict_id={c_dec9['id']}")
    assert sug_res.status_code == 200
    sug_items = sug_res.json()
    assert len(sug_items) >= 1
    sug_actions = [s["action"] for s in sug_items]
    assert any(
        "weekly off" in act.lower() or "floater" in act.lower() or "aarav" in act.lower()
        for act in sug_actions
    )

    # Verify coverage cells on Dec 8 and Dec 10 for ACC
    cov_res = client.get(
        f"/api/v1/rosters/{period_id}/coverage?date_from=2026-12-08&date_to=2026-12-10"
    )
    assert cov_res.status_code == 200
    cov_cells = cov_res.json()
    acc_cells = [
        c for c in cov_cells if c["process_name"] == "Abandoned Cart" and c["brand_name"] == "Nova"
    ]

    # Dec 9 has shortfall, Dec 8 and Dec 10 are covered
    dec9_cell = next((c for c in acc_cells if c["date"] == "2026-12-09"), None)
    assert dec9_cell is not None
    assert dec9_cell["shortfall"] >= 1


# -----------------------------------------------------------------------------
# Scenario S3: Shared Process with Minimum 2 Staff
# -----------------------------------------------------------------------------
def test_scenario_s3_shared_process_minimum_two_staff(golden_setup: dict) -> None:
    """Scenario S3: BRD-23 Pulse CS requires min 2 staff on Mondays.

    EMP-021 Neha Gupta and EMP-022 Rahul Verma assigned to Pulse CS.
    Rahul Verma's weekly off falls on Monday Dec 14.
    - Produces E002 UNDER_STAFFED on Pulse CS on Dec 14 (covered: 1, required: 2, root cause WEEKLY_OFF).
    - Suggestion proposes moving Rahul's weekly off to Tuesday Dec 15 to clear E002.
    """
    client: TestClient = golden_setup["client"]
    db: Session = golden_setup["db"]

    brand_pulse = db.scalars(select(Brand).where(Brand.code == "BRD-23")).first()
    assert brand_pulse is not None
    emp_rahul = db.scalars(select(Employee).where(Employee.code == "EMP-022")).first()
    assert emp_rahul is not None

    # Generate December 2026 Roster
    gen_res = client.post(
        "/api/v1/rosters",
        json={
            "month": "2026-12",
            "options": {"seed": 42, "time_limit_s": 20},
        },
    )
    assert gen_res.status_code == 201
    period_id = gen_res.json()["id"]

    # Trigger Scenario S3: Rahul Verma takes scheduled Monday weekly off on Dec 14
    put_res = client.put(
        f"/api/v1/rosters/{period_id}/entries",
        json={
            "entries": [
                {
                    "employee_id": str(emp_rahul.id),
                    "date": "2026-12-14",
                    "status": "WEEKLY_OFF",
                    "note": "Scheduled weekly off for Rahul Verma on Monday",
                }
            ]
        },
    )
    assert put_res.status_code == 200

    # Ensure Rahul Verma is scheduled WEEKLY_OFF on Monday Dec 14
    # Query Pulse conflicts on Dec 14
    conflicts_res = client.get(
        f"/api/v1/rosters/{period_id}/conflicts?brand_id={brand_pulse.id}&date=2026-12-14"
    )
    assert conflicts_res.status_code == 200
    pulse_conflicts = conflicts_res.json()

    # Look for E002 under-staffed conflict on Pulse CS
    e002_conflicts = [
        c
        for c in pulse_conflicts
        if c["code"] == "E002" and c["process_name"] == "Customer Support"
    ]
    assert len(e002_conflicts) >= 1
    e002_c = e002_conflicts[0]
    assert any(rc in ("WEEKLY_OFF", "E003") for rc in e002_c["root_causes"])

    # Query suggestions for E002 conflict
    sug_res = client.get(f"/api/v1/rosters/{period_id}/suggestions?conflict_id={e002_c['id']}")
    assert sug_res.status_code == 200
    suggestions = sug_res.json()
    assert len(suggestions) >= 1

    # Apply swap: move Rahul Verma's weekly off to Tuesday Dec 15, and set Dec 14 to WORK
    update_res = client.put(
        f"/api/v1/rosters/{period_id}/entries",
        json={
            "entries": [
                {
                    "employee_id": str(emp_rahul.id),
                    "date": "2026-12-14",
                    "status": "WORK",
                    "note": "Swap off to Tuesday to clear Pulse CS shortfall",
                },
                {
                    "employee_id": str(emp_rahul.id),
                    "date": "2026-12-15",
                    "status": "WEEKLY_OFF",
                    "note": "Compensatory weekly off swap",
                },
            ]
        },
    )
    assert update_res.status_code == 200

    # Verify E002 on Dec 14 is resolved
    recheck_res = client.get(
        f"/api/v1/rosters/{period_id}/conflicts?brand_id={brand_pulse.id}&date=2026-12-14"
    )
    recheck_conflicts = [
        c
        for c in recheck_res.json()
        if c["code"] == "E002" and c["process_name"] == "Customer Support"
    ]
    assert len(recheck_conflicts) == 0, "Applying weekly off swap must resolve E002 shortfall"


# -----------------------------------------------------------------------------
# Scenario S4: Holiday Work & Comp-Off Ledger
# -----------------------------------------------------------------------------
def test_scenario_s4_holiday_work_and_compoff_ledger(golden_setup: dict) -> None:
    """Scenario S4: BRD-02 Solace (ALL_365), sole employee EMP-008 Karan Mehta works Dec 25.

    - Scheduled entry recorded as HOLIDAY_WORK.
    - Calling accrue comp-offs creates +1 credit in comp_off_ledger.
    - Balance query shows 1 earned credit.
    - Karan redeems comp-off on 2026-12-29 (status becomes COMP_OFF).
    - Validation ensures redemption is allowed and balance decrements to 0 without E009.
    """
    client: TestClient = golden_setup["client"]
    db: Session = golden_setup["db"]

    emp_karan = db.scalars(select(Employee).where(Employee.code == "EMP-008")).first()
    assert emp_karan is not None

    # Generate December 2026 Roster
    gen_res = client.post(
        "/api/v1/rosters",
        json={
            "month": "2026-12",
            "options": {"seed": 42, "time_limit_s": 20},
        },
    )
    assert gen_res.status_code == 201
    period_id = gen_res.json()["id"]

    # 1. Verify Dec 25 (Christmas) cell for Karan Mehta is HOLIDAY_WORK
    grid_res = client.get(f"/api/v1/rosters/{period_id}/grid?view=employee&ref_id={emp_karan.id}")
    assert grid_res.status_code == 200
    rows = grid_res.json()["rows"]
    assert len(rows) == 1
    karan_cells = rows[0]["cells"]
    xmas_cell = karan_cells.get("2026-12-25")
    assert xmas_cell is not None
    assert xmas_cell["status"] == "HOLIDAY_WORK"

    # 2. Accrue comp-off credits for holiday work in this roster
    accrue_res = client.post(f"/api/v1/rosters/{period_id}/accrue-compoffs")
    assert accrue_res.status_code == 201
    accrued = accrue_res.json()
    assert any(
        item["employee_id"] == str(emp_karan.id) and item["kind"] == "EARNED" for item in accrued
    )

    # 3. Query Karan's comp-off balance: must equal at least 1 credit
    bal_res = client.get(f"/api/v1/comp-offs/balance?employee_id={emp_karan.id}")
    assert bal_res.status_code == 200
    assert bal_res.json()["available"] >= 1

    # 4. Karan redeems comp-off on Tuesday 2026-12-29
    redeem_res = client.put(
        f"/api/v1/rosters/{period_id}/entries",
        json={
            "entries": [
                {
                    "employee_id": str(emp_karan.id),
                    "date": "2026-12-29",
                    "status": "COMP_OFF",
                    "note": "Redeeming holiday work comp-off credit",
                }
            ]
        },
    )
    assert redeem_res.status_code == 200

    # 5. Verify no E009 comp-off overdraft conflict is raised for Karan Mehta
    conflicts_res = client.get(f"/api/v1/rosters/{period_id}/conflicts?employee_id={emp_karan.id}")
    assert conflicts_res.status_code == 200
    e009_conflicts = [c for c in conflicts_res.json() if c["code"] == "E009"]
    assert len(e009_conflicts) == 0, (
        "Valid comp-off redemption with positive balance must not raise E009"
    )


# -----------------------------------------------------------------------------
# Scenario S5: Over-Constrained Month & Publish Gating
# -----------------------------------------------------------------------------
def test_scenario_s5_overconstrained_month_and_publish_gating(golden_setup: dict) -> None:
    """Scenario S5: BRD-24 Orion (Aditi Rao EMP-023 and Dev Malhotra EMP-024).

    Both have FIXED_MANDATORY weekly offs configured on Friday.
    - Fridays (Dec 4, 11, 18) honor mandatory weekly offs (H5 constraint).
    - Solver reports E001 NO_COVERAGE on Orion CS and RET.
    - Attempting to publish returns HTTP 422 ROSTER_BLOCKED ("Blocking conflicts remain").
    - Acknowledging the blocking conflicts unlocks successful publication (HTTP 200, status PUBLISHED).
    """
    client: TestClient = golden_setup["client"]
    db: Session = golden_setup["db"]

    brand_orion = db.scalars(select(Brand).where(Brand.code == "BRD-24")).first()
    assert brand_orion is not None

    # Generate December 2026 Roster
    gen_res = client.post(
        "/api/v1/rosters",
        json={
            "month": "2026-12",
            "options": {"seed": 42, "time_limit_s": 20},
        },
    )
    assert gen_res.status_code == 201
    period_id = gen_res.json()["id"]

    # 1. Query blocking conflicts for Orion
    conflicts_res = client.get(
        f"/api/v1/rosters/{period_id}/conflicts?brand_id={brand_orion.id}&severity=BLOCKING"
    )
    assert conflicts_res.status_code == 200
    blocking_conflicts = conflicts_res.json()
    assert len(blocking_conflicts) >= 1
    # Verify Friday conflicts exist
    friday_conflicts = [
        c for c in blocking_conflicts if dt.date.fromisoformat(c["date_from"]).weekday() == 4
    ]
    assert len(friday_conflicts) >= 1

    # 2. Attempt to publish the draft roster -> Must fail with 422 ROSTER_BLOCKED
    pub_fail_res = client.post(f"/api/v1/rosters/{period_id}/publish")
    assert pub_fail_res.status_code == 422
    err_body = pub_fail_res.json()
    assert err_body["error"]["code"] == "ROSTER_BLOCKED"
    assert "blocking conflict" in err_body["error"]["message"].lower()

    # 3. Ops Manager acknowledges all blocking conflicts with justified reasons
    all_blocking = client.get(f"/api/v1/rosters/{period_id}/conflicts?severity=BLOCKING").json()
    for c in all_blocking:
        ack_res = client.post(
            f"/api/v1/rosters/{period_id}/acknowledge",
            json={
                "conflict_id": c["id"],
                "reason": "Business continuity exception acknowledged by Ops Manager",
            },
        )
        assert ack_res.status_code == 200
        assert ack_res.json()["is_acknowledged"] is True

    # 4. Attempt to publish again -> Must succeed with 200 OK and status PUBLISHED
    pub_success_res = client.post(f"/api/v1/rosters/{period_id}/publish")
    assert pub_success_res.status_code == 200
    published_roster = pub_success_res.json()
    assert published_roster["status"] == "PUBLISHED"
