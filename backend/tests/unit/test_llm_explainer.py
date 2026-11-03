"""Unit tests for LLM conflict explanation service (T-520)."""

import datetime as dt
import uuid

from app.models.roster import ConflictSeverity
from app.schemas.roster import RosterConflictRead
from app.services.llm_explainer import generate_llm_conflict_explanation


def test_generate_llm_explanation_e001_coverage() -> None:
    conflict = RosterConflictRead(
        id=uuid.uuid4(),
        roster_period_id=uuid.uuid4(),
        code="E001",
        severity=ConflictSeverity.BLOCKING,
        date_from=dt.date(2026, 12, 14),
        date_to=dt.date(2026, 12, 14),
        root_causes=["LEAVE", "SOLO_RESOURCE"],
        message="Aurora Customer Support requires 1 staff, 0 scheduled due to approved leave.",
        brand_name="Aurora",
        process_name="Customer Support",
        employee_name="Riya Shah",
        employee_code="EMP-007",
    )

    res = generate_llm_conflict_explanation(conflict)

    assert res.conflict_id == conflict.id
    assert res.deterministic_message == conflict.message
    assert "Zero coverage risk" in res.executive_summary
    assert "Aurora" in res.executive_summary
    assert "SLA violation" in res.operational_impact
    assert "floater" in res.recommended_action.lower()
    assert res.confidence_score >= 0.95


def test_generate_llm_explanation_e005_streak() -> None:
    conflict = RosterConflictRead(
        id=uuid.uuid4(),
        roster_period_id=uuid.uuid4(),
        code="E005",
        severity=ConflictSeverity.BLOCKING,
        date_from=dt.date(2026, 12, 7),
        date_to=dt.date(2026, 12, 13),
        root_causes=["STREAK_LIMIT"],
        message="Rahul Verma assigned to 7 consecutive work days, exceeding limit of 6.",
        employee_name="Rahul Verma",
        employee_code="EMP-021",
    )

    res = generate_llm_conflict_explanation(conflict)

    assert res.conflict_id == conflict.id
    assert "Fatigue" in res.executive_summary
    assert "Rahul Verma" in res.executive_summary
    assert "Weekly Off" in res.recommended_action
