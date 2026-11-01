# Changelog

All notable changes to this project are recorded here. Format follows [Keep a Changelog](https://keepachangelog.com/); versions follow [Semantic Versioning](https://semver.org/) once code exists.

## [Unreleased]

### Added
- Master data repositories and domain services with audit hooks (Task T-306 marked Completed in `TASK_TRACKER.md`):
  - Created repository layer in `backend/app/repositories/`:
    - `BaseRepository[ModelType: Base]`: generic CRUD, active filtering, and paginated query helpers.
    - Specific repositories in `core.py`: `PodRepository`, `EmployeeRepository`, `ProcessRepository`, `BrandRepository`, `BrandProcessRepository`, `AssignmentRepository`, and `AuditLogRepository`.
  - Created domain use-case service layer in `backend/app/services/master_data.py`:
    - `PodService`: uniqueness checks on name, lead validation, soft-delete protection against pods with active members/brands, and audit mutation logging.
    - `EmployeeService`: unique code/email validation, pod foreign key verification, deletion guard against employees with assignments/leaves, and audit logging.
    - `ProcessService`: unique code/name validation, deletion guard against brand-configured processes, and audit logging.
    - `BrandService`: unique code/name validation, pod scoping, deletion guard against configured processes, and audit logging.
    - `BrandProcessService`: unique (brand_id, process_id) pairing, deletion guard against active staff assignments/coverage rules, and audit logging.
    - `AssignmentService`: exact date overlap constraint checks, employee/brand-process relationship validation, and audit logging.
  - Added unit test suite in `backend/tests/unit/test_master_data_services.py` testing complete service lifecycle, duplicate validation, deletion constraints, and audit log tracking.
- Schemas and uniform error handling middleware (Task T-305 marked Completed in `TASK_TRACKER.md`):
  - Created Pydantic v2 schemas across:
    - `backend/app/schemas/common.py`: generic `PaginatedResponse[T]`, `PaginationParams`, `MessageResponse`, `EntityCreatedResponse`.
    - `backend/app/schemas/core.py`: create, update, and read models for pods, employees, processes, brands, brand-processes, and assignments.
    - `backend/app/schemas/rules.py`: models and validators for coverage rules (`weekday` vs `specific_date` mutual exclusivity), holidays, leaves (`end_date >= start_date`), comp-off ledger & balance, weekly-off rules, and employee preferences.
    - `backend/app/schemas/auth.py`: login/refresh request, user read/update, token response, and audit log models.
    - `backend/app/schemas/roster.py`: roster generation, cell batch updates, lock/unlock requests, conflicts, acknowledgements, grid matrix rows/cells, and what-if impact simulation payloads.
  - Enhanced uniform error envelope in `backend/app/core/errors.py` with typed exceptions (`BadRequestError`, `AuthenticationError`, `ForbiddenError`, `NotFoundError`, `ConflictError`, `BusinessValidationError`, `RosterBlockedError`, `RateLimitedError`) and fallback `generic_exception_handler` (500 `INTERNAL_ERROR`), ensuring `X-Request-ID` is uniformly delivered in headers and JSON payloads per `API_DOCUMENTATION.md` §3.
  - Added unit test suite in `backend/tests/unit/test_schemas_and_errors.py` verifying schema validators, serialization, and HTTP error envelope compliance for all status codes.
- Initial Alembic database migration (Task T-304 marked Completed in `TASK_TRACKER.md`):
  - Created initial schema revision `backend/alembic/versions/754504684d23_0001_initial_schema.py` covering all 16 application tables:
    - Core: `pods`, `processes`, `brands`, `employees`, `brand_processes`, `assignments`.
    - Rules & availability: `coverage_rules`, `holidays`, `leaves`, `comp_off_ledger`, `weekly_off_rules`, `employee_preferences`.
    - Roster & audit: `roster_periods`, `roster_entries`, `roster_conflicts`, `users`, `audit_logs`.
  - Added partial unique index `uq_roster_periods_month_published` on `roster_periods(month)` where `status = 'PUBLISHED'` enforcing that at most one published roster version exists per month.
  - Added partial index `ix_leaves_emp_dates_approved` on `leaves(employee_id, start_date, end_date)` where `status = 'APPROVED'`.
  - Configured `backend/alembic/env.py` to support dynamic `-x url=...` command line arguments for test environments and dialect fallbacks.
  - Added full migration lifecycle integration tests in `backend/tests/unit/test_alembic_config.py` verifying clean `upgrade(head)` -> `downgrade(base)` -> `upgrade(head)` runs and table discovery.
- Roster, conflict, user, and audit ORM models (Task T-303 marked Completed in `TASK_TRACKER.md`):
  - Created `backend/app/models/auth.py` defining:
    - `User`: application user accounts with `UserRole` enum (`OPS_MANAGER`, `POD_LEAD`, `EMPLOYEE`), unique email index, optional `employee_id` link, and active state.
    - `AuditLog`: immutable audit history recording `user_id`, `action`, `entity_type`, `entity_id`, and `before`/`after` JSON payloads.
  - Created `backend/app/models/roster.py` defining:
    - `RosterPeriod`: monthly roster version container with `(month, version)` unique constraint, lifecycle status (`GENERATING`, `DRAFT`, `PUBLISHED`, `ARCHIVED`), `solver_status`, `generation_params` JSON, and self-referential parent/child version tree.
    - `RosterEntry`: employee daily assignment cells with `(roster_period_id, employee_id, date)` unique constraint, operational status (`WORK`, `WEEKLY_OFF`, `HOLIDAY_OFF`, `HOLIDAY_WORK`, `LEAVE`, `COMP_OFF`), `source` (`AUTO`, `MANUAL`, `LOCKED_FIXED`), and lock flag.
    - `RosterConflict`: validation conflicts and warnings with `severity` (`BLOCKING`, `WARNING`, `INFO`), code, `root_causes` JSON list, `suggestions` JSON list, foreign keys to brand_process and employee, and acknowledgement workflow fields.
  - Re-exported all auth, audit, and roster models and enums in `backend/app/models/__init__.py`.
  - Added unit test suite in `backend/tests/unit/test_roster_models.py` verifying table registration, unique constraints, self-referential version hierarchies, cascade deletes, and acknowledgement workflows.
- Rules, availability, leaves, and holidays ORM models (Task T-302 marked Completed in `TASK_TRACKER.md`):
  - Created `backend/app/models/rules.py` defining:
    - `CoverageRule`: with mutual exclusivity CheckConstraint for `weekday` (0..6) vs `specific_date` and non-negative `min_staff`.
    - `Holiday`: global vs brand-scoped holidays with `(date, brand_id)` unique constraint.
    - `Leave`: approved and requested employee leaves with `end_date >= start_date` constraint and compound index.
    - `CompOffLedger`: credit tracking with `EARNED` and `REDEEMED` transactions.
    - `WeeklyOffRule`: employee policies with JSON array of weekdays.
    - `EmployeePreference`: soft scheduling preferences with weights and JSON values.
  - Linked back-populating relationships in `backend/app/models/core.py` and registered models on `backend/app/models/__init__.py`.
  - Added unit test suite in `backend/tests/unit/test_rules_models.py` verifying table discovery, check constraints, unique constraints, and relationship navigation.
- Core SQLAlchemy 2.0 ORM models and relationships (Task T-301 marked Completed in `TASK_TRACKER.md`):
  - Created `backend/app/models/mixins.py` providing `UUIDPrimaryKeyMixin` and `TimestampMixin` (`created_at`, `updated_at`).
  - Created `backend/app/models/core.py` defining core tables per `DATABASE_DESIGN.md` §3:
    - `Pod`: with deferred `lead_employee_id` and relationship to member employees and brands.
    - `Employee`: with `code`, `pod_id`, floater flag, weekly-off counts, consecutive days and overload limits.
    - `Process`: with unique capability names and codes.
    - `Brand`: with unique names, codes, and pod association.
    - `BrandProcess`: with `(brand_id, process_id)` unique constraint and calendar types (`ALL_365`, `ALL_EXCEPT_HOLIDAYS`, `EXCLUDE_SUNDAY_AND_HOLIDAYS`).
    - `Assignment`: with dated staffing assignments (`PRIMARY`, `BACKUP`) and uniqueness on `(employee_id, brand_process_id, valid_from)`.
  - Registered all models on `backend/alembic/env.py` and `backend/app/models/__init__.py`.
  - Added unit test suite in `backend/tests/unit/test_core_models.py` verifying SQLite in-memory DDL, bidirectional relationship cascades, and unique constraints.
- CP-SAT monthly roster generator module using Google OR-Tools (Task T-508 marked Completed in `TASK_TRACKER.md`):
  - Created `backend/app/scheduler/generator_cpsat.py` implementing full constraint optimization per `SCHEDULING_ENGINE.md` §§5–6:
    - Mandatory hard constraints: H1 (fixed cells & approved leaves), H2 (weekly offs with Mon–Sun pro-rating), H3 (consecutive work days limit with carry-in tail), H4 (leave days not double-counted as weekly off), H5 (fixed mandatory weekly off weekdays).
    - Hard with slack coverage: coverage deficits penalized heavily ($BIG = 100,000$), ensuring the solver never raises "infeasible" and quantifies shortfalls explicitly.
    - Soft preference penalties: P1 (preferred off days, weight 5), P4 (primary over backup staffing, weight 4), P6 (multi-brand overload avoidance, weight 8).
    - Determinism: fixed random seed and single-worker configuration guarantees 100% reproducible rosters.
    - Full post-solve integration: independently validated with `validate_roster` and enriched with plain-language explanations and suggestions via `enrich_conflicts`.
  - Added unit test suite in `backend/tests/unit/scheduler/test_generator_cpsat.py` covering feasible solving, determinism, coverage with slack without crashing, approved leave fixing, fixed mandatory weekly offs, and module isolation.
- Root-cause explainer and suggestion ranking module (Task T-506 marked Completed in `TASK_TRACKER.md`):
  - Created `backend/app/scheduler/explain.py` implementing plain-language explanation generation and actionable gap suggestions per `SCHEDULING_ENGINE.md` §§8–9:
    - Template-based deterministic plain English messages matching Scenario S1 specification (e.g. `"Brand Aurora — Customer Support has no coverage on 14 Dec (Mon)..."`).
    - Ranked backup candidate evaluation hierarchy: Assigned `BACKUP` (+100) > Same Pod (+50) > Floater (+30) > Other Pod (+10), with active working bonus and concurrent process overload disqualification.
    - Weekly-off swap suggestions (`SWAP_WEEKLY_OFF`) identifying surplus/zero-demand alternative dates within the same Mon–Sun week.
    - Leave rescheduling suggestions (`SHIFT_LEAVE`) for gaps caused by approved leaves.
    - Enrichment routines `explain_conflict` and `enrich_conflicts`.
  - Added unit test suite in `backend/tests/unit/scheduler/test_explain.py` verifying Scenario S1 parity, weekly off swap suggestions, candidate ranking hierarchy, and module isolation.
- Independent roster validator core module (Task T-505 marked Completed in `TASK_TRACKER.md`):
  - Created `backend/app/scheduler/validator.py` implementing comprehensive rule validation independent of solver per `SCHEDULING_ENGINE.md` Section 7:
    - `E001` (No Coverage) & `E002` (Under-Staffed) with automatic root-cause tagging (`E003` / `WEEKLY_OFF`, `E004` / `LEAVE`, `HOLIDAY_OFF`).
    - `E006` (Missing Weekly Offs) with Mon–Sun week partitioning and month-boundary pro-rating ($\ge 4$ days in month = 1 off; $< 4$ days = 0).
    - `E005` (Max Consecutive Work Days) with previous month carry-in tail support.
    - `E007` (Invalid Cell) catching work/weekly-off assignments during approved leaves, illegal holiday statuses, and manager lock overrides.
    - `E008` (Multi-Brand Overload WARNING) checking active concurrent brand-processes against threshold.
    - `E009` (Comp-Off Balance) ensuring redeemed comp-offs do not exceed earned credits.
    - `W001` (Preference Violations & Fixed Off mandates) and `W003` (Single Point of Failure warnings).
    - Outputting both `ValidationResult` and `CoverageCell` grids.
  - Added unit test suite in `backend/tests/unit/scheduler/test_validator.py` with dedicated test cases for each conflict code, month-edge pro-rating, fault injection, clean rosters, and module isolation.
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
