# Recommended Folder Structure

Monorepo: one repository, three deployable parts (API, web, docs). Layers mirror `SYSTEM_ARCHITECTURE.md`.

```
rosterops/
├── README.md                    # setup, architecture summary, the 8 "How do you think" answers
├── .env.example                 # placeholders for all variables (see DEPLOYMENT.md)
├── docker-compose.yml           # db + api + web for local development
├── .gitignore  .editorconfig
├── docs/                        # the Markdown blueprint (these files) + ADRs
│   ├── PROJECT_OVERVIEW.md  REQUIREMENTS.md  TECH_STACK.md  SYSTEM_ARCHITECTURE.md
│   ├── SCHEDULING_ENGINE.md  DATABASE_DESIGN.md  API_DOCUMENTATION.md
│   ├── UI_UX_REQUIREMENTS.md  DESIGN_SYSTEM.md  USER_FLOW.md
│   ├── PROJECT_ROADMAP.md  TASK_TRACKER.md  TESTING_DOCUMENTATION.md
│   ├── DEPLOYMENT.md  SECURITY.md  SAMPLE_DATA.md
│   ├── ASSUMPTIONS_AND_OPEN_QUESTIONS.md  CHANGELOG.md
│   └── adr/                     # short Architecture Decision Records (0001-use-cp-sat.md …)
│
├── backend/
│   ├── pyproject.toml           # uv project; ruff, mypy, pytest config
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── alembic/versions/        # migrations (0001_init …)
│   ├── app/
│   │   ├── main.py              # FastAPI app factory, middleware, router mounting
│   │   ├── core/                # config (pydantic-settings), security, logging, errors, deps
│   │   ├── api/
│   │   │   └── v1/              # routers: auth, pods, employees, brands, processes,
│   │   │                        #   brand_processes, assignments, rules, holidays,
│   │   │                        #   leaves, rosters, audit, health
│   │   ├── schemas/             # Pydantic request/response models
│   │   ├── services/            # use-cases: roster_service, leave_service, publish_service …
│   │   ├── repositories/        # DB access per aggregate
│   │   ├── models/              # SQLAlchemy ORM models + enums
│   │   ├── db/                  # engine, session, base, helpers
│   │   ├── scheduler/           # PURE Python engine (no DB/HTTP imports)
│   │   │   ├── domain.py        # dataclasses & enums (DemandCell, RosterCell, Conflict …)
│   │   │   ├── calendar.py      # operating-day resolver
│   │   │   ├── demand.py        # demand builder
│   │   │   ├── supply.py        # availability builder
│   │   │   ├── validator.py     # E001–E009, W001–W004
│   │   │   ├── explain.py       # plain-language messages
│   │   │   ├── generator_cpsat.py
│   │   │   ├── generator_greedy.py
│   │   │   ├── suggestions.py   # ranked resolutions
│   │   │   └── repair.py        # local repair (stretch)
│   │   └── seed/                # deterministic seed data (python -m app.seed)
│   └── tests/
│       ├── unit/scheduler/      # calendar, demand, supply, validator, generator, suggestions
│       ├── property/            # hypothesis invariants
│       ├── scenarios/           # S1–S5 golden tests
│       └── api/                 # endpoint, RBAC and error-format tests
│
└── frontend/
    ├── package.json  vite.config.ts  tailwind.config.ts  tsconfig.json
    ├── index.html
    └── src/
        ├── main.tsx  App.tsx  routes.tsx
        ├── styles/              # tokens.css, globals.css (from DESIGN_SYSTEM.md)
        ├── api/                 # generated client + fetch wrapper + query hooks
        ├── components/
        │   ├── ui/              # Button, Input, Select, Modal, Drawer, Popover, Table, Badge, Toast, Skeleton, EmptyState
        │   └── roster/          # RosterGrid, Cell, CoverageStrip, Heatmap, ConflictDrawer, ImpactPanel
        ├── features/            # auth, dashboard, roster, conflicts, leaves, team, brands, rules, settings
        ├── hooks/  lib/  types/
        └── tests/
```

## Conventions
| Topic | Rule |
|---|---|
| Dependency direction | `api → services → (repositories, scheduler, domain)`; `scheduler` imports nothing from `app.api/db/models` |
| Naming | Python `snake_case`, classes `PascalCase`; TS `camelCase`, components `PascalCase`; API JSON `snake_case` |
| Typing | `mypy --strict` on `scheduler/`; TypeScript `strict: true` |
| Style | `ruff` lint + format; ESLint + Prettier |
| Commits | Conventional commits (`feat:`, `fix:`, `docs:`); small, reviewable |
| Config | Only via `core/config.py`; no `os.environ` scattered in code |
| Decisions | Any non-obvious choice gets a 10-line ADR in `docs/adr/` |
| Migrations | One Alembic revision per schema change; never edit applied revisions |
| Tests | Mirror source layout; engine changes require tests in the same PR |
