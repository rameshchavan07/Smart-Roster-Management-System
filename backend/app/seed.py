"""Database seed script populating master data and rules per SAMPLE_DATA.md.

Implements:
- 6 Pods (A to F)
- 4 Processes (CS, ACC, RET, NDR)
- 36 Employees (6 Pod Leads, 26 Primary Staff, 4 Floaters)
- 25 Brands (20 single-resource, 5 multi-resource)
- Brand Processes with Operating Calendars
- Staffing Assignments (Primary and Backup)
- Coverage Rules & Overrides (Pulse Monday, Nova Friday, Aurora Dec 18)
- Weekly Off Rules (Fixed Mandatory, Fixed Preferred, Rotating, Any)
- Public Holidays (Global Christmas Dec 25, Regional Dec 10 for Kredo)
- Pre-seeded Approved Leaves for December 2026
- Seeded Demo Accounts (Ops Manager, Pod Lead, Employee) with Argon2 passwords
- Scale generator support (`--scale 3` generates 18 pods, 108 employees, 75 brands)
"""

from __future__ import annotations

import argparse
import logging
import sys
import uuid
from datetime import date
from typing import Any

from argon2 import PasswordHasher
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.db.base import Base
from app.models.auth import AuditLog, User, UserRole
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
from app.models.roster import RosterConflict, RosterEntry, RosterPeriod
from app.models.rules import (
    CompOffLedger,
    CoverageRule,
    EmployeePreference,
    Holiday,
    Leave,
    LeaveStatus,
    LeaveType,
    WeeklyOffMode,
    WeeklyOffRule,
)

logger = logging.getLogger("app.seed")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def clean_database(session: Session) -> None:
    """Wipe all application data in foreign-key safe order."""
    logger.info("Cleaning existing database data...")
    # Break circular FK between pods and lead employees
    session.execute(text("UPDATE pods SET lead_employee_id = NULL"))
    session.commit()

    # Delete in leaf-to-root order
    session.query(AuditLog).delete()
    session.query(RosterConflict).delete()
    session.query(RosterEntry).delete()
    session.query(RosterPeriod).delete()
    session.query(User).delete()
    session.query(CompOffLedger).delete()
    session.query(Leave).delete()
    session.query(EmployeePreference).delete()
    session.query(WeeklyOffRule).delete()
    session.query(CoverageRule).delete()
    session.query(Holiday).delete()
    session.query(Assignment).delete()
    session.query(BrandProcess).delete()
    session.query(Brand).delete()
    session.query(Employee).delete()
    session.query(Pod).delete()
    session.query(Process).delete()
    session.commit()
    logger.info("Database cleaned successfully.")


def seed_database(
    session: Session,
    scale: int = 1,
    clean: bool = True,
    demo_password: str = "DemoPass123!",
) -> dict[str, int]:
    """Seed the database according to SAMPLE_DATA.md.

    Args:
        session: Active SQLAlchemy session.
        scale: Scaling factor (1 = standard 36 employees / 25 brands, 3 = stress test 108 / 75).
        clean: Whether to wipe existing tables first.
        demo_password: Plaintext password to hash for demo user accounts.

    Returns:
        dict summarizing the counts of seeded entities.
    """
    # Ensure all tables exist before cleaning or seeding
    Base.metadata.create_all(bind=session.get_bind())

    if clean:
        clean_database(session)

    hasher = PasswordHasher()
    hashed_pwd = hasher.hash(demo_password)

    # -------------------------------------------------------------------------
    # 1. Processes (CS, ACC, RET, NDR)
    # -------------------------------------------------------------------------
    processes_data = [
        ("CS", "Customer Support", "Customer Support tier 1 & 2"),
        ("ACC", "Abandoned Cart", "Abandoned Cart recovery and follow-ups"),
        ("RET", "Retention", "Customer Retention and Loyalty campaigns"),
        ("NDR", "Non-Delivery Reports", "Non-Delivery Report issue resolution"),
    ]
    processes: dict[str, Process] = {}
    for code, name, desc in processes_data:
        p = Process(code=code, name=name, description=desc, is_active=True)
        session.add(p)
        processes[code] = p
    session.flush()

    # -------------------------------------------------------------------------
    # 2. Pods and Employees
    # -------------------------------------------------------------------------
    pods: dict[str, Pod] = {}
    employees: dict[str, Employee] = {}

    pod_configs = [
        ("A", "Pod A (Support Specialists)"),
        ("B", "Pod B (D2C Accelerators)"),
        ("C", "Pod C (Operations & Retention)"),
        ("D", "Pod D (Logistics & NDR)"),
        ("E", "Pod E (Growth & Engagement)"),
        ("F", "Pod F (Flex & Peak Operations)"),
    ]

    for p_letter, p_name in pod_configs:
        pod = Pod(name=p_name, is_active=True)
        session.add(pod)
        pods[p_letter] = pod
    session.flush()

    # Employee specs: (code, name, email, pod_letter, is_floater, weekly_off_count)
    emp_specs: list[tuple[str, str, str, str, bool, int]] = [
        # Pod Leads (EMP-001 to EMP-006)
        ("EMP-001", "Aanya Sharma", "aanya.sharma@example.test", "A", False, 1),
        ("EMP-002", "Bhavin Patel", "bhavin.patel@example.test", "B", False, 1),
        ("EMP-003", "Chetan Kumar", "chetan.kumar@example.test", "C", False, 1),
        ("EMP-004", "Divya Nair", "divya.nair@example.test", "D", False, 1),
        ("EMP-005", "Eshaan Joshi", "eshaan.joshi@example.test", "E", False, 1),
        ("EMP-006", "Farhan Ali", "farhan.ali@example.test", "F", False, 1),
        # Pod A Staff (EMP-007 to EMP-010)
        ("EMP-007", "Riya Shah", "riya.shah@example.test", "A", False, 1),
        ("EMP-008", "Karan Mehta", "karan.mehta@example.test", "A", False, 1),
        ("EMP-009", "Tanvi Rao", "tanvi.rao@example.test", "A", False, 1),
        ("EMP-010", "Arjun Das", "arjun.das@example.test", "A", False, 1),
        # Pod B Staff (EMP-011 to EMP-017)
        ("EMP-011", "Siddharth Jain", "siddharth.jain@example.test", "B", False, 1),
        ("EMP-012", "Ananya Iyer", "ananya.iyer@example.test", "B", False, 2),  # 2 weekly offs
        ("EMP-013", "Manish Rawat", "manish.rawat@example.test", "B", False, 1),
        ("EMP-014", "Deepak Joshi", "deepak.joshi@example.test", "B", False, 1),
        ("EMP-015", "Aarav Patel", "aarav.patel@example.test", "B", False, 1),
        ("EMP-016", "Pooja Sharma", "pooja.sharma@example.test", "B", False, 1),
        ("EMP-017", "Vikram Singh", "vikram.singh@example.test", "B", False, 1),
        # Pod C Staff (EMP-018 to EMP-022)
        ("EMP-018", "Gaurav Sen", "gaurav.sen@example.test", "C", False, 1),
        ("EMP-019", "Swati Mishra", "swati.mishra@example.test", "C", False, 1),
        ("EMP-020", "Harish Nambiar", "harish.nambiar@example.test", "C", False, 1),
        ("EMP-021", "Neha Gupta", "neha.gupta@example.test", "C", False, 1),
        ("EMP-022", "Rahul Verma", "rahul.verma@example.test", "C", False, 1),
        # Pod D Staff (EMP-023 to EMP-027)
        ("EMP-023", "Aditi Rao", "aditi.rao@example.test", "D", False, 1),
        ("EMP-024", "Dev Malhotra", "dev.malhotra@example.test", "D", False, 1),
        ("EMP-025", "Kavita Reddy", "kavita.reddy@example.test", "D", False, 1),
        ("EMP-026", "Suresh Babu", "suresh.babu@example.test", "D", False, 1),
        ("EMP-027", "Pallavi Ghosh", "pallavi.ghosh@example.test", "D", False, 1),
        # Pod E Staff (EMP-028 to EMP-031)
        ("EMP-028", "Zoya Khan", "zoya.khan@example.test", "E", False, 1),
        ("EMP-029", "Kunal Kapoor", "kunal.kapoor@example.test", "E", False, 1),
        ("EMP-030", "Meera Sen", "meera.sen@example.test", "E", False, 2),  # 2 weekly offs
        ("EMP-031", "Tarun Varma", "tarun.varma@example.test", "E", False, 1),
        # Pod F Staff & Floaters (EMP-032 to EMP-036)
        ("EMP-032", "Rohit Deshmukh", "rohit.deshmukh@example.test", "F", False, 1),
        ("EMP-033", "Kabir Nair", "kabir.nair@example.test", "F", True, 1),  # Floater
        ("EMP-034", "Ananya Verma", "ananya.verma@example.test", "F", True, 1),  # Floater
        ("EMP-035", "Rohan Mehra", "rohan.mehra@example.test", "F", True, 1),  # Floater
        ("EMP-036", "Priya Pillai", "priya.pillai@example.test", "F", True, 1),  # Floater
    ]

    for code, name, email, pod_letter, is_floater, wo_count in emp_specs:
        emp = Employee(
            code=code,
            full_name=name,
            email=email,
            pod_id=pods[pod_letter].id,
            is_floater=is_floater,
            weekly_off_count=wo_count,
            max_consecutive_days=6,
            max_concurrent_processes=3,
            joined_on=date(2026, 1, 1),
            is_active=True,
        )
        session.add(emp)
        employees[code] = emp
    session.flush()

    # Link pod leads
    pods["A"].lead_employee_id = employees["EMP-001"].id
    pods["B"].lead_employee_id = employees["EMP-002"].id
    pods["C"].lead_employee_id = employees["EMP-003"].id
    pods["D"].lead_employee_id = employees["EMP-004"].id
    pods["E"].lead_employee_id = employees["EMP-005"].id
    pods["F"].lead_employee_id = employees["EMP-006"].id
    session.flush()

    # -------------------------------------------------------------------------
    # 3. Brands (25 Brands: BRD-01 to BRD-25)
    # -------------------------------------------------------------------------
    brands_data = [
        # Single-resource brands (BRD-01 to BRD-20)
        ("BRD-01", "Aurora", "A"),
        ("BRD-02", "Solace", "A"),
        ("BRD-03", "Lumina", "A"),
        ("BRD-04", "Zenith Essentials", "A"),
        ("BRD-05", "Kredo", "B"),
        ("BRD-06", "Vortex", "B"),
        ("BRD-07", "Nectar", "B"),
        ("BRD-08", "Aura", "B"),
        ("BRD-09", "Crest", "C"),
        ("BRD-10", "Haven", "C"),
        ("BRD-11", "Echo", "C"),
        ("BRD-12", "Summit", "D"),
        ("BRD-13", "Tide", "D"),
        ("BRD-14", "Verve", "D"),
        ("BRD-15", "Bliss", "E"),
        ("BRD-16", "Strive", "E"),
        ("BRD-17", "Oasis", "A"),
        ("BRD-18", "Prism", "B"),
        ("BRD-19", "Mirage", "C"),
        ("BRD-20", "Beacon", "D"),
        # Multi-resource brands (BRD-21 to BRD-25)
        ("BRD-21", "Nova", "B"),
        ("BRD-22", "Zenith Brand", "E"),
        ("BRD-23", "Pulse", "C"),
        ("BRD-24", "Orion", "D"),
        ("BRD-25", "Apex", "F"),
    ]

    brands: dict[str, Brand] = {}
    for code, name, pod_letter in brands_data:
        brand = Brand(
            code=code,
            name=name,
            pod_id=pods[pod_letter].id,
            is_active=True,
        )
        session.add(brand)
        brands[code] = brand
    session.flush()

    # -------------------------------------------------------------------------
    # 4. Brand Processes & Assignments
    # -------------------------------------------------------------------------
    # Map of (brand_code, process_code) -> BrandProcess
    bp_map: dict[tuple[str, str], BrandProcess] = {}

    def add_bp(
        b_code: str,
        p_code: str,
        cal_type: CalendarType,
        min_cov: int = 1,
    ) -> BrandProcess:
        bp = BrandProcess(
            id=uuid.uuid4(),
            brand_id=brands[b_code].id,
            process_id=processes[p_code].id,
            calendar_type=cal_type,
            min_coverage_default=min_cov,
            valid_from=date(2026, 1, 1),
            is_active=True,
        )
        session.add(bp)
        session.flush()
        bp_map[(b_code, p_code)] = bp
        return bp

    def add_assignment(
        emp_code: str,
        bp: BrandProcess,
        asgn_type: AssignmentType = AssignmentType.PRIMARY,
    ) -> Assignment:
        asgn = Assignment(
            id=uuid.uuid4(),
            employee_id=employees[emp_code].id,
            brand_process_id=bp.id,
            type=asgn_type,
            allocation_pct=100,
            valid_from=date(2026, 1, 1),
        )
        session.add(asgn)
        return asgn

    # Single-resource brand processes and assignments (matching SAMPLE_DATA.md §2.1)
    # BRD-01: Aurora (EMP-007)
    bp_01_cs = add_bp("BRD-01", "CS", CalendarType.ALL_365)
    bp_01_acc = add_bp("BRD-01", "ACC", CalendarType.ALL_EXCEPT_HOLIDAYS)
    bp_01_ndr = add_bp("BRD-01", "NDR", CalendarType.EXCLUDE_SUNDAY_AND_HOLIDAYS)
    add_assignment("EMP-007", bp_01_cs)
    add_assignment("EMP-007", bp_01_acc)
    add_assignment("EMP-007", bp_01_ndr)

    # BRD-02: Solace (EMP-008)
    bp_02_cs = add_bp("BRD-02", "CS", CalendarType.ALL_365)
    add_assignment("EMP-008", bp_02_cs)

    # BRD-03: Lumina (EMP-009)
    bp_03_cs = add_bp("BRD-03", "CS", CalendarType.ALL_EXCEPT_HOLIDAYS)
    bp_03_acc = add_bp("BRD-03", "ACC", CalendarType.EXCLUDE_SUNDAY_AND_HOLIDAYS)
    add_assignment("EMP-009", bp_03_cs)
    add_assignment("EMP-009", bp_03_acc)

    # BRD-04: Zenith Essentials (EMP-010)
    bp_04_cs = add_bp("BRD-04", "CS", CalendarType.ALL_365)
    add_assignment("EMP-010", bp_04_cs)

    # BRD-05: Kredo (EMP-011)
    bp_05_cs = add_bp("BRD-05", "CS", CalendarType.ALL_EXCEPT_HOLIDAYS)
    bp_05_ret = add_bp("BRD-05", "RET", CalendarType.ALL_EXCEPT_HOLIDAYS)
    add_assignment("EMP-011", bp_05_cs)
    add_assignment("EMP-011", bp_05_ret)

    # BRD-06: Vortex (EMP-012)
    bp_06_cs = add_bp("BRD-06", "CS", CalendarType.ALL_365)
    add_assignment("EMP-012", bp_06_cs)

    # BRD-07: Nectar (EMP-013)
    bp_07_cs = add_bp("BRD-07", "CS", CalendarType.ALL_EXCEPT_HOLIDAYS)
    bp_07_acc = add_bp("BRD-07", "ACC", CalendarType.EXCLUDE_SUNDAY_AND_HOLIDAYS)
    add_assignment("EMP-013", bp_07_cs)
    add_assignment("EMP-013", bp_07_acc)

    # BRD-08: Aura (EMP-014)
    bp_08_cs = add_bp("BRD-08", "CS", CalendarType.ALL_365)
    add_assignment("EMP-014", bp_08_cs)

    # BRD-09: Crest (EMP-018)
    bp_09_cs = add_bp("BRD-09", "CS", CalendarType.ALL_EXCEPT_HOLIDAYS)
    add_assignment("EMP-018", bp_09_cs)

    # BRD-10: Haven (EMP-019)
    bp_10_cs = add_bp("BRD-10", "CS", CalendarType.ALL_365)
    bp_10_ret = add_bp("BRD-10", "RET", CalendarType.ALL_EXCEPT_HOLIDAYS)
    add_assignment("EMP-019", bp_10_cs)
    add_assignment("EMP-019", bp_10_ret)

    # BRD-11: Echo (EMP-020)
    bp_11_cs = add_bp("BRD-11", "CS", CalendarType.ALL_EXCEPT_HOLIDAYS)
    add_assignment("EMP-020", bp_11_cs)

    # BRD-12: Summit (EMP-025)
    bp_12_cs = add_bp("BRD-12", "CS", CalendarType.ALL_365)
    bp_12_ndr = add_bp("BRD-12", "NDR", CalendarType.EXCLUDE_SUNDAY_AND_HOLIDAYS)
    add_assignment("EMP-025", bp_12_cs)
    add_assignment("EMP-025", bp_12_ndr)

    # BRD-13: Tide (EMP-026)
    bp_13_cs = add_bp("BRD-13", "CS", CalendarType.ALL_EXCEPT_HOLIDAYS)
    add_assignment("EMP-026", bp_13_cs)

    # BRD-14: Verve (EMP-027)
    bp_14_cs = add_bp("BRD-14", "CS", CalendarType.ALL_365)
    add_assignment("EMP-027", bp_14_cs)

    # BRD-15: Bliss (EMP-031)
    bp_15_cs = add_bp("BRD-15", "CS", CalendarType.ALL_EXCEPT_HOLIDAYS)
    add_assignment("EMP-031", bp_15_cs)

    # BRD-16: Strive (EMP-005)
    bp_16_cs = add_bp("BRD-16", "CS", CalendarType.ALL_365)
    add_assignment("EMP-005", bp_16_cs)

    # BRD-17: Oasis (EMP-001)
    bp_17_cs = add_bp("BRD-17", "CS", CalendarType.ALL_EXCEPT_HOLIDAYS)
    add_assignment("EMP-001", bp_17_cs)

    # BRD-18: Prism (EMP-002)
    bp_18_cs = add_bp("BRD-18", "CS", CalendarType.ALL_365)
    add_assignment("EMP-002", bp_18_cs)

    # BRD-19: Mirage (EMP-003)
    bp_19_cs = add_bp("BRD-19", "CS", CalendarType.ALL_EXCEPT_HOLIDAYS)
    add_assignment("EMP-003", bp_19_cs)

    # BRD-20: Beacon (EMP-004)
    bp_20_cs = add_bp("BRD-20", "CS", CalendarType.ALL_365)
    add_assignment("EMP-004", bp_20_cs)

    # Multi-resource brands (matching SAMPLE_DATA.md §2.2)
    # BRD-21: Nova (EMP-015, EMP-016, EMP-017)
    bp_21_cs = add_bp("BRD-21", "CS", CalendarType.ALL_365)
    bp_21_acc = add_bp("BRD-21", "ACC", CalendarType.ALL_EXCEPT_HOLIDAYS)
    bp_21_ndr = add_bp("BRD-21", "NDR", CalendarType.EXCLUDE_SUNDAY_AND_HOLIDAYS)
    add_assignment("EMP-015", bp_21_cs, AssignmentType.PRIMARY)
    add_assignment("EMP-016", bp_21_acc, AssignmentType.PRIMARY)
    add_assignment("EMP-015", bp_21_acc, AssignmentType.BACKUP)  # Secondary on ACC
    add_assignment("EMP-017", bp_21_ndr, AssignmentType.PRIMARY)

    # BRD-22: Zenith Brand (EMP-028, EMP-029, EMP-030)
    bp_22_cs = add_bp("BRD-22", "CS", CalendarType.ALL_365)
    bp_22_acc = add_bp("BRD-22", "ACC", CalendarType.ALL_EXCEPT_HOLIDAYS)
    bp_22_ret = add_bp("BRD-22", "RET", CalendarType.ALL_EXCEPT_HOLIDAYS)
    add_assignment("EMP-028", bp_22_cs, AssignmentType.PRIMARY)
    add_assignment("EMP-029", bp_22_acc, AssignmentType.PRIMARY)
    add_assignment("EMP-030", bp_22_ret, AssignmentType.PRIMARY)

    # BRD-23: Pulse (EMP-021, EMP-022)
    bp_23_cs = add_bp("BRD-23", "CS", CalendarType.ALL_365)
    add_assignment("EMP-021", bp_23_cs, AssignmentType.PRIMARY)
    add_assignment("EMP-022", bp_23_cs, AssignmentType.PRIMARY)

    # BRD-24: Orion (EMP-023, EMP-024)
    bp_24_cs = add_bp("BRD-24", "CS", CalendarType.ALL_EXCEPT_HOLIDAYS)
    bp_24_ret = add_bp("BRD-24", "RET", CalendarType.ALL_EXCEPT_HOLIDAYS)
    add_assignment("EMP-023", bp_24_cs, AssignmentType.PRIMARY)
    add_assignment("EMP-024", bp_24_cs, AssignmentType.PRIMARY)
    add_assignment("EMP-023", bp_24_ret, AssignmentType.PRIMARY)
    add_assignment("EMP-024", bp_24_ret, AssignmentType.PRIMARY)

    # BRD-25: Apex (EMP-006, EMP-032)
    bp_25_cs = add_bp("BRD-25", "CS", CalendarType.ALL_365)
    bp_25_ndr = add_bp("BRD-25", "NDR", CalendarType.ALL_EXCEPT_HOLIDAYS)
    add_assignment("EMP-006", bp_25_cs, AssignmentType.PRIMARY)
    add_assignment("EMP-032", bp_25_ndr, AssignmentType.PRIMARY)

    session.flush()

    # -------------------------------------------------------------------------
    # 5. Coverage Rules & Overrides (SAMPLE_DATA.md §3)
    # -------------------------------------------------------------------------
    # Weekday override 1: Pulse (BRD-23) CS min 2 staff on Mondays (weekday 0)
    cr_pulse = CoverageRule(
        brand_process_id=bp_23_cs.id,
        weekday=0,
        specific_date=None,
        min_staff=2,
        reason="Pulse Monday surge",
        is_active=True,
    )
    session.add(cr_pulse)

    # Weekday override 2: Nova (BRD-21) ACC min 2 staff on Fridays (weekday 4)
    cr_nova = CoverageRule(
        brand_process_id=bp_21_acc.id,
        weekday=4,
        specific_date=None,
        min_staff=2,
        reason="Nova Friday surge",
        is_active=True,
    )
    session.add(cr_nova)

    # Specific date override: Aurora (BRD-01) CS min 2 staff on Dec 18, 2026
    cr_aurora = CoverageRule(
        brand_process_id=bp_01_cs.id,
        weekday=None,
        specific_date=date(2026, 12, 18),
        min_staff=2,
        reason="Year-end campaign surge",
        is_active=True,
    )
    session.add(cr_aurora)
    session.flush()

    # -------------------------------------------------------------------------
    # 6. Weekly-off Policy Rules (SAMPLE_DATA.md §4)
    # -------------------------------------------------------------------------
    # FIXED_MANDATORY: EMP-023 (Friday=4), EMP-024 (Friday=4)
    session.add(
        WeeklyOffRule(
            employee_id=employees["EMP-023"].id,
            mode=WeeklyOffMode.FIXED_MANDATORY,
            weekdays=[4],
            valid_from=date(2026, 1, 1),
        )
    )
    session.add(
        WeeklyOffRule(
            employee_id=employees["EMP-024"].id,
            mode=WeeklyOffMode.FIXED_MANDATORY,
            weekdays=[4],
            valid_from=date(2026, 1, 1),
        )
    )

    # FIXED_PREFERRED: EMP-007 (Sunday=6), EMP-015 (Wednesday=2), EMP-022 (Monday=0)
    session.add(
        WeeklyOffRule(
            employee_id=employees["EMP-007"].id,
            mode=WeeklyOffMode.FIXED_PREFERRED,
            weekdays=[6],
            valid_from=date(2026, 1, 1),
        )
    )
    session.add(
        WeeklyOffRule(
            employee_id=employees["EMP-015"].id,
            mode=WeeklyOffMode.FIXED_PREFERRED,
            weekdays=[2],
            valid_from=date(2026, 1, 1),
        )
    )
    session.add(
        WeeklyOffRule(
            employee_id=employees["EMP-022"].id,
            mode=WeeklyOffMode.FIXED_PREFERRED,
            weekdays=[0],
            valid_from=date(2026, 1, 1),
        )
    )

    # ROTATING: EMP-008, EMP-028
    session.add(
        WeeklyOffRule(
            employee_id=employees["EMP-008"].id,
            mode=WeeklyOffMode.ROTATING,
            weekdays=[],
            valid_from=date(2026, 1, 1),
        )
    )
    session.add(
        WeeklyOffRule(
            employee_id=employees["EMP-028"].id,
            mode=WeeklyOffMode.ROTATING,
            weekdays=[],
            valid_from=date(2026, 1, 1),
        )
    )

    # ANY: Remaining 29 employees
    explicit_wo_employees = {
        "EMP-023",
        "EMP-024",
        "EMP-007",
        "EMP-015",
        "EMP-022",
        "EMP-008",
        "EMP-028",
    }
    for e_code, emp in employees.items():
        if e_code not in explicit_wo_employees:
            session.add(
                WeeklyOffRule(
                    employee_id=emp.id,
                    mode=WeeklyOffMode.ANY,
                    weekdays=[],
                    valid_from=date(2026, 1, 1),
                )
            )
    session.flush()

    # -------------------------------------------------------------------------
    # 7. Holidays (SAMPLE_DATA.md §5)
    # -------------------------------------------------------------------------
    # Global Christmas holiday
    h_xmas = Holiday(
        name="Christmas",
        date=date(2026, 12, 25),
        brand_id=None,
        is_active=True,
    )
    session.add(h_xmas)

    # Brand-specific holiday for BRD-05 (Kredo) on Dec 10, 2026
    h_kredo = Holiday(
        name="Regional Event",
        date=date(2026, 12, 10),
        brand_id=brands["BRD-05"].id,
        is_active=True,
    )
    session.add(h_kredo)
    session.flush()

    # -------------------------------------------------------------------------
    # 8. Pre-seeded Approved Leaves for December 2026 (SAMPLE_DATA.md §5)
    # -------------------------------------------------------------------------
    leaves_data = [
        # EMP-016 (Pooja Sharma): 2026-12-08 to 2026-12-10
        ("EMP-016", date(2026, 12, 8), date(2026, 12, 10), "Pre-planned vacation"),
        # EMP-018: 2026-12-03 to 2026-12-04
        ("EMP-018", date(2026, 12, 3), date(2026, 12, 4), "Personal leave"),
        # EMP-026: 2026-12-16 to 2026-12-17
        ("EMP-026", date(2026, 12, 16), date(2026, 12, 17), "Family event"),
        # EMP-029: 2026-12-21 to 2026-12-23
        ("EMP-029", date(2026, 12, 21), date(2026, 12, 23), "Winter break"),
    ]
    for emp_code, s_date, e_date, note in leaves_data:
        l_obj = Leave(
            employee_id=employees[emp_code].id,
            start_date=s_date,
            end_date=e_date,
            type=LeaveType.PLANNED,
            status=LeaveStatus.APPROVED,
            note=note,
        )
        session.add(l_obj)
    session.flush()

    # -------------------------------------------------------------------------
    # 9. Seeded Demo Accounts (SAMPLE_DATA.md §8)
    # -------------------------------------------------------------------------
    demo_accounts = [
        ("ops@example.test", UserRole.OPS_MANAGER, None),
        ("lead.a@example.test", UserRole.POD_LEAD, employees["EMP-001"].id),
        ("emp@example.test", UserRole.EMPLOYEE, employees["EMP-007"].id),
    ]
    for email, role, emp_id in demo_accounts:
        user = User(
            email=email,
            password_hash=hashed_pwd,
            role=role,
            employee_id=emp_id,
            is_active=True,
        )
        session.add(user)
    session.flush()

    # -------------------------------------------------------------------------
    # 10. Scale Up (if scale > 1)
    # -------------------------------------------------------------------------
    if scale > 1:
        logger.info("Scaling dataset by factor %d...", scale)
        for s in range(2, scale + 1):
            pod_letter = chr(65 + 6 * (s - 1))  # G, M, etc.
            scaled_pods: list[Pod] = []
            for i in range(6):
                name = f"Pod {chr(ord(pod_letter) + i)} (Scale {s})"
                p = Pod(name=name, is_active=True)
                session.add(p)
                scaled_pods.append(p)
            session.flush()

            # Create 36 scaled employees
            scaled_emps: list[Employee] = []
            for i in range(1, 37):
                code = f"EMP-S{s}-{i:03d}"
                name = f"Staff S{s}-{i:03d}"
                email = f"staff.s{s}.{i:03d}@example.test"
                is_flt = i >= 33
                pod_idx = min(i // 6, 5)
                emp = Employee(
                    code=code,
                    full_name=name,
                    email=email,
                    pod_id=scaled_pods[pod_idx].id,
                    is_floater=is_flt,
                    weekly_off_count=1,
                    is_active=True,
                )
                session.add(emp)
                scaled_emps.append(emp)
            session.flush()

            # Set pod leads
            for idx, p in enumerate(scaled_pods):
                p.lead_employee_id = scaled_emps[idx].id

            # Create 25 scaled brands
            for i in range(1, 26):
                b_code = f"BRD-S{s}-{i:02d}"
                b_name = f"Brand S{s}-{i:02d}"
                b_pod = scaled_pods[min(i // 5, 5)]
                brand = Brand(code=b_code, name=b_name, pod_id=b_pod.id, is_active=True)
                session.add(brand)
                session.flush()

                bp = BrandProcess(
                    id=uuid.uuid4(),
                    brand_id=brand.id,
                    process_id=processes["CS"].id,
                    calendar_type=CalendarType.ALL_365,
                    min_coverage_default=1,
                    is_active=True,
                )
                session.add(bp)
                session.flush()

                # Assign employee
                asgn = Assignment(
                    id=uuid.uuid4(),
                    employee_id=scaled_emps[min(i, 31)].id,
                    brand_process_id=bp.id,
                    type=AssignmentType.PRIMARY,
                    allocation_pct=100,
                )
                session.add(asgn)
                session.add(
                    WeeklyOffRule(
                        employee_id=scaled_emps[min(i, 31)].id,
                        mode=WeeklyOffMode.ANY,
                        weekdays=[],
                    )
                )

    session.commit()

    # Query counts for summary
    counts: dict[str, int] = {
        "pods": session.query(Pod).count(),
        "employees": session.query(Employee).count(),
        "processes": session.query(Process).count(),
        "brands": session.query(Brand).count(),
        "brand_processes": session.query(BrandProcess).count(),
        "assignments": session.query(Assignment).count(),
        "coverage_rules": session.query(CoverageRule).count(),
        "weekly_off_rules": session.query(WeeklyOffRule).count(),
        "holidays": session.query(Holiday).count(),
        "leaves": session.query(Leave).count(),
        "users": session.query(User).count(),
    }
    logger.info("Database seeded successfully: %s", counts)
    return counts


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments for the seed script."""
    parser = argparse.ArgumentParser(description="Seed RosterOps database per SAMPLE_DATA.md")
    parser.add_argument(
        "--scale",
        type=int,
        default=1,
        help="Scale factor (1=36 emps / 25 brands, 3=108 emps / 75 brands)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        default=True,
        help="Clean existing database tables before seeding (default: True)",
    )
    parser.add_argument(
        "--no-clean",
        action="store_false",
        dest="clean",
        help="Do not clean existing database tables before seeding",
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="Database connection URL (defaults to DATABASE_URL in settings)",
    )
    parser.add_argument(
        "--demo-password",
        type=str,
        default=None,
        help="Password for seeded demo accounts (defaults to DEMO_PASSWORD setting or 'DemoPass123!')",
    )
    return parser.parse_args(args)


def main() -> None:
    """CLI entrypoint for python -m app.seed."""
    args = parse_args()
    settings = get_settings()

    db_url = args.db_url or settings.DATABASE_URL
    demo_password = args.demo_password or settings.DEMO_PASSWORD or "DemoPass123!"

    logger.info("Connecting to database at %s...", db_url)
    engine_kwargs: dict[str, Any] = {"echo": False}
    if db_url.startswith("sqlite"):
        engine_kwargs["poolclass"] = NullPool

    engine = create_engine(db_url, **engine_kwargs)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    with session_factory() as session:
        try:
            summary = seed_database(
                session=session,
                scale=args.scale,
                clean=args.clean,
                demo_password=demo_password,
            )
            print("\nSeeding Summary:")
            for entity, count in summary.items():
                print(f"  - {entity}: {count}")
            print("\nDemo Accounts Seeded:")
            print("  - OPS_MANAGER: ops@example.test")
            print("  - POD_LEAD:    lead.a@example.test (Pod A)")
            print("  - EMPLOYEE:    emp@example.test (EMP-007 Riya Shah)")
            print(f"  - Password:    {demo_password}\n")
        except Exception as e:
            logger.error("Seeding failed: %s", e)
            session.rollback()
            sys.exit(1)


if __name__ == "__main__":
    main()
