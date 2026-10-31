# Sample Dataset Specification

> Status: **Frozen v1.0 (Locked 2026-11-01)** · Aligned with confirmed decisions Q1–Q6 & Q11 · Source of truth for seed script (`python -m app.seed`) and golden scenario tests (`T-805`).

Target month for demos: **December 2026** (31 days, starts Tuesday, ends Thursday).

---

## 1. Headcount Arithmetic & Entity Topology (Brief §4)

| Entity | Count | Allocation & Mapping Details |
|---|---|---|
| **Pods** | 6 | Pods **A, B, C, D, E, F**, each led by one Pod Lead (`EMP-001` through `EMP-006`) |
| **Employees** | 36 | 6 Pod Leads, 26 Primary Brand Staff, 4 Dedicated Floaters (`EMP-033`–`EMP-036`) |
| **Brands** | 25 | 20 Single-resource brands (80%), 5 Multi-resource brands (20%) |
| **Staffed Brand Slots** | 32 | Exactly matches the 32 non-floater employees (20 single + 12 multi = 32) |
| **Floaters** | 4 | Dedicated cross-brand backups (`is_floater = true`); hold no initial primary brand |
| **Processes** | 4 | `CS` (Customer Support), `ACC` (Abandoned Cart), `RET` (Retention), `NDR` (Non-Delivery Reports) |

### 1.1 Pod and Employee Roster
- **Pod A (Support Specialists):**
  - Lead: `EMP-001` (Aanya Sharma)
  - Staff: `EMP-007` (Riya Shah — Aurora Lead), `EMP-008` (Karan Mehta — Solace), `EMP-009` (Tanvi Rao), `EMP-010` (Arjun Das)
- **Pod B (D2C Accelerators):**
  - Lead: `EMP-002` (Bhavin Patel)
  - Staff: `EMP-011` to `EMP-014` (Single-resource staff), `EMP-015` (Aarav Patel — Nova), `EMP-016` (Pooja Sharma — Nova), `EMP-017` (Vikram Singh — Nova)
- **Pod C (Operations & Retention):**
  - Lead: `EMP-003` (Chetan Kumar)
  - Staff: `EMP-018` to `EMP-020` (Single-resource staff), `EMP-021` (Neha Gupta — Pulse), `EMP-022` (Rahul Verma — Pulse)
- **Pod D (Logistics & NDR):**
  - Lead: `EMP-004` (Divya Nair)
  - Staff: `EMP-023` (Aditi Rao — Orion), `EMP-024` (Dev Malhotra — Orion), `EMP-025` to `EMP-027` (Single-resource staff)
- **Pod E (Growth & Engagement):**
  - Lead: `EMP-005` (Eshaan Joshi)
  - Staff: `EMP-028` (Zoya Khan — Zenith), `EMP-029` (Kunal Kapoor — Zenith), `EMP-030` (Meera Sen — Zenith), `EMP-031` (Single-resource)
- **Pod F (Flex & Peak Operations):**
  - Lead: `EMP-006` (Farhan Ali)
  - Staff: `EMP-032` (Single-resource staff)
  - Floaters: `EMP-033` (Kabir Nair), `EMP-034` (Ananya Verma), `EMP-035` (Rohan Mehra), `EMP-036` (Priya Pillai)

---

## 2. Brands and Operating Calendars

### 2.1 Single-Resource Brands (`BRD-01` to `BRD-20` — 80%)
Each single-resource brand has all its processes managed by 1 dedicated primary employee.
- **`BRD-01` Aurora (Pod A):** Primary `EMP-007` (Riya Shah). Processes: `CS` (`ALL_365`), `ACC` (`ALL_EXCEPT_HOLIDAYS`), `NDR` (`EXCLUDE_SUNDAY_AND_HOLIDAYS`). *(Powers Scenario S1)*
- **`BRD-02` Solace (Pod A):** Primary `EMP-008` (Karan Mehta). Processes: `CS` (`ALL_365`). *(Powers Scenario S4)*
- **`BRD-03` Lumina (Pod A):** Primary `EMP-009`. `CS` (`ALL_EXCEPT_HOLIDAYS`), `ACC` (`EXCLUDE_SUNDAY_AND_HOLIDAYS`).
- **`BRD-04` Zenith Essentials (Pod B):** Primary `EMP-010`. `CS` (`ALL_365`).
- **`BRD-05` Kredo (Pod B):** Primary `EMP-011`. `CS` (`ALL_EXCEPT_HOLIDAYS`), `RET` (`ALL_EXCEPT_HOLIDAYS`). (Has regional holiday Dec 10).
- **`BRD-06` to `BRD-20`:** Distributed across Pods B–F; 7 brands on `ALL_365`, 5 on `ALL_EXCEPT_HOLIDAYS`, 3 on `EXCLUDE_SUNDAY_AND_HOLIDAYS`.

### 2.2 Multi-Resource Brands (`BRD-21` to `BRD-25` — 20%)
- **`BRD-21` Nova (Pod B) — 3 Employees:**
  - `EMP-015` (Aarav Patel): Primary `CS` (`ALL_365`), Secondary `ACC`.
  - `EMP-016` (Pooja Sharma): Primary `ACC` (`ALL_EXCEPT_HOLIDAYS`).
  - `EMP-017` (Vikram Singh): Primary `NDR` (`EXCLUDE_SUNDAY_AND_HOLIDAYS`).
  - *(Powers Scenario S2)*
- **`BRD-22` Zenith Brand (Pod E) — 3 Employees:**
  - `EMP-028` (Zoya Khan): Primary `CS` (`ALL_365`).
  - `EMP-029` (Kunal Kapoor): Primary `ACC` (`ALL_EXCEPT_HOLIDAYS`).
  - `EMP-030` (Meera Sen): Primary `RET` (`ALL_EXCEPT_HOLIDAYS`).
- **`BRD-23` Pulse (Pod C) — 2 Employees:**
  - `EMP-021` (Neha Gupta): Primary `CS` (`ALL_365`).
  - `EMP-022` (Rahul Verma): Primary `CS` (`ALL_365`).
  - *(Shared process with minimum 2 coverage; powers Scenario S3)*
- **`BRD-24` Orion (Pod D) — 2 Employees:**
  - `EMP-023` (Aditi Rao): Primary `CS` (`ALL_EXCEPT_HOLIDAYS`), `RET` (`ALL_EXCEPT_HOLIDAYS`).
  - `EMP-024` (Dev Malhotra): Primary `CS` (`ALL_EXCEPT_HOLIDAYS`), `RET` (`ALL_EXCEPT_HOLIDAYS`).
  - *(Over-constrained Friday mandatory offs; powers Scenario S5)*
- **`BRD-25` Apex (Pod F) — 2 Employees:**
  - `EMP-006` (Pod Lead Farhan Ali) & `EMP-032` (Staff): Primary `CS` & `NDR`.

---

## 3. Coverage Rules & Overrides

1. **Default Rule:** Minimum 1 employee per active operating day for every brand-process.
2. **Weekday Rule Overrides:**
   - `BRD-23` (Pulse) — `CS`: Minimum **2 staff on Mondays** (`2026-12-07`, `2026-12-14`, `2026-12-21`, `2026-12-28`).
   - `BRD-21` (Nova) — `ACC`: Minimum **2 staff on Fridays** (`2026-12-04`, `2026-12-11`, `2026-12-18`).
3. **Specific Date Override:**
   - `BRD-01` (Aurora) — `CS`: Minimum **2 staff on 2026-12-18** (Year-end campaign surge).

---

## 4. Employee Availability Profiles

- **Weekly-off Entitlements:**
  - 34 employees: 1 weekly off per full Mon–Sun week.
  - 2 employees (`EMP-012`, `EMP-030`): 2 weekly offs per week.
- **Weekly-off Policy Rules:**
  - `FIXED_MANDATORY`: `EMP-023` (Friday), `EMP-024` (Friday) — both mandatory, non-negotiable.
  - `FIXED_PREFERRED`: `EMP-007` (Sunday), `EMP-015` (Wednesday), `EMP-022` (Monday).
  - `ROTATING`: `EMP-008` (Karan Mehta), `EMP-028` (Zoya Khan).
  - `ANY`: Remaining 29 employees.
- **Max Consecutive Days:** 6 working days (default).

---

## 5. Holidays & Pre-seeded Leaves (December 2026)

- **Public Holidays:**
  - **Global:** `2026-12-25` (Christmas, Friday) — all brands with `ALL_EXCEPT_HOLIDAYS` or `EXCLUDE_SUNDAY_AND_HOLIDAYS` close. `ALL_365` brands remain active.
  - **Brand-specific:** `2026-12-10` (Regional Event, Thursday) — applies only to `BRD-05` (Kredo).
- **Pre-seeded Approved Leaves:**
  - `EMP-016` (Pooja Sharma, Nova): `2026-12-08` to `2026-12-10` (Tue–Thu).
  - `EMP-018`: `2026-12-03` to `2026-12-04` (Thu–Fri).
  - `EMP-026`: `2026-12-16` to `2026-12-17` (Wed–Thu).
  - `EMP-029`: `2026-12-21` to `2026-12-23` (Mon–Wed).
  - **Demo Clean State:** `EMP-007` (Riya Shah, Aurora) has **zero** pre-seeded leave so the evaluator can execute Scenario S1 live.

---

## 6. Golden Demo Scenarios (Tested in T-805)

### Scenario S1: Single-Resource 365-Day Brand, Sole Employee Unavailable
- **Setup:** `BRD-01` (Aurora). Sole employee `EMP-007` (Riya Shah). Add approved leave `2026-12-13` to `2026-12-15` (Sun–Tue).
- **Calendar Logic:**
  - `2026-12-13` (Sun): CS operates (`ALL_365`), ACC operates (`ALL_EXCEPT_HOLIDAYS`), NDR is closed (`EXCLUDE_SUNDAY_AND_HOLIDAYS`).
  - `2026-12-14` (Mon) & `2026-12-15` (Tue): CS, ACC, NDR all operate.
- **Expected Validator Conflicts:**
  - `2026-12-13`: `E001 NO_COVERAGE` on CS, `E001 NO_COVERAGE` on ACC (NDR demand is 0, no conflict).
  - `2026-12-14`: `E001 NO_COVERAGE` on CS, ACC, and NDR.
  - `2026-12-15`: `E001 NO_COVERAGE` on CS, ACC, and NDR.
  - Root causes: `["LEAVE"]`.
- **Suggestion Engine:**
  - Top suggestion: Floater `EMP-033` (Kabir Nair) available across all 3 dates.
  - Net effect: "Fixes 8 gaps, opens 0".
  - Application: Links Kabir Nair as `BACKUP` assignment to Aurora for those dates, resolving all `E001` conflicts.

### Scenario S2: Three-Person Brand, One Unavailable (Coverage Evaluation)
- **Setup:** `BRD-21` (Nova). 3 employees: `EMP-015` (Aarav - CS), `EMP-016` (Pooja - ACC), `EMP-017` (Vikram - NDR). Pooja is on leave `2026-12-08` to `2026-12-10`.
- **Expected Validator Outcome:**
  - Evaluates remaining 2 employees per day against demand.
  - Aarav has secondary capability on ACC: on Dec 8 & Dec 10, Aarav covers ACC alongside CS (green, covered).
  - On Dec 9, Aarav has scheduled weekly off: ACC is left under-staffed (`E001` on ACC, root cause `["WEEKLY_OFF"]`).
  - Suggestion: Swap Aarav's weekly off to Dec 11 or allocate floater `EMP-034`.

### Scenario S3: Shared Process with Minimum 2 Staff
- **Setup:** `BRD-23` (Pulse). Process CS requires min 2 staff on Mondays. Assigned: `EMP-021` (Neha Gupta) and `EMP-022` (Rahul Verma).
- **Trigger:** Rahul Verma's weekly off falls on Monday `2026-12-14`.
- **Expected Validator Outcome:**
  - `E002 UNDER_STAFFED` on `BRD-23` CS for `2026-12-14` (Headcount: 1, Required: 2, root cause `["WEEKLY_OFF"]`).
- **Suggestion Engine:**
  - Proposes swapping Rahul's weekly off to Tuesday `2026-12-15`.
  - Applying swap clears `E002`.

### Scenario S4: Holiday Work & Comp-Off Ledger
- **Setup:** `BRD-02` (Solace, `ALL_365`). Sole employee `EMP-008` (Karan Mehta) works Friday `2026-12-25` (Christmas).
- **System Outcome:**
  - Roster entry recorded as `HOLIDAY_WORK`.
  - Ledger creates entry: `+1 comp-off credit` in `comp_off_ledger`.
  - Karan redeems comp-off on `2026-12-29` (Tue) $\to$ entry status becomes `COMP_OFF`.
  - Validation ensures redemption is allowed (balance $\ge 1$) and decrements balance to 0.

### Scenario S5: Over-Constrained Month & Publish Gating
- **Setup:** `BRD-24` (Orion). Two assigned employees `EMP-023` (Aditi) and `EMP-024` (Dev) both have `FIXED_MANDATORY` weekly offs configured on Friday.
- **Expected Solver & Validator Outcome:**
  - On Fridays (`Dec 4, 11, 18`), mandatory weekly offs are honored (H5 constraint).
  - Solver falls back to coverage slack, reporting `E001 NO_COVERAGE` on Orion CS and RET.
  - Ops Manager clicks **Publish** $\to$ API responds with HTTP 422 `ROSTER_BLOCKED` ("Blocking conflicts remain").
  - Ops Manager must either acknowledge the conflicts with a logged reason or adjust a weekly-off rule before publish succeeds.

---

## 7. Stress Dataset Topology (Performance Proof T-901)
Generated with `python -m app.seed --scale 3`:
- **Employees:** 108
- **Brands:** 75 (60 single-resource, 15 multi-resource)
- **Pods:** 18
- Used to benchmark CP-SAT solution time ($\le 20$ s) and verify virtualised grid performance.

---

## 8. Seeded Demo Accounts (for Evaluators)

| Role | Email | Scope |
|---|---|---|
| `OPS_MANAGER` | `ops@example.test` | Full company-wide management, generation, and publishing |
| `POD_LEAD` | `lead.a@example.test` | Pod A scoped management; reviews own pod roster |
| `EMPLOYEE` | `emp@example.test` | Linked to `EMP-007` (Riya Shah); read-only personal schedule & ledger |

*Passwords are securely seeded at deployment from the `DEMO_PASSWORD` environment variable.*
