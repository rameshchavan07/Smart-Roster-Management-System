# Project Roadmap

Task-level detail is in `TASK_TRACKER.md`. Hour figures below were **computed from the tracker by script**, not estimated by hand. They are AI-assisted effort estimates and are probably conservative; **re-baseline after the first working day** using real velocity.

## 1. Reality check on scope

| Measure | Hours |
|---|---|
| Tracker total (all 91 tasks) | 167 |
| MVP tasks only (80 tasks) | 145 |
| MVP still to do (T-101–T-104, T-201–T-203 done) | 136.0 |
| Brief's own expectation | ~1.5–2 days of focused work, 4-day deadline |

The full blueprint is larger than what the brief asks for. The tracker therefore uses **scope levels**; build level by level and stop when time runs out. Every level ends in something demo-able.

| Level | What it adds | Tasks | Hours | Cumulative (remaining) |
|---|---|---|---|---|
| *Completed* | Setup & database (`T-101`–`T-104`, `T-201`–`T-203`) | 7 | 9.0 | 9.0 (done) |
| **L1 — Demo-able core** | Scaffold, models, seed, full engine (calendar → demand → supply → validator → explainer → CP-SAT), generate/read/impact/suggestion APIs, roster grid + views + conflict drawer + impact simulator, deployment, README, video | 44 | 84.0 | 84.0 |
| **L2 — Complete product** | CRUD screens for all master data, leaves UI, auth + roles, cell edit/lock, publish + versioning, cell popover with live impact, unit/property tests, security hardening | 20 | 38.5 | 122.5 |
| **L3 — Polish** | Greedy fallback generator, comp-off ledger, dashboard, audit API, optimistic cache, API tests, perf tuning, dependency audit, CHANGELOG sync | 11 | 15.5 | 136.0 |
| **Stretch** | Local repair, export, compare, LLM explanations, mobile agenda, e2e tests, CI, a11y, Settings screen, visual mockup | 11 | 22.0 | 158.0 (+9.0h done = 167h total) |

**Target scope confirmed (Q11):** 4-day deadline (~1.5–2 days focused effort per brief). Build focus is locked to **Level 1 (demo-able core, 87h)** first to guarantee a complete and working submission, expanding into L2 and L3 as velocity permits.

## 2. Phases

| Phase | Goal | MVP h | Stretch h | Exit criteria |
|---|---|---|---|---|
| 1 Analysis | Requirements, assumptions, frozen model + demo scenarios | 6.0 | 2.0 | Open questions Q1–Q6 answered; schema frozen |
| 2 Setup | Repo, backend/frontend scaffold, Postgres, tokens | 7.0 | 1.0 | `/health` ok; blank themed shell; migrations run |
| 3 DB + backend | Models, migration, schemas, CRUD APIs, seed | 16.5 | 0 | Seeded DB; CRUD works in OpenAPI docs |
| 4 Auth | JWT, roles, demo users | 5.5 | 0 | Login + role-guarded routes |
| 5 Core features | Scheduling engine and roster services | 33.5 | 8.5 | Generate → conflicts → impact → suggestions via API; validator tests green |
| 6 Frontend | Shell, components, screens, grid, views | 35.0 | 6.0 | Whole workflow clickable against mock/real API |
| 7 Integration | Typed client, hooks, wiring | 10.0 | 0 | No mock data left |
| 8 Testing | Unit, property, scenario, API tests, bug fixing | 15.0 | 3.0 | All 5 demo scenarios pass as golden tests |
| 9 Perf + security | Solver timing, indexes, hardening | 4.5 | 1.5 | 36×31 generation within target; checklist passed |
| 10 Deploy + docs | Containers, hosting, README, video, submission | 12.0 | 0 | Live URL verified from a fresh browser |

## 3. Build order (vertical slices)

Work in slices so something runs end to end early, instead of finishing a layer at a time.

1. **Slice 0 — Engine on paper.** Pure-Python engine + tests with in-memory fixtures (T-501–T-506, T-508). No DB, no UI. This is the highest-risk part; de-risk it first.
2. **Slice 1 — Data.** Models, migration, seed script (T-301–T-304, T-309), `POST /rosters` returning a persisted roster.
3. **Slice 2 — See it.** Roster grid with coverage strips and the conflict drawer against the real API (T-607–T-612).
4. **Slice 3 — Change it.** Impact simulator + suggestions (T-511, T-513, T-612). **This slice is the heart of the demo video.**
5. **Slice 4 — Manage it.** CRUD screens, auth, edit/publish (L2).
6. **Slice 5 — Ship it.** Deploy early (even a skeleton), then redeploy each slice; docs and video last.

## 4. Suggested day plan (assuming 4 days; adjust after Q11)

| Day | Focus | Done when |
|---|---|---|
| 1 | Decisions (T-103/104), scaffold, **engine core + validator + tests**, models + seed | Engine validates the seeded month correctly in tests |
| 2 | CP-SAT generator, generate/read/impact APIs, grid + views | Click Generate in the browser and see a roster with conflicts |
| 3 | Suggestions, impact simulator, CRUD screens/auth (as time allows), early deploy | Change scenario works on the live URL |
| 4 | Tests for demo scenarios, bug fixes, README + 8 answers, video, final QA, submission email | Submitted with a verified live link |

## 5. Milestones

| ID | Milestone | Evidence |
|---|---|---|
| M1 | Blueprint approved | This documentation set + answered questions |
| M2 | Engine proven | Validator + generator tests green on seeded data |
| M3 | Roster visible | Grid, strips, conflicts rendered from live API |
| M4 | Change handling demo | Leave on single-resource brand → gap → suggestion → applied |
| M5 | Live deployment | Public URL + seeded data + demo accounts |
| M6 | Submission | Email with URL, repo, LinkedIn, approach note, video |

## 6. Dependencies and critical path
`Decisions → Models/Seed → Engine → Generate API → Grid → Impact/Suggestions → Deploy → Video`.
The engine and seed data are on the critical path; UI polish and CRUD screens are not.

## 7. Risks to the plan
| Risk | Mitigation |
|---|---|
| Scope exceeds time | Scope levels; stop at the last green level |
| CP-SAT learning curve | Engine tests first; validator is solver-independent; greedy fallback (T-507) if needed |
| Free-tier cold starts | Warm the service before recording/submitting |
| Demo data doesn't show scenarios clearly | Design scenarios in `SAMPLE_DATA.md` before seeding |
