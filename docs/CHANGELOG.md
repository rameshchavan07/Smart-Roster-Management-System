# Changelog

All notable changes to this project are recorded here. Format follows [Keep a Changelog](https://keepachangelog.com/); versions follow [Semantic Versioning](https://semver.org/) once code exists.

## [Unreleased]

### Added
- Monorepo repository skeleton and tooling configuration (Task T-201 marked Completed in `TASK_TRACKER.md`): initialized git repository, root `.gitignore`, root `.editorconfig`, `backend/` and `frontend/` directory structures.

### Changed
- Frozen database schema and seed specifications (Task T-104 marked Completed in `TASK_TRACKER.md`):
  - `DATABASE_DESIGN.md` locked to Frozen v1.0, including nullable `shift_id` on `roster_entries` for future shift extensibility.
  - `SAMPLE_DATA.md` locked to Frozen v1.0, establishing exact 36-employee / 25-brand arithmetic (32 non-floater employees staffing 32 slots + 4 dedicated floaters), process catalog, and full setups and assertions for golden demo scenarios S1–S5.
- Resolved open questions Q1–Q6 and deadline Q11 (Task T-103 marked Completed in `TASK_TRACKER.md`):
  - Q1: Confirmed React 18 + TypeScript SPA with FastAPI REST backend.
  - Q2: Confirmed Day-level granularity only (`WORK`, `WEEKLY_OFF`, `HOLIDAY_OFF`, `HOLIDAY_WORK`, `LEAVE`, `COMP_OFF`), extensible with `shift_id`.
  - Q3: Confirmed 1 mandatory weekly off per week, pro-rated at month boundaries ($\ge 4$ days in month = 1 off, $< 4$ days = 0).
  - Q4: Confirmed floater pool of 4 employees held as backups; suggestion engine dynamically assigns them to resolve coverage shortfalls.
  - Q5: Confirmed CP-SAT auto-generation with independent validation, suggestion ranking, and manager publish gating.
  - Q6: Confirmed multi-brand employees count toward all assigned brand-processes simultaneously with `E008 OVERLOAD` warning above 3.
  - Q11: Confirmed 4-day deadline targeting Level 1 (demo-able core, 87h) as primary build scope.
- Aligned `README.md` key decisions table from "Needs your confirmation" to "Confirmed".
- Corrected `SCHEDULING_ENGINE.md` explainer date from November 14 to December 14, 2026.
- Corrected `UI_UX_REQUIREMENTS.md` S3 grid header weekday sequence to start on Tuesday (`T W T F S S M ...`) for December 1, 2026.
- Clarified conflict code relationship in `SCHEDULING_ENGINE.md`: `E001`/`E002` are primary codes; `WEEKLY_OFF` (`E003`) and `LEAVE` (`E004`) are root-cause tags.
- Clarified `PROJECT_ROADMAP.md` table to separate completed tasks (`T-101`, `T-102`) and reconcile 141h remaining MVP hours with 167h total.
- Updated `BUILD_PROMPTS.md` decision status preamble.
- Renamed folder `doc/` to `docs/`, created root `.env.example`, and initialized `docs/adr/0001-use-cp-sat.md`.

### Added
- Test cases `TC-IMP-03` (multi-brand schedule change gap detection) and `TC-SUG-03` (floater backup assignment resolution) in `TESTING_DOCUMENTATION.md`.
- Architecture Decision Record `docs/adr/0001-use-cp-sat.md` documenting CP-SAT solver selection.

## [0.0.1] — 2026-11-01 — Documentation baseline

### Added
- Project understanding and requirement analysis from the Datastraw assessment brief.
- Documentation set: `PROJECT_OVERVIEW`, `REQUIREMENTS`, `TECH_STACK`, `SYSTEM_ARCHITECTURE`, `SCHEDULING_ENGINE`, `DATABASE_DESIGN`, `API_DOCUMENTATION`, `UI_UX_REQUIREMENTS`, `DESIGN_SYSTEM`, `USER_FLOW`, `PROJECT_ROADMAP`, `TASK_TRACKER`, `TESTING_DOCUMENTATION`, `DEPLOYMENT`, `SECURITY`, `FOLDER_STRUCTURE`, `SAMPLE_DATA`, `ASSUMPTIONS_AND_OPEN_QUESTIONS`, `README`.
- Task tracker: 91 tasks across 10 phases with scope tags and computed hour totals.

### Decided
- Python is the primary language (confirmed by project owner).
- Proposed, awaiting confirmation: FastAPI, SQLAlchemy 2.0, PostgreSQL 16, OR-Tools CP-SAT, React + TypeScript frontend.

### Known open items
- Questions Q1–Q6 in `ASSUMPTIONS_AND_OPEN_QUESTIONS.md` (frontend choice, shifts, weekly-off policy, floaters, generate-vs-assist, multi-brand handling).
- Submission deadline and daily hours (Q11) to fix the scope level.

---
### How to use this file
Add an entry under **[Unreleased]** with every merged change, grouped as *Added / Changed / Fixed / Removed / Security*. On release or milestone, rename the section with a version and date. Reference task IDs (e.g. `T-505`) in each line.
