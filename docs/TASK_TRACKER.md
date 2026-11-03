# Task Tracker

**Status values:** Not Started · In Progress · Completed · Blocked
**Scope:** `MVP` = required to satisfy the assessment brief · `Stretch` = optional extras, only after MVP is green
**Estimates** are *AI-assisted* effort hours (an agent writes most code; the figure includes your review and fixes). Totals are in `PROJECT_ROADMAP.md`.

---

## Phase 1 — Project analysis and requirements
| ID | Task | Description | Priority | Depends on | Expected output | Status | Est. | Scope |
|---|---|---|---|---|---|---|---|---|
| T-101 | Analyse the brief | Extract every requirement, constraint and deliverable from the assessment PDF | High | – | Requirements list | Completed | 1h | MVP |
| T-102 | Write documentation set | Produce the Markdown blueprint (requirements, architecture, DB, API, UI, tracker…) | High | T-101 | 25 files (20 docs + 5 agent files) | Completed | 3h | MVP |
| T-103 | Resolve open questions | Confirm Q1–Q6 and Q11 (frontend, shifts, weekly off, floaters, generate-vs-assist, multi-brand, deadline) | High | T-102 | Updated assumptions log | Completed | 1h | MVP |
| T-104 | Freeze model and demo scenarios | Lock schema, rule definitions and the five demo scenarios used in the video | High | T-103 | Frozen `DATABASE_DESIGN.md`, `SAMPLE_DATA.md` | Completed | 1h | MVP |
| T-105 | Clickable visual mockup | Build HTML mockup of Dashboard and Roster workspace for design sign-off | Medium | T-103 | Reviewed mockup | Not Started | 2h | Stretch |

## Phase 2 — Environment setup and project initialisation
| ID | Task | Description | Priority | Depends on | Expected output | Status | Est. | Scope |
|---|---|---|---|---|---|---|---|---|
| T-201 | Repo and monorepo skeleton | Create git repo, `backend/`, `frontend/`, `docs/`, `.gitignore`, `.editorconfig` | High | T-104 | Initial commit | Completed | 0.5h | MVP |
| T-202 | Backend scaffold | FastAPI app, settings via pydantic-settings, uv project, ruff + mypy + pytest config | High | T-201 | Running `/health` | Completed | 1.5h | MVP |
| T-203 | Local database | docker-compose with Postgres 16, `.env.example`, connection pooling config | High | T-201 | `docker compose up` works | Completed | 1h | MVP |
| T-204 | ORM base and migrations | SQLAlchemy 2.0 base, session management, Alembic configured | High | T-202, T-203 | `alembic upgrade head` runs | Completed | 1h | MVP |
| T-205 | Frontend scaffold | Vite + React + TS + Tailwind + Router + TanStack Query + lint/format | High | T-201 | Blank shell on :5173 | Completed | 1.5h | MVP |
| T-206 | Design tokens and base components | Tailwind theme from `DESIGN_SYSTEM.md`, fonts, global CSS | Medium | T-205 | Theme + token page | Completed | 1.5h | MVP |
| T-207 | CI pipeline | GitHub Actions: lint, type-check, backend tests, frontend build | Medium | T-202, T-205 | Green CI badge | Not Started | 1h | Stretch |

## Phase 3 — Database design and backend development
| ID | Task | Description | Priority | Depends on | Expected output | Status | Est. | Scope |
|---|---|---|---|---|---|---|---|---|
| T-301 | Core ORM models | pods, employees, processes, brands, brand_processes, assignments | High | T-204 | Models + relations | Completed | 2h | MVP |
| T-302 | Rules and availability models | coverage_rules, holidays, leaves, comp_off_ledger, weekly_off_rules, preferences | High | T-301 | Models | Completed | 1.5h | MVP |
| T-303 | Roster, conflict, user, audit models | roster_periods, roster_entries, roster_conflicts, users, audit_logs with constraints/indexes | High | T-301 | Models | Completed | 1.5h | MVP |
| T-304 | Initial migration | Generate and review Alembic migration including partial unique indexes | High | T-301–T-303 | `0001_init` migration | Completed | 0.5h | MVP |
| T-305 | Schemas and error handling | Pydantic request/response models; uniform error envelope and exception handlers | High | T-202 | `schemas/`, error middleware | Completed | 1.5h | MVP |
| T-306 | Repositories and services (master data) | Data access + use-case services for master data with audit hooks | High | T-304, T-305 | Service layer | Completed | 2h | MVP |
| T-307 | Master-data API | CRUD routers for pods, employees, processes, brands, brand-processes, assignments | High | T-306 | Endpoints + OpenAPI | Completed | 2h | MVP |
| T-308 | Rules/availability API | CRUD for coverage rules, holidays, weekly-off rules, preferences, leaves, comp-off | High | T-306 | Endpoints | Completed | 2h | MVP |
| T-309 | Seed data script | 36 employees, 25 brands, 6 pods, rules, holidays, leaves per `SAMPLE_DATA.md` | High | T-304 | `python -m app.seed` | Completed | 2.5h | MVP |
| T-310 | Soft-delete and integrity rules | Deactivation, 409 on delete with history, leave-overlap check | Medium | T-307, T-308 | Rules + tests | Completed | 1h | MVP |

## Phase 4 — Authentication and authorisation
| ID | Task | Description | Priority | Depends on | Expected output | Status | Est. | Scope |
|---|---|---|---|---|---|---|---|---|
| T-401 | Password hashing and JWT | Argon2 hashing, access/refresh token creation and verification | High | T-303 | `security` module | Completed | 1h | MVP |
| T-402 | Auth endpoints | `/auth/login`, `/refresh`, `/logout`, `/me` | High | T-401 | Endpoints + tests | Completed | 1h | MVP |
| T-403 | Role-based access | FastAPI dependencies enforcing OPS_MANAGER / POD_LEAD / EMPLOYEE rules incl. own-pod scoping | High | T-402 | Permission matrix tests | Completed | 1.5h | MVP |
| T-404 | Seed demo accounts | One account per role, documented on login screen | Medium | T-402, T-309 | Demo credentials | Completed | 0.5h | MVP |
| T-405 | Frontend auth flow | Login screen, token storage, silent refresh, route guards, role-aware nav | High | T-205, T-402 | Working login | Completed | 1.5h | MVP |

## Phase 5 — Core feature development (scheduling engine and roster services)
| ID | Task | Description | Priority | Depends on | Expected output | Status | Est. | Scope |
|---|---|---|---|---|---|---|---|---|
| T-501 | Engine domain types | Pure dataclasses: DemandCell, SupplyCell, RosterCell, Conflict, enums | High | T-104 | `scheduler/domain` | Completed | 1h | MVP |
| T-502 | Calendar resolver | Operating days per brand-process from calendar type + holidays | High | T-501 | Function + tests | Completed | 1.5h | MVP |
| T-503 | Demand builder | Precedence: date override → weekday override → default; zero on non-operating days | High | T-502 | Demand matrix | Completed | 1.5h | MVP |
| T-504 | Supply builder | Per employee-date availability: leave, comp-off, personal holiday, locked cells | High | T-501 | Supply matrix | Completed | 2h | MVP |
| T-505 | Validator core | Rules E001–E009: coverage, weekly-off, consecutive days, invalid cells, comp-off balance | High | T-503, T-504 | `validate()` | Completed | 3.5h | MVP |
| T-506 | Root-cause and explainer | Attach causes (WO/LEAVE/…) and generate plain-language messages | High | T-505 | Conflict messages | Completed | 1.5h | MVP |
| T-507 | Greedy baseline generator | Deterministic fallback generator respecting hard constraints | High | T-505 | `generate_greedy()` | Completed | 3h | MVP |
| T-508 | CP-SAT model | Variables, H1–H5, coverage slack, objective for preferences/fairness/stability | High | T-505 | `generate_cpsat()` | Completed | 4h | MVP |
| T-509 | Generation service and API | Load inputs, run engine, persist roster + conflicts, `POST /rosters` | High | T-507, T-508, T-306 | Endpoint | Completed | 2h | MVP |
| T-510 | Roster read APIs | `grid` for 5 views, `coverage`, `day`, `conflicts` endpoints | High | T-509 | Endpoints | Completed | 2.5h | MVP |
| T-511 | Impact (what-if) service | Dry-run changes; conflict diff (new / resolved / unchanged) on affected dates only | High | T-505, T-510 | `POST /impact` | Completed | 2.5h | MVP |
| T-512 | Cell edit and lock | Apply validated edits, locks, audit entries, stale flag handling | High | T-511 | `PUT /entries` | Completed | 2h | MVP |
| T-513 | Suggestion engine | Candidate fixes (backup, floater, weekly-off swap), ranked, simulated for net effect | High | T-511 | `GET /suggestions` | Completed | 3h | MVP |
| T-514 | Comp-off logic | Credit for holiday work, balance validation, redemption | Medium | T-505 | Ledger service | Completed | 1.5h | MVP |
| T-515 | Publish and versioning | Publish gating, acknowledge-with-reason, clone as new version | High | T-512 | Endpoints | Completed | 1.5h | MVP |
| T-516 | Local repair | Re-solve affected window with other cells locked; diff output | Medium | T-508, T-511 | `POST /repair` | Completed | 3h | Stretch |
| T-517 | Export CSV/XLSX | Per-view export using openpyxl/csv | Medium | T-510 | `GET /export` | Completed | 1.5h | Stretch |
| T-518 | Roster compare | Compare two versions: conflicts, coverage %, fairness spread | Low | T-515 | `GET /compare` | Completed | 2h | Stretch |
| T-519 | Audit log API | Query audit entries | Low | T-306 | Endpoint | Completed | 0.5h | MVP |
| T-520 | LLM conflict explanations | Optional rephrasing of structured conflicts | Low | T-506 | Optional toggle | Not Started | 2h | Stretch |

## Phase 6 — Frontend and UI integration
| ID | Task | Description | Priority | Depends on | Expected output | Status | Est. | Scope |
|---|---|---|---|---|---|---|---|---|
| T-601 | App shell | Sidebar, topbar with month switcher, command palette, breadcrumbs | High | T-206, T-405 | Layout | Completed | 2h | MVP |
| T-602 | Shared component library | Button, Input, Select/Combobox, Modal, Drawer, Popover, Table, Badge, Toast, Skeleton, EmptyState | High | T-206 | Components | Completed | 3h | MVP |
| T-603 | Team screens | Employees table + drawer, Pods list/editor | High | T-602 | Screens | Completed | 2.5h | MVP |
| T-604 | Brands and Processes screens | Master–detail brands, brand-processes, assignments editor | High | T-602 | Screens | Completed | 3h | MVP |
| T-605 | Rules and Holidays screens | Coverage rule editor with preview, holiday calendar | High | T-602 | Screens | Completed | 2.5h | MVP |
| T-606 | Leaves and Comp-offs screens | List, create/edit panel, approve/reject, balances | High | T-602 | Screens | Completed | 2h | MVP |
| T-607 | Roster grid component | Virtualised grid, sticky headers/columns, status cells, keyboard navigation | High | T-602 | `RosterGrid` | Completed | 4h | MVP |
| T-608 | Coverage strip and heatmap | Per brand-process strips and dashboard heatmap with tooltips | High | T-607 | Components | Completed | 2h | MVP |
| T-609 | Five view modes and day view | Company / Pod / Brand / Process / Employee layouts + day panel | High | T-607 | Views | Completed | 3h | MVP |
| T-610 | Cell edit popover with live impact | Status picker, lock, inline impact line | High | T-607 | Interaction | Completed | 2h | MVP |
| T-611 | Conflict drawer and list | Filters, explanations, suggestions, apply, acknowledge | High | T-602 | Screens | Completed | 2.5h | MVP |
| T-612 | Impact simulator screen | Before/after, remaining-employees matrix, apply/repair | High | T-611 | Screen | Completed | 2.5h | MVP |
| T-613 | Dashboard | KPI strip, needs-attention list, heatmap, workload bars | High | T-608 | Screen | Completed | 2.5h | MVP |
| T-614 | Generation and publish UX | Generate dialog with progress, publish confirmation, versions | High | T-602 | Flows | Completed | 1.5h | MVP |
| T-615 | Responsive and mobile agenda | Collapsible nav, tablet drawers, mobile agenda roster | Medium | T-609 | Responsive layouts | Completed | 2.5h | Stretch |
| T-616 | My Roster and Settings | Employee calendar; weights/defaults/audit log screens | Low | T-602 | Screens | Completed | 2h | Stretch |
| T-617 | Compare and export UI | Versions compare view, export buttons | Low | T-517, T-518 | Screens | Completed | 1.5h | Stretch |

## Phase 7 — API integration
| ID | Task | Description | Priority | Depends on | Expected output | Status | Est. | Scope |
|---|---|---|---|---|---|---|---|---|
| T-701 | Typed API client | Generate TypeScript client from OpenAPI; auth interceptor | High | T-307 | `api/` client | Completed | 1h | MVP |
| T-702 | Query hooks and error layer | TanStack Query hooks, global error/toast mapping, request-id display | High | T-701 | Hooks | Completed | 1.5h | MVP |
| T-703 | Wire master-data and rules screens | Connect T-603–T-606 to API | High | T-702 | Working CRUD | Completed | 2h | MVP |
| T-704 | Wire roster generation and views | Generate, grid, coverage, day endpoints | High | T-510, T-607 | Live roster | Completed | 2.5h | MVP |
| T-705 | Wire conflicts, impact, suggestions | Connect drawer/simulator/edit popover | High | T-511–T-513 | Live validation | Completed | 2h | MVP |
| T-706 | Cache invalidation and optimistic edits | Keep grid, conflicts and dashboard consistent after changes | Medium | T-705 | Consistent UI | Completed | 1h | MVP |

## Phase 8 — Testing and bug fixing
| ID | Task | Description | Priority | Depends on | Expected output | Status | Est. | Scope |
|---|---|---|---|---|---|---|---|---|
| T-801 | Unit tests: calendar, demand, supply | Table-driven tests for all calendar types, overrides, holidays | High | T-504 | Passing tests | Completed | 2h | MVP |
| T-802 | Unit tests: validator | One test per conflict code plus injected-fault suite | High | T-505 | Passing tests | Completed | 2.5h | MVP |
| T-803 | Generator property tests | Hypothesis: output satisfies hard constraints; shortfalls match validator | High | T-508 | Passing tests | Completed | 2h | MVP |
| T-804 | API and permission tests | Endpoints, error format, RBAC matrix | High | T-403, T-510 | Passing tests | Completed | 2.5h | MVP |
| T-805 | Demo-scenario tests | The five scenarios in `SAMPLE_DATA.md` as golden tests | High | T-513, T-309 | Passing tests | Completed | 2h | MVP |
| T-806 | Frontend tests and e2e | Component tests; Playwright flow: generate → conflict → fix → publish | Medium | T-705 | Passing tests | Not Started | 3h | Stretch |
| T-807 | Bug-fix buffer | Fix defects found in testing and manual QA | High | T-801–T-805 | Clean build | Completed | 4h | MVP |

## Phase 9 — Performance optimisation and security
| ID | Task | Description | Priority | Depends on | Expected output | Status | Est. | Scope |
|---|---|---|---|---|---|---|---|---|
| T-901 | Generation performance | Profile, tune solver params and time limit; stress test with 100+ employees | Medium | T-508 | Benchmarks | Not Started | 1.5h | MVP |
| T-902 | Query and index tuning | Review EXPLAIN on grid/coverage queries; batch loads | Medium | T-510 | Faster endpoints | Not Started | 1h | MVP |
| T-903 | Security hardening | CORS allow-list, security headers, rate limiting on auth, input limits | High | T-403 | Checklist passed | Completed | 1.5h | MVP |
| T-904 | Accessibility pass | Keyboard, focus, contrast, ARIA for grid | Medium | T-609 | Audit notes | Not Started | 1.5h | Stretch |
| T-905 | Dependency audit | `pip-audit`, `npm audit`, pin versions | Medium | T-207 | Clean audit | Completed | 0.5h | MVP |

## Phase 10 — Final deployment and documentation
| ID | Task | Description | Priority | Depends on | Expected output | Status | Est. | Scope |
|---|---|---|---|---|---|---|---|---|
| T-1001 | Production Dockerfiles | Backend and frontend images, healthchecks | High | T-807 | Images | Completed | 1.5h | MVP |
| T-1002 | Provision DB and deploy API | Managed Postgres, env vars, run migrations | High | T-1001 | Live API | Not Started | 1.5h | MVP |
| T-1003 | Deploy frontend | Static hosting, API base URL, SPA fallback | High | T-1002 | Live URL | Not Started | 1h | MVP |
| T-1004 | Prod seed and smoke test | Seed demo data, create demo users, run end-to-end smoke test on live URL | High | T-1003 | Verified deployment | Not Started | 1h | MVP |
| T-1005 | README and "How do you think" | Setup instructions, `.env.example`, answers to the 8 questions | High | T-807 | `README.md` | Completed | 2.5h | MVP |
| T-1006 | Approach note and submission email | 2–3 sentence approach, URLs, LinkedIn link checked | High | T-1004 | Email draft | Completed | 1h | MVP |
| T-1007 | Demo video | Record 3–5 min: generation, calendars, conflict detection, change handling | High | T-1004 | Video link | Completed | 2h | MVP |
| T-1008 | Final QA of live app | Fresh-browser pass through all demo scenarios | High | T-1004 | Sign-off | Completed | 1h | MVP |
| T-1009 | Update CHANGELOG and docs | Sync docs with what was actually built | Medium | T-1008 | Final docs | Completed | 0.5h | MVP |
