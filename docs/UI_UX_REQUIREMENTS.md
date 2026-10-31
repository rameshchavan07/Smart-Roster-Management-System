# UI/UX Requirements and Screen Specifications

Visual tokens live in `DESIGN_SYSTEM.md`. This file defines **what each screen contains and how it behaves.** Wireframes are structural concepts, not final visuals; a high-fidelity clickable HTML mockup is the proposed next step before frontend build.

## 1. Global requirements
- **Desktop-first** (1280+), fully usable at tablet (768) and mobile (375) with adapted layouts.
- States for every data view: **loading** (skeleton), **empty** (one-line explanation + primary action), **error** (message + retry + request id), **success** (toast).
- Destructive actions need confirmation naming the object; deactivation preferred over deletion.
- Keyboard access for the grid, menus, dialogs; visible focus ring; no colour-only meaning (letters + icons accompany colour).
- Language: plain operational English; conflict messages name brand, process, date and person.

## 2. Information architecture
```
Login
└─ App shell (sidebar + topbar)
   ├─ Dashboard
   ├─ Roster  ── Views: Company | Pod | Brand | Process | Employee
   │            ├─ Day view (who is working on a date)
   │            ├─ Conflicts drawer / Impact simulator
   │            └─ Versions / Compare
   ├─ Conflicts (full list)
   ├─ Leaves & Comp-offs
   ├─ Team: Employees · Pods
   ├─ Brands & Processes: Brands · Processes · Assignments
   ├─ Rules & Holidays: Coverage rules · Holiday calendar
   ├─ Reports & Export
   └─ Settings (weights, defaults, users, audit log)
```

## 3. Screens

### S1 — Login
Centered 400px form on `--bg`; wordmark, email, password, primary button; error inline. Footer shows demo accounts (collapsed "Demo access" disclosure) for evaluators.

### S2 — Dashboard (month overview)
```
┌ Dec 2026 ▾   Roster v2 · DRAFT · Generated 10:42          [Generate] [Open roster] ┐
├────────────────────────────────────────────────────────────────────────────────────┤
│ Blocking 2 │ Warnings 5 │ Coverage 99.1% │ Single-point brands 14 │ Pending leave 3 │
├──────────────────────────────────────┬─────────────────────────────────────────────┤
│ Needs attention (list)               │ Coverage heatmap (brand-process × days)     │
│ ● Aurora CS uncovered 14 Dec    ▸    │ ▓▓▓▓░▓▓▓▓▓▓▓▓▓▓░▓▓▓ …                      │
│ ● Nova ACC understaffed 9 Dec   ▸    │                                             │
│ ▲ Weekend-off imbalance (3 emp) ▸    ├─────────────────────────────────────────────┤
│                                      │ Workload per employee (days worked)         │
└──────────────────────────────────────┴─────────────────────────────────────────────┘
```
Behaviour: KPI items link to the filtered conflicts. If no roster exists for the month: empty state with **Generate roster** as the only primary action and a checklist of prerequisites (holidays loaded, leaves entered, assignments complete).

### S3 — Roster workspace (main screen)
```
┌ Topbar: ◂ Dec 2026 ▸ │ View: [Company|Pod|Brand|Process|Employee] ▾ filter │ Search ┐
├ Status: DRAFT v2 · 2 blocking ▸ │ [Validate] [Impact…] [Lock] [Export] [Publish] ┤
├──────────────────────┬───────────────────────────────────────────────────────────┤
│ Employee      Pod  Ld│ T W T F S S M T W T F S S …   (1 … 31)                  │
│ ─ coverage strips ───│ ▇▇▇▇▇▇▓▇▇▇▇▇▇▇▇  Aurora · CS    ← 4px strips per brand-proc│
│ Riya Shah     A  22  │ W W W L L L WO W W …                                      │
│ Kabir Nair    F  23  │ W WO W W W W W W …                                        │
└──────────────────────┴───────────────────────────────────────────────────────────┘
                                                        ┌ Right drawer (on select) ┐
                                                        │ Aurora · CS · 14 Dec     │
                                                        │ Needs 1 · Has 0          │
                                                        │ Cause: Riya on leave     │
                                                        │ Suggestions: …           │
                                                        └──────────────────────────┘
```
Behaviour:
- **View switcher** changes grouping/filtering: *Company* (all, grouped by pod), *Pod* (pod lead header + members), *Brand* (employees grouped by process, with required-vs-actual rows), *Process* (all brands for CS etc.), *Employee* (single person month calendar with legend and leave/comp-off ledger).
- Clicking a **day header** opens **Day view**: list of everyone working, grouped by brand-process, with coverage state.
- Clicking a **cell** opens a popover: status picker, note, lock toggle, and an **inline impact line** ("Opens 1 gap: Aurora CS 14 Dec") updating as the choice changes before Apply.
- Sticky headers/columns; virtualised rendering; keyboard shortcuts documented in a `?` sheet.
- Stale roster banner when inputs changed since generation.

### S4 — Conflicts
Full-width table: severity · code · brand/process · date(s) · employee · cause · status · actions. Filters by severity/brand/date. Row opens right drawer with explanation, ranked suggestions (each showing "fixes N / opens M"), **Apply**, **Acknowledge with reason**.

### S5 — Impact simulator (change handling)
Launched from Leaves ("Preview impact"), the roster toolbar, or a cell. Left: form (change type: add leave / mark unavailable / change min coverage / remove assignment). Right: **Before → After** summary with new, resolved and unchanged conflicts; multi-person brands show a small matrix "remaining employees vs demand" per day. Buttons: **Apply change**, **Apply + repair**, **Discard**.

### S6 — Leaves & Comp-offs
Table (employee, dates, type, status, impact badge) with segmented filter by status; side panel to create/edit; approve/reject inline with impact summary shown before confirming. Comp-off tab: balances per employee, earned/redeemed history.

### S7 — Team: Employees & Pods
Employees: dense table with search, filters (pod, active, floater), inline edit drawer containing details, assignments list, weekly-off rule, preferences, comp-off balance. Pods: list with lead selector and member counts; drag-free (use multiselect) to keep it simple and accessible.

### S8 — Brands & Processes
Master–detail layout: brand list left; right shows brand-processes (calendar type, min coverage, assigned employees as avatars/chips, **single-point-of-failure** flag). "Add process to brand" opens a modal with calendar type and default minimum. Assignments editable here (PRIMARY/BACKUP, dates).

### S9 — Rules & Holidays
Coverage rules: per brand-process table of weekday/date overrides with explanatory preview ("Min 2 on Mondays"). Holiday calendar: month-grid with list; global vs brand-specific toggle.

### S10 — Reports & Export
Version list and **Compare** (side-by-side metrics: blocking count, coverage %, fairness spread, changes vs base). Export CSV/XLSX buttons with the chosen view.

### S11 — Settings
Defaults (weekly offs, max consecutive days, solver time limit), objective weights with sliders and plain-language descriptions, user management, **Audit log** table.

### S12 — My Roster (Employee role)
Single-month calendar of own statuses with legend, upcoming holidays, comp-off balance.

## 4. Responsive behaviour
| Breakpoint | Behaviour |
|---|---|
| ≥ 1280 | Full sidebar, grid with side drawer |
| 768–1279 | Sidebar collapses to icon rail; drawer overlays |
| < 768 | Bottom tab bar (Dashboard, Roster, Conflicts, Leaves, More); **roster becomes an agenda**: pick employee/brand + week strip, vertical day list; tables become stacked rows; drawers become full-screen sheets |

## 5. Microcopy examples
- Empty roster: *"No roster for December yet. Generate one from your current team, rules and leaves."*
- Blocking publish: *"2 blocking issues remain. Resolve them or acknowledge each with a reason."*
- Generation: *"Optimising… 8 s of 20 s · best roster so far covers 98.7% of required days."*

## 6. Accessibility
Contrast AA; focus order logical; grid uses `role="grid"` with roving tabindex; dialogs trap focus; status never conveyed by colour alone; touch targets ≥ 40px on mobile.

## 7. UX acceptance checks
1. Manager sees where the roster is broken within 5 seconds of opening the workspace.
2. Any conflict explains itself without leaving the drawer.
3. A leave change shows impact before saving.
4. Every list/table has loading, empty and error states.
