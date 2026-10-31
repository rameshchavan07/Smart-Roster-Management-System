# AGENTS.md — Standing instructions for the coding agent

Project: **Smart Roster Management System** (working name RosterOps). Python backend, React + TypeScript frontend, PostgreSQL.
Goal: an ops manager generates, validates and edits a monthly roster; the system never presents an invalid roster as valid and explains every conflict.

## 1. Read before coding (in this order)
1. `docs/ASSUMPTIONS_AND_OPEN_QUESTIONS.md` — decisions marked "proposed" are defaults; do not treat as final if the owner has changed them.
2. `docs/SCHEDULING_ENGINE.md` — the core logic; the source of truth for constraints, conflict codes and suggestions.
3. `docs/DATABASE_DESIGN.md`, `docs/API_DOCUMENTATION.md`, `docs/SYSTEM_ARCHITECTURE.md`.
4. `docs/SAMPLE_DATA.md` — seed shape and the five demo scenarios (S1–S5).
5. `docs/TASK_TRACKER.md` and `docs/PROJECT_ROADMAP.md` — pick the next task by ID; respect dependencies and the current scope level.
6. For UI work only: `docs/DESIGN_SYSTEM.md`, `docs/UI_UX_REQUIREMENTS.md`, `docs/USER_FLOW.md`.

## 2. Working rules
- Work on **one tracker task (or one slice from `BUILD_PROMPTS.md`) at a time.** Name the task ID(s) in your summary.
- If a requirement is unclear or conflicts between documents, **stop and ask**; do not guess. Record the answer in `ASSUMPTIONS_AND_OPEN_QUESTIONS.md`.
- Do not add a dependency, framework, or new top-level folder without asking.
- Do not break existing functionality: run the full test suite before and after your change.
- Prefer small, reviewable changes. Conventional commits (`feat:`, `fix:`, `test:`, `docs:`).
- After finishing a task: update its status in `TASK_TRACKER.md` and add a line under `[Unreleased]` in `CHANGELOG.md`.

## 3. Architecture rules (non-negotiable)
- Layers: `api → services → (repositories, scheduler, domain)`. Routers contain no business logic.
- `backend/app/scheduler/` is **pure Python**: no imports from `api`, `db`, `models`, `fastapi` or `sqlalchemy`. It takes dataclasses in and returns dataclasses out.
- The **validator is independent of the generator**. Never make the validator trust solver output; it recomputes from the roster, demand and supply.
- The engine never raises for "infeasible". It returns the best roster plus explicit shortfalls (coverage uses slack variables).
- Mandatory constraints always beat preferences. Coverage shortfall weight must dominate all preference weights.
- Output must be deterministic for the same input and seed. Use stable ordering.
- Rules are **data, not code**: calendar types, coverage minimums, weekly-off modes live in the database and are editable without code changes.
- Every conflict has: code, severity, brand-process, date(s), employee(s), root causes, plain-language message, suggestions.

## 4. Backend standards
- Python 3.12, type hints everywhere; `mypy --strict` on `scheduler/`.
- `ruff` for lint and format. Pydantic v2 schemas for all request/response bodies.
- SQLAlchemy 2.0 style; schema changes only through Alembic migrations (never edit an applied revision).
- Uniform error envelope from `API_DOCUMENTATION.md` §3; include `request_id`.
- Authorisation enforced server-side in dependencies/services, with a negative test for each guarded route.
- No secrets in code; configuration only via `core/config.py` and environment variables.

## 5. Frontend standards
- React 18 + TypeScript (`strict`), Vite, Tailwind with the tokens from `DESIGN_SYSTEM.md`, Radix primitives, TanStack Query/Table/Virtual.
- Use the design tokens; no ad-hoc colours, fonts or radii. Avoid gradients, glow, glassmorphism, card-in-card layouts.
- Every data view has loading (skeleton), empty, error and success states.
- Status is never colour-only: cells show a letter code (W, WO, PH, HW, L, CO).
- Keyboard accessible roster grid (`role="grid"`, roving tabindex).
- API calls only through the generated typed client and query hooks.

## 6. Testing requirements
- Engine changes need unit tests in the same change; add a regression test for every bug fixed in the engine.
- Keep property-based tests green (`TESTING_DOCUMENTATION.md` §3).
- Scenarios S1–S5 are golden tests; do not modify their expected outputs without owner approval.

## 7. Definition of done
Code and tests added, lint/type-check clean, all tests pass, docs and tracker updated, no secrets committed, behaviour matches the relevant document.

## 8. What to report back
Short summary: task IDs done, files changed, tests run and result, anything you were unsure about, and the next suggested task. Do not paste whole files into the summary.
