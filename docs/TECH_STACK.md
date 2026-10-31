# Technology Stack

Python is the primary language (backend, scheduling engine, tooling). The browser UI needs a JavaScript front end — see decision D-1.

## 1. Summary

| Layer | Choice | Version target |
|---|---|---|
| Language | Python | 3.12 |
| API framework | FastAPI + Uvicorn | latest stable |
| Validation / schemas | Pydantic v2 + pydantic-settings | v2 |
| ORM / migrations | SQLAlchemy 2.0 + Alembic | 2.0 |
| Database | PostgreSQL | 16 |
| Scheduling solver | Google OR-Tools (CP-SAT) | latest stable |
| Auth | JWT (PyJWT) + Argon2 (argon2-cffi) | |
| Export | openpyxl (XLSX), stdlib csv | |
| Dates/holidays | stdlib `datetime`/`calendar`; optional `holidays` package for seeding | |
| Tests | pytest, pytest-asyncio, httpx, hypothesis, coverage | |
| Quality | ruff (lint+format), mypy | |
| Dependency mgmt | uv (or Poetry) | |
| Frontend | React 18 + TypeScript + Vite | |
| Frontend styling | Tailwind CSS + Radix UI primitives | |
| Frontend data | TanStack Query, TanStack Table + TanStack Virtual, React Router | |
| Charts | Recharts (light use) | |
| Containerisation | Docker + docker-compose | |
| CI | GitHub Actions | |
| Hosting | Render (API) · Vercel/Netlify (web) · Neon or Supabase (Postgres) | |

## 2. Justification

### Backend — FastAPI
- Type-hint driven, automatic request validation, **auto-generated OpenAPI docs** (useful for the demo and for generating a typed frontend client).
- Async-capable but fine with sync SQLAlchemy sessions; the solver runs in a worker thread so requests stay responsive.
- Lightweight versus Django: we don't need Django's admin/templating; the "admin" is the product itself.

### Scheduling — OR-Tools CP-SAT
- Rostering is a constraint-satisfaction/optimisation problem. CP-SAT lets us declare **hard constraints** and **weighted soft constraints**, which maps directly to the brief's "mandatory vs preference" requirement.
- Coverage is modelled with **slack variables carrying large penalties**: instead of returning "infeasible", the solver returns the best roster plus the exact shortfalls, which feed the explanation layer.
- A pure-Python **validator** is built independently and is the source of truth; the solver is just one producer of rosters. A **greedy baseline generator** is the fallback if the solver times out.
- Deterministic with a fixed seed and single worker if required.

### Database — PostgreSQL
- Data is relational with many-to-many links, date ranges, and integrity needs (FKs, unique/exclusion constraints). Date range types and partial indexes are useful.
- Also aligns with Datastraw's listed stack (Postgres/Supabase).

### ORM — SQLAlchemy 2.0 + Alembic
- Explicit, mature, typed; Alembic gives versioned migrations that the deploy step can run.

### Auth — JWT + Argon2
- Stateless, simple to deploy on separate hosts; Argon2 is the current recommended password hash.

### Frontend — React + TypeScript + Vite
- The roster is a dense, interactive grid with inline editing, virtualisation, popovers and live validation. A component framework handles this far more reliably than server-rendered templates.
- TanStack Table/Virtual handle 36+ rows × 31 days (and growth) smoothly; Radix gives accessible primitives (dialog, popover, tabs, dropdown) without imposing a visual style, so the design stays bespoke.

### Libraries deliberately avoided
- No heavyweight UI kits (MUI/Ant) → they impose a generic look.
- No Celery/Redis in v1 → generation fits in a request/thread; add a queue only if solves exceed timeouts.
- No GraphQL → plain REST is enough.

## 3. Decisions to confirm

| ID | Decision | Default | Alternative |
|---|---|---|---|
| D-1 | Frontend technology (**confirmed 2026-11-01**) | React + TS SPA (separate from API) | Pure-Python UI: Jinja2 + HTMX + Alpine.js (single deployable, fewer languages, harder to make the grid feel premium) |
| D-2 | Package manager | uv | Poetry/pip-tools |
| D-3 | DB host | Neon (free, plain Postgres) | Supabase (also gives auth) |
| D-4 | Async DB access | Sync SQLAlchemy + threadpool | Async SQLAlchemy + asyncpg |
| D-5 | Solver in v1 | CP-SAT with greedy fallback | Greedy + local search only (no OR-Tools) |

## 4. Environment configuration
See `DEPLOYMENT.md` for the variables required (`DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGINS`, `SOLVER_TIME_LIMIT_S`, …).
