# Assumptions and Open Questions

The brief says: *"Make reasonable assumptions, document them clearly, and ensure the application allows the relevant information to be configured."* Each assumption below is a **proposed default, not a confirmed decision**, and is configurable where noted. Items marked ⚠ are ones I'd like you to confirm **before architecture is frozen**.

## A. Assumptions (proposed defaults)

| ID | Area | Assumption | Configurable? |
|---|---|---|---|
| A-01 ⚠ | Granularity | Roster is **day-level** (working / off). No time-of-day shifts in v1 | Schema extensible (add `shift_id`) |
| A-02 ⚠ | Weekly off | Default **1 weekly off per Mon–Sun week**, per employee setting (1 or 2) | Yes |
| A-03 | Weekly-off rule | Rule can be Fixed-mandatory, Fixed-preferred, Rotating, or Any | Yes |
| A-04 | Max consecutive days | Default 6 working days in a row | Yes, per employee |
| A-05 | Month edges | Weeks cut by month boundaries are pro-rated; previous month's tail used for consecutive-day count if a prior roster exists | Yes |
| A-06 ⚠ | Floaters | A small pool of **floater/backup** employees exists; they can cover other brand-processes and are the main resolution for single-resource 365-day brands | Yes (flag per employee) |
| A-07 | Multi-brand employees | A working employee counts toward **every** brand-process they are assigned to that day, with an overload **warning** above `max_concurrent_processes` (default 3) | Yes |
| A-08 | Holidays | One national holiday list (India-style sample) plus optional brand-specific holidays | Yes |
| A-09 | Working a holiday | Working a public holiday earns 1 comp-off credit; comp-offs redeemable once approved by the manager | Yes |
| A-10 | Weekly off on holidays | A holiday or leave on a weekly-off day does not "use up" that week's weekly off unless the manager configures it so | Yes |
| A-11 | Coverage unit | Coverage is measured per **brand-process-day**; minimum defaults to 1 | Yes |
| A-12 | Mandatory vs preference | Mandatory: coverage, approved leave, comp-off, weekly-off entitlement, max consecutive days, fixed-mandatory weekly offs. Preference: preferred off days, fairness, stability, avoid overload | Weights configurable |
| A-13 | Publishing | A roster can be published only with zero **unacknowledged** BLOCKING conflicts | Setting |
| A-14 | Leave workflow | Only APPROVED leave affects the roster; managers can enter leave directly as approved | Yes |
| A-15 | Time zone / locale | IST, week starts Monday | Setting |
| A-16 | Sample data | 36 employees, 25 brands, 6 pods (see `SAMPLE_DATA.md`) | Seed script |
| A-17 | Auth | Email + password; seeded demo accounts for evaluators | – |
| A-18 | Scale | Designed for ≤ 100 employees per solve; beyond that solve per pod/component | – |

## B. Open questions

### Blocking (answers change architecture/model)
**All confirmed by you 2026-11-01:**
- **Q1 = A:** React 18 + TypeScript SPA with FastAPI REST backend.
- **Q2 = A:** Day-level granularity only (`WORK`, `WEEKLY_OFF`, `HOLIDAY_OFF`, `HOLIDAY_WORK`, `LEAVE`, `COMP_OFF`). Schema remains extensible with a nullable `shift_id`.
- **Q3 = A:** 1 mandatory weekly off per Mon–Sun week (pro-rated at month edges: $\ge 4$ days in month = 1 off; $< 4$ days = 0). Hard constraint: coverage deficit is flagged rather than silently omitting weekly offs.
- **Q4 = A:** Pool of 4 dedicated floater employees exists in the sample data. In the initial generation, floaters are held as backups; when gaps occur (such as for single-resource brands on weekly offs/leave), the suggestion engine recommends floaters and applying them establishes an ad-hoc or dynamic backup assignment.
- **Q5 = A:** Auto-generate monthly draft via CP-SAT solver $\to$ validate $\to$ report conflicts $\to$ manager reviews, resolves with suggestions or manual edits, acknowledges any remaining blocking issues $\to$ publish.
- **Q6 = A:** Employee assigned to multiple brands counts toward all assigned active brand-processes on that day simultaneously, with a `WARNING` (`E008`) flagged if concurrent brand-processes exceed `max_concurrent_processes` (default 3).
- **Q11:** 4 days from receipt (~1.5–2 days focused effort per brief). Scope locked to **Level 1 (Demo-able core)** first, expanding into L2 if time permits.

| # | Question | Decision |
|---|---|---|
| Q1 | **Frontend:** React + TypeScript SPA, or a pure-Python UI (Jinja2 + HTMX)? | **Confirmed: React 18 + TypeScript SPA** |
| Q2 | **Shifts:** day-level only, or morning/evening/night shifts? | **Confirmed: Day-level only (A-01)** |
| Q3 | **Weekly offs:** how many per week, fixed or rotating, and is the entitlement absolute even if coverage suffers? | **Confirmed: 1/week, pro-rated ($\ge 4$ d = 1, $< 4$ d = 0), entitlement mandatory** |
| Q4 | **Backups:** is a floater pool realistic for the company? A 365-day single-resource brand cannot give its employee a weekly off otherwise | **Confirmed: 4 floaters in sample; suggestion engine dynamically assigns them to gaps** |
| Q5 | **Generate vs assist:** fully automatic generation with manager review, or "suggest only"? | **Confirmed: Auto-generate + validate + suggest; manager approves/publishes** |
| Q6 | **Multi-brand employees:** simultaneous coverage of all assigned brands, or split time? | **Confirmed: Simultaneous with overload warning above 3 (A-07)** |

### Non-blocking (affect polish/scope)
| # | Question | Default |
|---|---|---|
| Q7 | Do employees log in and request leave themselves? | Read-only own roster; managers enter leave (self-service = stretch) |
| Q8 | Which optional features matter most? | Suggestions, impact preview, fairness, export |
| Q9 | Approval workflow for pod leads? | Pod lead can *review/comment*; publish stays with Ops Manager |
| Q10 | Public holiday source: static seed or per-region? | Static seed |
| Q11 | Exact submission date/time (brief says 4 days from receipt)? | – needed to fix the scope cut line |
| Q12 | Hosting accounts available (Render / Vercel / Neon or Supabase)? | Free tiers |
| Q13 | Should I also draft the README "How do you think" answers and approach note when design is frozen? | Yes |
| Q14 | Product name/logo for the UI? | Working name "RosterOps" (placeholder) |
| Q15 | Data scale: stay at ~36 employees, or demo 100+? | 36, with a generated 100+ stress dataset for performance proof |

## C. Decisions log
| Date | Decision | Status |
|---|---|---|
| 2026-11-01 | Python is the primary stack | **Confirmed by you** |
| 2026-11-01 | FastAPI + SQLAlchemy 2.0 + PostgreSQL 16 + OR-Tools CP-SAT | **Confirmed by you** |
| 2026-11-01 | React 18 + TS frontend SPA (Q1 = A) | **Confirmed by you** |
| 2026-11-01 | Day-level roster granularity; extensible with shift_id (Q2 = A) | **Confirmed by you** |
| 2026-11-01 | 1 mandatory weekly off per week, pro-rated $\ge 4$ d = 1, $< 4$ d = 0 (Q3 = A) | **Confirmed by you** |
| 2026-11-01 | Floater pool (4 floaters); held as backups, suggestion engine recommends & assigns to gaps (Q4 = A) | **Confirmed by you** |
| 2026-11-01 | Auto-generate draft with CP-SAT + validator + suggestions; manager reviews and publishes (Q5 = A) | **Confirmed by you** |
| 2026-11-01 | Multi-brand employees count toward all assigned processes, overload warning above 3 (Q6 = A) | **Confirmed by you** |
| 2026-11-01 | Deadline: 4 days per brief; scope target prioritized on Level 1 (demo-able core) (Q11) | **Confirmed by you** |
