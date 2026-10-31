# Build Prompts — paste one slice at a time

How to use: start a **new agent session per slice**, paste the prompt, review the result, run the tests yourself, then move on. Never paste several slices at once. Each prompt assumes `AGENTS.md` is in the repo root.

**Decisions status:** All blocking decisions Q1–Q6 and deadline Q11 are confirmed by the owner (React 18 + TS SPA, day-level granularity, 1 mandatory weekly off pro-rated $\ge 4$ d = 1, 4 floaters held as backups with dynamic assignment via suggestions, CP-SAT generation with manager publish gating, simultaneous multi-brand coverage with overload warning, and 4-day deadline targeting Level 1 demo-able core first).

Scope level tags: **[L1]** demo-able core · **[L2]** complete product · **[L3]** polish (see `PROJECT_ROADMAP.md`).

---

## Slice A — Repository and scaffold [L1] (T-201 – T-206)
```
Read AGENTS.md, docs/TECH_STACK.md, docs/FOLDER_STRUCTURE.md and docs/DESIGN_SYSTEM.md.
Task IDs: T-201 to T-206.
Create the monorepo exactly as in FOLDER_STRUCTURE.md: backend (FastAPI, uv, pydantic-settings, ruff, mypy, pytest,
Alembic configured, GET /health), docker-compose with Postgres 16, .env.example usage, and frontend
(Vite + React + TypeScript + Tailwind + React Router + TanStack Query) with the design tokens from DESIGN_SYSTEM.md
and fonts Inter and IBM Plex Mono.
Do not implement any business features yet.
Done when: `docker compose up -d db`, `alembic upgrade head`, the API /health, and the themed blank frontend all run,
and COMMANDS.md commands work. Update TASK_TRACKER.md statuses and CHANGELOG.md. Report what you ran.
```

## Slice B — Scheduling engine on paper [L1] (T-501 – T-506, T-508) — **highest risk, do early**
```
Read AGENTS.md and docs/SCHEDULING_ENGINE.md fully, plus docs/TESTING_DOCUMENTATION.md sections 2–3.
Task IDs: T-501 to T-506, T-508.
Implement backend/app/scheduler as PURE Python (no DB, no FastAPI, no SQLAlchemy):
domain dataclasses/enums, calendar resolver, demand builder, supply builder, validator (E001–E009, W001–W004),
explainer (plain-language messages with brand, process, date, person), and the CP-SAT generator using coverage slack
variables (hard constraints H1–H5, soft preferences P1–P6, coverage shortfall weight must dominate all preference weights).
Write unit tests for every case TC-CAL, TC-DEM, TC-SUP, TC-VAL, TC-GEN in TESTING_DOCUMENTATION.md using in-memory fixtures.
Ask me before choosing weights or changing any rule in the document.
Done when: mypy --strict passes on scheduler/, all those tests pass, same seed gives an identical roster, infeasible
inputs return a roster plus explicit shortfalls instead of raising. Report test output.
```

## Slice C — Data layer and seed [L1] (T-301 – T-305, T-309)
```
Read AGENTS.md, docs/DATABASE_DESIGN.md, docs/SAMPLE_DATA.md, docs/API_DOCUMENTATION.md §3.
Task IDs: T-301 to T-305, T-309.
Create SQLAlchemy 2.0 models for every table in DATABASE_DESIGN.md (enums, constraints, indexes, partial unique index
for one PUBLISHED roster per month), one reviewed Alembic migration, Pydantic base schemas and the uniform error
envelope with request_id, and a deterministic idempotent seed (`python -m app.seed`) producing the dataset in SAMPLE_DATA.md
for December 2026 including everything needed by scenarios S1–S5.
Before writing the seed, show me the exact headcount arithmetic (36 employees, 25 brands, 20 single-resource, 5 multi)
and wait for approval.
Done when: migration applies on empty DB, seed runs twice with identical results, and counts match SAMPLE_DATA.md.
```

## Slice D — Generate and read APIs [L1] (T-509, T-510)
```
Read AGENTS.md, docs/SYSTEM_ARCHITECTURE.md §5, docs/API_DOCUMENTATION.md (Roster section).
Task IDs: T-509, T-510.
Add the service layer that loads month inputs in batched queries, maps them to scheduler dataclasses, runs
generator + validator, persists roster_period, roster_entries and roster_conflicts, and exposes
POST /rosters, GET /rosters, GET /rosters/{id}, /grid?view=company|pod|brand|process|employee, /coverage, /day, /conflicts.
Keep routers thin. Add API tests for happy and failure paths.
Done when: generating December 2026 from the seed returns a roster with summary counts and conflicts, and all five
grid views return correct data. Report timings for a 36-employee month.
```

## Slice E — Impact and suggestions [L1] (T-511, T-513) — **core of the demo video**
```
Read AGENTS.md, docs/SCHEDULING_ENGINE.md sections 9–10, docs/SAMPLE_DATA.md scenarios S1–S3.
Task IDs: T-511, T-513.
Implement POST /rosters/{id}/impact (dry run, nothing persisted; revalidate only affected dates; diff into new,
resolved, unchanged conflicts) and GET /rosters/{id}/suggestions (backup/floater, weekly-off swap, ranked, each simulated
through the validator and reported as "fixes N / opens M").
Add golden tests for scenarios S1, S2, S3 asserting exact conflict codes, dates, root causes and the top suggestion.
Done when: adding a leave for the single-resource brand in S1 shows the expected gaps and a floater suggestion that
fixes them with opens 0.
```

## Slice F — Roster UI [L1] (T-601, T-602, T-607, T-608, T-609, T-611, T-612, T-614, T-701, T-702, T-704, T-705)
```
Read AGENTS.md, docs/DESIGN_SYSTEM.md, docs/UI_UX_REQUIREMENTS.md (S2–S5), docs/USER_FLOW.md.
Task IDs: listed above.
Build the app shell, the shared components needed (Button, Input, Select, Drawer, Popover, Table, Badge, Toast,
Skeleton, EmptyState), the virtualised RosterGrid with letter-coded status cells, coverage strips, the five views and
day view, the conflict drawer, and the impact simulator. Generate the typed API client from /openapi.json and use
TanStack Query hooks only. Include loading, empty and error states everywhere.
Follow the design tokens exactly; no gradients, glow, glassmorphism or card-in-card layouts.
Done when: from the browser I can Generate, switch all five views, open a conflict, preview a leave's impact and apply a
suggestion. Show me screenshots at 1440px and 768px.
```

## Slice G — Deploy early [L1] (T-1001 – T-1004)
```
Read AGENTS.md and docs/DEPLOYMENT.md.
Task IDs: T-1001 to T-1004.
Write production Dockerfiles, deployment configuration for the hosts I choose (confirm hosts with me), CORS from
environment, pre-deploy migrations, and a smoke-test script. Do not commit secrets.
Done when: a public URL serves the seeded demo and the smoke test passes from a fresh browser.
```

---

## Slice H — Master data CRUD and auth [L2] (T-306 – T-308, T-603 – T-606, T-703, T-401 – T-405)
```
Read AGENTS.md, docs/API_DOCUMENTATION.md, docs/SECURITY.md, docs/UI_UX_REQUIREMENTS.md (S6–S9), docs/USER_FLOW.md §1.
Implement CRUD APIs and screens for pods, employees, processes, brands, brand-processes, coverage rules, assignments,
holidays, weekly-off rules, preferences, leaves; JWT login with Argon2, refresh rotation and role guards
(OPS_MANAGER, POD_LEAD, EMPLOYEE) enforced server-side with negative tests.
Prefer one reusable schema-driven table + drawer component over many bespoke screens.
Done when: I can add a new brand, process and assignment from the UI, regenerate the roster, and see it appear;
RBAC tests pass.
```

## Slice I — Edit, lock, publish [L2] (T-512, T-515, T-610)
```
Read AGENTS.md, docs/SYSTEM_ARCHITECTURE.md §5.2 and §5.4, docs/API_DOCUMENTATION.md (entries, publish).
Implement validated cell edits with locks and audit entries, acknowledge-with-reason, publish gating (422 ROSTER_BLOCKED),
clone as a new version, and the cell edit popover showing live impact before Apply.
Done when: scenario S5 blocks publish until each blocking conflict is acknowledged with a reason, and editing a
published roster creates a new draft.
```

## Slice J — Tests, hardening, submission [L2] (T-801, T-803, T-807, T-903, T-1005 – T-1008)
```
Read AGENTS.md, docs/TESTING_DOCUMENTATION.md, docs/SECURITY.md §10, and docs/SAMPLE_DATA.md.
Add the property-based invariants, run the security checklist, fix defects found, then draft the README including the
eight "How do you think" answers from the assessment brief, the approach note, the submission email, and a demo script
for scenarios S1–S5 (3–5 minutes). Ask me to confirm each answer's wording before finalising.
```

---

## Slice K — Polish [L3]
Greedy fallback generator (T-507), comp-off logic (T-514), dashboard (T-613), audit API (T-519), cache invalidation (T-706), API test completion (T-804), performance and index tuning (T-901, T-902), dependency audit (T-905), CHANGELOG sync (T-1009). Use one prompt per item in the same format: *read → task IDs → what to build → done when*.

## Prompt template
```
Read AGENTS.md and <specific docs>.
Task IDs: <ids>.
Build: <what>.
Constraints: <anything from the docs that must not be violated>.
Ask me before: <decisions you must not guess>.
Done when: <observable result> + tests pass + tracker/CHANGELOG updated. Report commands run and results.
```
