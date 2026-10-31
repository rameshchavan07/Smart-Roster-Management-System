# Testing Documentation

Principle: **the scheduling logic is the product**, so it gets the deepest testing. The engine is pure Python, which makes this cheap.

## 1. Strategy (pyramid)

| Layer | Tooling | Focus | Target |
|---|---|---|---|
| Unit — engine | pytest, hypothesis | Calendar resolver, demand/supply builders, validator, explainer, suggestion ranking | Branch coverage ≥ 90% on `scheduler/` |
| Property-based — engine | hypothesis | Invariants over random inputs | See §3 |
| Scenario / golden | pytest | The 5 demo scenarios on the seeded dataset | All pass |
| Service + API | pytest, httpx, test Postgres | Endpoints, RBAC, error format, transactions | Every endpoint has happy + failure path |
| Frontend component | Vitest + Testing Library | Grid cell states, conflict drawer, forms | Stretch |
| End-to-end | Playwright | Generate → conflict → fix → publish | Stretch |
| Manual QA | checklist below | Fresh-browser run on the live URL | Before submission |

## 2. Unit test cases (engine)

| ID | Area | Case | Expected |
|---|---|---|---|
| TC-CAL-01 | Calendar | `ALL_365` on Sunday and on a holiday | Operating |
| TC-CAL-02 | Calendar | `ALL_EXCEPT_HOLIDAYS` on a holiday / on Sunday | Not operating / operating |
| TC-CAL-03 | Calendar | `EXCLUDE_SUNDAY_AND_HOLIDAYS` on Sunday / holiday / Monday | Not / not / operating |
| TC-CAL-04 | Calendar | Brand-specific holiday | Affects only that brand |
| TC-DEM-01 | Demand | Date override beats weekday override beats default | Correct precedence |
| TC-DEM-02 | Demand | Non-operating day with an override | Demand 0 |
| TC-SUP-01 | Supply | Approved leave | Employee unavailable; REQUESTED leave ignored |
| TC-SUP-02 | Supply | Holiday where none of employee's brand-processes operate | Personal holiday off |
| TC-SUP-03 | Supply | Holiday where one assigned process operates | May work → `HOLIDAY_WORK` |
| TC-VAL-01 | Validator | Sole employee on leave, required day | E001 + root cause LEAVE |
| TC-VAL-02 | Validator | Coverage 1 of 2 | E002 |
| TC-VAL-03 | Validator | Weekly off causes the gap | E003 root cause |
| TC-VAL-04 | Validator | 7 consecutive WORK days (limit 6) | E005 |
| TC-VAL-05 | Validator | Week with no weekly off | E006 |
| TC-VAL-06 | Validator | WORK on a leave day | E007 |
| TC-VAL-07 | Validator | Employee counted on 4 processes (limit 3) | E008 WARNING |
| TC-VAL-08 | Validator | Comp-off redeemed with zero balance | E009 |
| TC-VAL-09 | Validator | Preferred off not honoured | W001 only (never blocking) |
| TC-VAL-10 | Validator | Single employee, no backup, operating days | W003 |
| TC-GEN-01 | Generator | Easy month, ample staff | Zero blocking conflicts |
| TC-GEN-02 | Generator | Mandatory vs preference clash | Mandatory wins; preference violation reported |
| TC-GEN-03 | Generator | Infeasible coverage | Returns roster with exact shortfalls; never raises |
| TC-GEN-04 | Generator | Locked cells | Unchanged after generation |
| TC-GEN-05 | Generator | Same seed twice | Identical roster |
| TC-SUG-01 | Suggestions | Candidate that would open another gap | Discarded or shown with "opens N" |
| TC-SUG-02 | Suggestions | Ranking | BACKUP in same pod > floater > other pod |
| TC-SUG-03 | Suggestions | Floater assignment | Applying floater suggestion links employee as BACKUP, satisfying coverage |
| TC-IMP-01 | Impact | Add leave | New conflicts listed; unaffected conflicts unchanged |
| TC-IMP-02 | Impact | Dry run | Nothing persisted |
| TC-IMP-03 | Impact | Multi-brand schedule change | Schedule change for multi-brand employee flags concurrent gaps across all assigned brands |

## 3. Property-based invariants
1. Demand is 0 on every non-operating day.
2. For any generated roster: fixed cells (leave, comp-off, locked) are unchanged.
3. Every generated roster satisfies H2/H3 (weekly offs, consecutive days) for every employee.
4. The shortfalls reported by the solver equal the E001/E002 set computed by the **independent** validator.
5. Injecting any single fault (remove a weekly off, add WORK to a leave day, drop a covering employee) produces the matching conflict code.
6. Validation is idempotent and independent of employee ordering.

## 4. Scenario tests (golden)
One test per scenario S1–S5 in `SAMPLE_DATA.md`, asserting exact conflict codes, dates, root causes, and top suggestion. Run against the seeded December 2026 dataset.

## 5. API tests
| Area | Cases |
|---|---|
| Auth | Bad password → 401; expired token → 401; refresh rotation |
| RBAC | Pod lead cannot edit another pod; employee cannot generate; only ops manager publishes |
| Validation | `end_date < start_date` → 422 with field detail; duplicate brand → 409 |
| Roster | Generate twice for same month creates version 2; publish with BLOCKING → 422 `ROSTER_BLOCKED`; edit on published roster creates a new draft |
| Errors | Every error uses the standard envelope with `request_id` |
| Concurrency | Two edits to the same cell → second gets 409 |

## 6. Performance validation
| Test | Pass criterion |
|---|---|
| Generate 36 employees × 31 days | ≤ 15 s |
| Stress dataset (~110 employees) | Completes within solver limit; status reported honestly (`FEASIBLE`/`FALLBACK`) |
| Impact dry run | ≤ 500 ms |
| Grid endpoint (company view) | ≤ 1 s |

## 7. Manual QA checklist (live URL, fresh browser)
- [ ] Login with each demo role
- [ ] Generate December 2026; summary matches expected conflict counts
- [ ] Switch all five views; day view shows who is working
- [ ] Scenario S1 end to end (add leave → gaps → apply suggestion → gaps cleared)
- [ ] Scenario S5: publish blocked; acknowledge with reason works
- [ ] Add a new brand + process + assignment from the UI; regenerate; it appears
- [ ] Empty, loading and error states visible (kill API once)
- [ ] Tablet and mobile widths usable
- [ ] Keyboard-only: move through the grid, open popover, set a status

## 8. Bug handling
Defects are logged as tracker tasks (`T-807` buffer). A fix must come with a regression test whenever it touches the engine.

## 9. Definition of done (any task)
Code merged, lint/type-check clean, tests added or updated, docs touched if behaviour changed, no previously passing test broken.
