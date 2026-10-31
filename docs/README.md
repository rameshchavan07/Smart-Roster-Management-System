# Smart Roster Management System — Project Blueprint

Planning documentation for the Datastraw tech-internship assessment: a browser-based tool that lets an operations manager **plan, generate, validate and manage monthly rosters** across brands, processes and pods, with reliable coverage checking and clear conflict explanations.

> Status: **Blueprint v0.1 — no application code yet.** Some decisions are awaiting your confirmation; see `ASSUMPTIONS_AND_OPEN_QUESTIONS.md`.

## Read in this order
| # | File | Purpose |
|---|---|---|
| 1 | `PROJECT_OVERVIEW.md` | What and why |
| 2 | `REQUIREMENTS.md` | Functional / non-functional requirements (tagged brief vs recommendation) |
| 3 | `ASSUMPTIONS_AND_OPEN_QUESTIONS.md` | **Start here for decisions you need to make** |
| 4 | `TECH_STACK.md` | Python-first stack and justification |
| 5 | `SYSTEM_ARCHITECTURE.md` | Components, layers, data flows |
| 6 | `SCHEDULING_ENGINE.md` | Constraints, validator, generator, suggestions (the core) |
| 7 | `DATABASE_DESIGN.md` | Tables, ER diagram |
| 8 | `API_DOCUMENTATION.md` | Endpoints, errors, examples |
| 9 | `UI_UX_REQUIREMENTS.md`, `DESIGN_SYSTEM.md`, `USER_FLOW.md` | Screens, visual system, journeys |
| 10 | `SAMPLE_DATA.md` | Dataset shape and the 5 demo scenarios |
| 11 | `PROJECT_ROADMAP.md`, `TASK_TRACKER.md` | Phases, scope levels, 91 tasks |
| 12 | `TESTING_DOCUMENTATION.md`, `DEPLOYMENT.md`, `SECURITY.md` | Quality, release, protection |
| 13 | `FOLDER_STRUCTURE.md`, `CHANGELOG.md` | Repo layout, history |

## The idea in one paragraph
Treat the problem as **demand vs supply**. *Demand* is what each brand-process needs per day (from its operating calendar and coverage rules). *Supply* is who can work (assignments minus weekly offs, holidays, leaves, comp-offs). A solver proposes a roster; an **independent validator** checks it and explains every gap in plain language; the manager previews the impact of any change, picks a ranked suggestion, and publishes only when blocking conflicts are resolved or consciously acknowledged.

## Key decisions at a glance
| Decision | Choice | Status |
|---|---|---|
| Language | Python | **Confirmed** |
| API | FastAPI + SQLAlchemy 2.0 + Alembic | **Confirmed** |
| Database | PostgreSQL 16 | **Confirmed** |
| Solver | OR-Tools CP-SAT with pure-Python validator and greedy fallback | **Confirmed** |
| Frontend | React 18 + TypeScript + Tailwind (separate SPA) | **Confirmed** |
| Granularity | Day-level roster, no shifts in v1 (extensible schema) | **Confirmed** |
| Backups | 4 Floaters pool; assigned dynamically via suggestion engine | **Confirmed** |

## Scope reality
The full MVP in the tracker is about **141 hours remaining** (80 MVP tasks total, 4h completed, 141h remaining) at AI-assisted estimates, while the brief expects roughly 1.5–2 days of focused work within a 4-day deadline. `PROJECT_ROADMAP.md` defines three build levels (L1 demo-able core = 87 h, L2 = +38.5 h, L3 = +15.5 h). We target **Level 1 (demo-able core)** first to guarantee a working submission, then expand to L2/L3 as time permits.

## Next step
All blocking questions (Q1–Q6) and deadline scope (Q11) are confirmed. Next: freeze the schema and demo scenarios (T-104) and execute Slice 0 / Slice A/B: the pure-Python scheduling engine and its tests.

> When the application exists, this README is replaced by the repository README with setup instructions and the eight "How do you think" answers required by the brief.
