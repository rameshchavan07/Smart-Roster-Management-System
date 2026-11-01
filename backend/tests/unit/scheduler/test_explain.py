"""Unit tests for pure-Python root-cause explainer and suggestion ranking."""

from datetime import date

from app.scheduler.domain import (
    Assignment,
    AssignmentType,
    BrandProcess,
    CalendarType,
    Conflict,
    ConflictCode,
    ConflictSeverity,
    DemandCell,
    Employee,
    EmployeeLeave,
    LeaveType,
    RosterCell,
    RosterStatus,
    SuggestionType,
)
from app.scheduler.explain import (
    enrich_conflicts,
    explain_conflict,
    rank_backup_candidates,
)


def test_explainer_module_isolation() -> None:
    """Verify explainer has no dependencies on fastapi, sqlalchemy, or app.db."""
    forbidden = ["fastapi", "sqlalchemy", "app.api", "app.db", "app.models"]
    import app.scheduler.explain

    for global_val in vars(app.scheduler.explain).values():
        val_mod = getattr(global_val, "__module__", "")
        for f in forbidden:
            assert not val_mod.startswith(f), f"Explainer leaks forbidden dependency: {val_mod}"


def test_scenario_s1_explainer_and_backup_suggestions() -> None:
    """Test Scenario S1: single-resource brand on leave generates exact explanation & floater suggestion."""
    bp = BrandProcess(
        id="bp-aurora",
        brand_id="b-aurora",
        brand_name="Aurora",
        process_id="p-cs",
        process_name="Customer Support",
        calendar_type=CalendarType.ALL_365,
        pod_id="pod-a",
    )
    riya = Employee(
        id="emp-riya",
        code="EMP-014",
        full_name="Riya Shah",
        pod_id="pod-a",
    )
    kabir = Employee(
        id="emp-kabir",
        code="EMP-001",
        full_name="Kabir Sharma",
        pod_id="pod-floaters",
        is_floater=True,
    )
    anaya = Employee(
        id="emp-anaya",
        code="EMP-002",
        full_name="Anaya Gupta",
        pod_id="pod-a",  # Same pod as Aurora
    )

    mon_14 = date(2026, 12, 14)

    assignments = (
        Assignment(
            employee_id="emp-riya", brand_process_id="bp-aurora", type=AssignmentType.PRIMARY
        ),
    )
    leaves = (
        EmployeeLeave(
            employee_id="emp-riya",
            start_date=date(2026, 12, 13),
            end_date=date(2026, 12, 15),
            type=LeaveType.PLANNED,
            note="Annual leave",
        ),
    )

    roster_cells = (
        RosterCell(employee_id="emp-riya", date=mon_14, status=RosterStatus.LEAVE),
        RosterCell(employee_id="emp-kabir", date=mon_14, status=RosterStatus.WORK),
        RosterCell(employee_id="emp-anaya", date=mon_14, status=RosterStatus.WORK),
    )

    demand_cells = (
        DemandCell(
            brand_process_id="bp-aurora",
            brand_id="b-aurora",
            brand_name="Aurora",
            process_id="p-cs",
            process_name="Customer Support",
            date=mon_14,
            is_operating_day=True,
            required_headcount=1,
        ),
    )

    conflict = Conflict(
        code=ConflictCode.E001,
        severity=ConflictSeverity.BLOCKING,
        brand_process_id="bp-aurora",
        date_from=mon_14,
        date_to=mon_14,
        root_causes=("LEAVE", ConflictCode.E004.value),
    )

    enriched = explain_conflict(
        conflict=conflict,
        employees=(riya, kabir, anaya),
        brand_processes=(bp,),
        assignments=assignments,
        roster_cells=roster_cells,
        demand_cells=demand_cells,
        leaves=leaves,
    )

    # 1. Message verification: plain English template from §8
    assert "Brand Aurora — Customer Support has no coverage on 14 Dec (Mon)" in enriched.message
    assert "Its only assigned employee Riya Shah is on approved planned leave" in enriched.message
    assert "Backups available that day:" in enriched.message

    # 2. Suggestions verification
    assert len(enriched.suggestions) >= 2
    suggestion_types = [s.type for s in enriched.suggestions]
    assert SuggestionType.ASSIGN_BACKUP in suggestion_types
    assert SuggestionType.SHIFT_LEAVE in suggestion_types

    # First suggestion is backup assignment
    top_suggestion = enriched.suggestions[0]
    assert top_suggestion.type == SuggestionType.ASSIGN_BACKUP
    assert top_suggestion.brand_process_id == "bp-aurora"
    assert top_suggestion.target_date == mon_14
    assert "Fixes 1 coverage gap" in top_suggestion.net_impact


def test_weekly_off_swap_suggestion() -> None:
    """Test weekly-off swap recommendation when single assigned staff has weekly off on required day."""
    bp = BrandProcess(
        id="bp-1",
        brand_id="b-1",
        brand_name="GlowCare",
        process_id="p-1",
        process_name="Support",
        calendar_type=CalendarType.ALL_365,
    )
    emp = Employee(id="emp-1", code="E1", full_name="Pooja Rao", pod_id="p1")

    mon = date(2026, 12, 7)  # Mon: required 1, but Pooja on WEEKLY_OFF
    wed = date(2026, 12, 9)  # Wed: required 0, Pooja is WORK

    assignments = (Assignment(employee_id="emp-1", brand_process_id="bp-1"),)

    roster_cells = (
        RosterCell(employee_id="emp-1", date=mon, status=RosterStatus.WEEKLY_OFF),
        RosterCell(employee_id="emp-1", date=wed, status=RosterStatus.WORK),
    )
    demand_cells = (
        DemandCell(
            brand_process_id="bp-1",
            brand_id="b-1",
            brand_name="GlowCare",
            process_id="p-1",
            process_name="Support",
            date=mon,
            is_operating_day=True,
            required_headcount=1,
        ),
        DemandCell(
            brand_process_id="bp-1",
            brand_id="b-1",
            brand_name="GlowCare",
            process_id="p-1",
            process_name="Support",
            date=wed,
            is_operating_day=True,
            required_headcount=0,
        ),
    )

    conflict = Conflict(
        code=ConflictCode.E001,
        severity=ConflictSeverity.BLOCKING,
        brand_process_id="bp-1",
        date_from=mon,
        date_to=mon,
        root_causes=("WEEKLY_OFF",),
    )

    enriched_list = enrich_conflicts(
        conflicts=[conflict],
        employees=[emp],
        brand_processes=[bp],
        assignments=assignments,
        roster_cells=roster_cells,
        demand_cells=demand_cells,
    )

    assert len(enriched_list) == 1
    suggestions = enriched_list[0].suggestions
    swap_sugg = next((s for s in suggestions if s.type == SuggestionType.SWAP_WEEKLY_OFF), None)
    assert swap_sugg is not None
    assert swap_sugg.target_date == mon
    assert swap_sugg.source_date == wed
    assert "Swap weekly off for Pooja Rao" in swap_sugg.action


def test_candidate_ranking_hierarchy() -> None:
    """Verify candidate ranking: Configured BACKUP > Same Pod > Floater > Other Pod."""
    bp = BrandProcess(
        id="bp-target",
        brand_id="b-target",
        brand_name="Target Brand",
        process_id="p-1",
        process_name="CS",
        calendar_type=CalendarType.ALL_365,
        pod_id="pod-alpha",
    )
    primary = Employee(id="e-primary", code="E0", full_name="Primary", pod_id="pod-alpha")
    configured_backup = Employee(
        id="e-backup", code="E1", full_name="Configured Backup", pod_id="pod-beta"
    )
    same_pod = Employee(id="e-samepod", code="E2", full_name="Same Pod", pod_id="pod-alpha")
    floater = Employee(
        id="e-floater", code="E3", full_name="Floater", pod_id="pod-floaters", is_floater=True
    )
    other_pod = Employee(id="e-other", code="E4", full_name="Other Pod", pod_id="pod-gamma")

    assignments = (
        Assignment(
            employee_id="e-primary", brand_process_id="bp-target", type=AssignmentType.PRIMARY
        ),
        Assignment(
            employee_id="e-backup", brand_process_id="bp-target", type=AssignmentType.BACKUP
        ),
    )

    target_date = date(2026, 12, 1)
    # All candidates working on target_date
    roster_lookup = {
        (e.id, target_date): RosterCell(
            employee_id=e.id, date=target_date, status=RosterStatus.WORK
        )
        for e in (primary, configured_backup, same_pod, floater, other_pod)
    }

    ranked = rank_backup_candidates(
        bp=bp,
        target_date=target_date,
        employees=[primary, configured_backup, same_pod, floater, other_pod],
        assignments=assignments,
        roster_lookup=roster_lookup,
        holidays=(),
    )

    ranked_ids = [emp.id for emp, _, _ in ranked]
    # Primary is excluded; ranking order is backup -> same pod -> floater -> other pod
    assert ranked_ids == ["e-backup", "e-samepod", "e-floater", "e-other"]
