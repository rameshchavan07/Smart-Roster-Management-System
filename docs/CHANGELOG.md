# Changelog

All notable changes to this project are recorded here. Format follows [Keep a Changelog](https://keepachangelog.com/); versions follow [Semantic Versioning](https://semver.org/) once code exists.

## [Unreleased]

### Added
- Employee availability supply builder module (Task T-504 marked Completed in `TASK_TRACKER.md`):
  - Created `backend/app/scheduler/supply.py` implementing availability classification per `SCHEDULING_ENGINE.md` Section 4:
    - Precedence evaluation: Manager-locked cell override (`SupplyAvailability.LOCKED`) -> Approved leaves & comp-off redemptions (`LEAVE` / `COMP_OFF`) -> Personal holiday calculation (`HOLIDAY_OFF` when none of assigned brand-processes operate) -> Default scheduling availability (`AVAILABLE`).
    - Deterministic matrix generator `build_supply_matrix` sorting by date then employee id.
    - Constant-time lookup index helper `build_supply_lookup`.
  - Added `EmployeeLeave` dataclass and updated `GenerationInput` in `backend/app/scheduler/domain.py`.
  - Added unit test suite in `backend/tests/unit/scheduler/test_supply.py` covering default availability, manager locks, sick/planned/comp-off leaves, multi-brand personal holiday scenarios, floater holiday handling, and matrix ordering.
- Demand matrix builder module (Task T-503 marked Completed in `TASK_TRACKER.md`):
  - Created `backend/app/scheduler/demand.py` enforcing rule precedence per `SCHEDULING_ENGINE.md` Section 3:
    - Precedence hierarchy: 0 demand on non-operating days -> Specific date override (`CoverageRule.specific_date`) -> Weekday override (`CoverageRule.weekday`) -> Default minimum (`BrandProcess.min_coverage_default`).
    - Deterministic matrix generator `build_demand_matrix` sorting by date then `brand_process_id`.
    - Index helper `build_demand_lookup` for $O(1)$ cell lookups.
  - Added unit test suite in `backend/tests/unit/scheduler/test_demand.py` verifying each precedence tier, holiday/Sunday zeroing, matrix ordering, and module isolation.
- Operating calendar resolver module (Task T-502 marked Completed in `TASK_TRACKER.md`):
  - Created `backend/app/scheduler/calendar.py` implementing pure-Python calendar evaluation per `SCHEDULING_ENGINE.md` Section 2:
    - Supported calendar types: `ALL_365`, `ALL_EXCEPT_HOLIDAYS`, and `EXCLUDE_SUNDAY_AND_HOLIDAYS`.
    - Handled global public holidays and brand-scoped holidays.
    - Implemented range resolving functions (`is_operating_day`, `resolve_operating_days`, `get_operating_dates`, and `resolve_calendar_matrix`).
  - Added unit test suite in `backend/tests/unit/scheduler/test_calendar.py` covering all calendar types, holiday scoping, Sunday exclusion, date range validation, and module isolation.
- Pure-Python scheduling engine domain types and enums (Task T-501 marked Completed in `TASK_TRACKER.md`):
  - Defined all pure dataclasses and enums in `backend/app/scheduler/domain.py` with zero framework dependencies: `CalendarType`, `AssignmentType`, `RosterStatus`, `SupplyAvailability`, `WeeklyOffMode`, `LeaveType`, `ConflictSeverity`, `ConflictCode` (E001–E009, W001–W004), `SolverStatus`, `SuggestionType`, `DemandCell`, `SupplyCell`, `RosterCell`, `CoverageCell`, `CoverageRule`, `BrandProcess`, `Assignment`, `Employee`, `Holiday`, `Suggestion`, `Conflict`, `ValidationResult`, `GenerationInput`, and `GenerationOutput`.
  - Added unit test suite in `backend/tests/unit/scheduler/test_domain.py` verifying framework isolation, validation rules, and immutability.
  - Verified clean `ruff`, `mypy --strict`, and passing pytest suite.
- Design tokens, base component library, and interactive showcase page (Task T-206 marked Completed in `TASK_TRACKER.md`):
  - Created reusable UI primitives in `frontend/src/components/ui/`: `Button` (4 variants, loading, disabled), `Input` (32px, error states), `Badge` (all severity types + icon support), `Skeleton`, `EmptyState`, accessible `Modal` (with backdrop & ESC listener), accessible 420px `Drawer`, and `StatusCell` (WCAG AA compliant cell rendering for W, WO, PH, HW, L, CO with manual dot marker and lock glyph).
  - Built interactive `/design-system` showcase page in `frontend/src/features/design-system/DesignSystemPage.tsx` demonstrating all color tokens, typography scales, buttons, inputs, severity badges, and interactive modals/drawers.
  - Verified zero errors on `npm run typecheck` and `npm run build`.
- React 18 + TypeScript + Vite frontend scaffold (Task T-205 marked Completed in `TASK_TRACKER.md`): configured Tailwind CSS design system tokens from `DESIGN_SYSTEM.md`, React Router, TanStack Query, application layout shell with sidebar/topbar navigation, and verified clean TypeScript typecheck and production build.
- Alembic migrations environment and SQLAlchemy 2.0 Base metadata configuration (Task T-204 marked Completed in `TASK_TRACKER.md`): configured `alembic.ini`, dynamic database URL resolution and type comparison in `alembic/env.py`, and verified test suite ensuring `alembic upgrade head` runs cleanly.
- PostgreSQL 16 container definition and connection pooling configuration (Task T-203 marked Completed in `TASK_TRACKER.md`): `docker-compose.yml` with health checks, updated `.env.example`, SQLAlchemy 2.0 `QueuePool` configuration in `backend/app/db/session.py`, and verified unit tests.
- FastAPI backend scaffold and tooling setup (Task T-202 marked Completed in `TASK_TRACKER.md`): `pyproject.toml` with Python 3.12, pydantic-settings, structured logging, uniform error envelope, `/health` and `/ready` endpoints, and verified test suite passing with ruff and mypy.
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
