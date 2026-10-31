# Scheduling Engine Specification

The heart of the project. Everything here is pure Python with no I/O.

## 1. Core concepts

```
Demand[bp, d]   = required headcount for brand-process bp on date d   (0 if not an operating day)
Supply[e, d]    = AVAILABLE | LEAVE | HOLIDAY_OFF | COMPOFF | LOCKED(status)
Roster[e, d]    = WORK | WEEKLY_OFF | HOLIDAY_OFF | LEAVE | COMP_OFF | HOLIDAY_WORK
Coverage[bp, d] = number of employees with Roster = WORK/HOLIDAY_WORK and an assignment to bp
Shortfall[bp, d]= max(0, Demand − Coverage)
```

The brand's **operating calendar** fixes `Demand`; the employee's **working schedule** is `Roster`. They are computed separately and compared by the validator.

## 2. Calendar resolver

| Calendar type | Operating on date d if… |
|---|---|
| `ALL_365` | always |
| `ALL_EXCEPT_HOLIDAYS` | d is not a public holiday applicable to the brand |
| `EXCLUDE_SUNDAY_AND_HOLIDAYS` | d is not Sunday and not a public holiday |

Holiday applicability: global holidays apply to all; brand-scoped holidays only to that brand.

## 3. Demand builder
Precedence (most specific wins): **date override → weekday override → default minimum**, applied only on operating days. Non-operating days → demand 0.

## 4. Employee availability
- **LEAVE**: approved leave (hard, fixed).
- **COMP_OFF**: approved comp-off redemption (hard, fixed).
- **HOLIDAY_OFF**: employee's *personal* holiday = a public holiday on which **none** of their assigned brand-processes operate. If any assigned brand-process operates, the employee may be rostered (becoming `HOLIDAY_WORK`, which earns a comp-off credit).
- **LOCKED**: manager-locked cells are fixed.

## 5. Constraints

### Mandatory (hard)
| ID | Constraint |
|---|---|
| H1 | Fixed cells (leave, comp-off, locked, personal holiday-off) are never changed |
| H2 | Each employee gets ≥ `weekly_off_count` weekly offs per full Mon–Sun week (pro-rated at month edges: partial weeks with $\ge 4$ days in the month receive 1 weekly off; $< 4$ days receive 0) |
| H3 | No more than `max_consecutive_days` consecutive WORK days (carry-in from previous month's tail when available) |
| H4 | Weekly offs only on days an employee is not otherwise off (no double-counting a leave as a weekly off; a public holiday on a weekly off defaults to `HOLIDAY_OFF` and grants a comp-off credit or alternate off per A-10) |
| H5 | Employee fixed weekly-off weekdays (when configured as `FIXED_MANDATORY`) are honoured |

### Coverage — "hard with slack"
`Coverage[bp,d] + slack[bp,d] ≥ Demand[bp,d]`, with slack penalised very heavily. This always yields a roster and quantifies exactly what couldn't be covered, rather than failing with "infeasible". Any `slack > 0` becomes a **BLOCKING** conflict.

### Preferences (soft)
| ID | Preference | Weight (default) |
|---|---|---|
| P1 | Preferred weekly-off weekday / date | 5 |
| P2 | Fairness: spread weekend offs evenly (minimise max−min Sat/Sun offs per employee) | 3 |
| P3 | Weekly offs adjacent to leaves/holidays clustered rather than isolated | 1 |
| P4 | Prefer assigning PRIMARY over BACKUP to cover a gap | 4 |
| P5 | Minimise changes vs previous roster/version (stability) | 6 |
| P6 | Avoid employee covering > `max_concurrent_processes` brand-processes on one day | 8 |

**Rule:** objective weight of a coverage shortfall ≫ sum of all preference weights, so a required coverage day always beats a preferred-off day (brief §3D).

## 6. Solver model (CP-SAT)
- Boolean `work[e,d]` for each non-fixed cell.
- Linear sums per week for H2; sliding window of length `max_consecutive+1` for H3.
- For each `(bp,d)` with demand > 0: `sum(work[e,d] for e in assigned(bp)) + slack = demand` bound as `≥`.
- Objective: `Σ BIG·slack + Σ w_p·penalty_p`.
- Time limit `SOLVER_TIME_LIMIT_S` (default 20), fixed random seed, reports `OPTIMAL | FEASIBLE`.
- Fallback: greedy generator (assign weekly offs to the day with most slack in each employee's brand-processes, respect constraints, then repair), flagged `solver_status = FALLBACK`.

## 7. Validator (independent of the solver)
Pure function `validate(roster, demand, supply, rules) → ValidationResult`. Runs on generated, edited and imported rosters.

### Conflict catalogue
| Code | Severity | Meaning |
|---|---|---|
| E001 `NO_COVERAGE` | BLOCKING | Required day, zero available employees assigned (primary conflict code) |
| E002 `UNDER_STAFFED` | BLOCKING | Coverage < demand but > 0 (primary conflict code) |
| E003 `WEEKLY_OFF_BREAKS_COVERAGE` | BLOCKING | Root-cause tag on E001/E002 indicating the gap is caused by a weekly off |
| E004 `LEAVE_BREAKS_COVERAGE` | BLOCKING | Root-cause tag on E001/E002 indicating the gap is caused by leave / comp-off |
| E005 `MAX_CONSECUTIVE_EXCEEDED` | BLOCKING | Run of WORK days > limit |
| E006 `WEEKLY_OFF_MISSING` | BLOCKING | Fewer weekly offs than entitled in a week |
| E007 `INVALID_CELL` | BLOCKING | WORK on a leave / comp-off day, or WEEKLY_OFF on non-eligible day |
| E008 `OVERLOAD` | WARNING | Employee counted on more than `max_concurrent_processes` that day |
| E009 `COMPOFF_BALANCE` | BLOCKING | Redeemed comp-off exceeds balance |
| W001 `PREFERENCE_VIOLATED` | WARNING | Preferred off not honoured (reason recorded) |
| W002 `UNFAIR_DISTRIBUTION` | INFO | Weekend-off imbalance beyond threshold |
| W003 `SINGLE_POINT_OF_FAILURE` | INFO/WARNING | Brand-process on operating days with exactly one eligible employee and no backup |
| W004 `STALE_ROSTER` | WARNING | Underlying inputs changed after generation |

Each conflict stores: code, severity, brand-process, date(s), employee(s), root-cause tags (`["WEEKLY_OFF"]`, `["LEAVE"]`, etc.), human message, and `suggestions[]`.

## 8. Explainer
Template-based plain English from structured causes, e.g.:
> *"Brand **Aurora** — Customer Support has no coverage on **14 Dec (Mon)**. Its only assigned employee **Riya Shah** is on approved leave (13–15 Dec). Backups available that day: **Kabir (floater, working)**, **Anaya (Pod B, working)**."*

Optional later: pass the structured conflict to an LLM for rephrasing; deterministic text remains the source of truth.

## 9. Suggestion engine (backup recommendations)
For each BLOCKING gap, candidates are generated and ranked:
1. **Backup/floater** working that day (not over capacity) — score by: assigned as BACKUP to bp > same pod > floater > other pod; lower recent workload first. Applying a floater links them as an active `BACKUP` assignment to `bp` for the required duration.
2. **Weekly-off swap**: move another eligible employee's weekly off off this date (keeps H2).
3. **Comp-off/leave shift** (propose; needs manager approval).
4. **Second-order check**: simulate each candidate through the validator and discard ones that open new BLOCKING gaps elsewhere. Show net effect ("fixes 1, opens 0").

## 10. Change handling

| Case | Behaviour |
|---|---|
| Single-resource brand, employee unavailable on required day | E001 (with LEAVE root cause / E004 tag); suggestions list backups; if none → remains flagged and blocks publish |
| 3-person brand, one unavailable | Re-evaluate remaining two against demand per day; report "covered" or the exact days that fail |
| New brand requirement (e.g. min 2 on Mondays) | Rebuild demand, re-validate whole month, list new gaps |
| Locked edit | Solver treats as fixed; validator still reports conflicts it causes |

**Local repair:** re-solve with all cells outside the impacted window (affected employees ± dates) locked; compare with previous version; show diff.

## 11. Determinism and testing
- Fixed seed; stable ordering of employees/brands.
- Property tests: *every generated roster passes the validator’s mandatory checks except explicitly reported shortfalls*; *validator detects each injected fault*; *demand is 0 on non-operating days*.
- Golden-file tests on the seeded dataset for each demo scenario.

## 12. Answers this design supports (README §8)
- **Q3 single vs multi-resource brands:** the same `Assignment` model; single-resource brands are those where all brand-processes map to one employee, surfaced via W003 and the suggestion engine.
- **Q4 sole employee unavailable:** see §10 row 1.
- **Q5 conflicting requirements:** coverage slack + penalties + root-cause tags.
- **Q6 automation vs human control:** engine auto-generates, validates and suggests; **manager decides** publish, acknowledging BLOCKING items, approving comp-offs/leaves, and applying suggestions.
