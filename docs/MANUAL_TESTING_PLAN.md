# Smart Roster Management System — End-to-End Manual Testing Plan

> This document is your step-by-step execution guide to manually verify **every single feature, role, button, and workflow** in the system against your local PostgreSQL database (`rosterops`) and the web UI (`http://localhost:5173`).

---

## Prerequisites & Launch Checklist

1. **PostgreSQL 18** running on port `5432` with database `rosterops`.
2. **Terminal 1 — Backend API**:
   ```powershell
   cd "d:\Smart Roster Management System\backend"
   .\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
   ```
   *Health Check*: Open `http://localhost:8000/health` $\to$ Returns `{"status":"ok"}`.
3. **Terminal 2 — Frontend UI**:
   ```powershell
   cd "d:\Smart Roster Management System\frontend"
   npm run dev
   ```
   *Web App*: Open `http://localhost:5173` in Chrome/Edge.

---

## 1. Authentication & Role-Based Access Control (RBAC)

### Test 1.1: Ops Manager Full-Access Login
- **Action**: Go to `http://localhost:5173/login`, enter `ops@example.test` / `TestPassword123!`.
- **Expected Result**:
  - Redirects to `/roster`.
  - Top navigation bar shows **all sections**: `Roster`, `Compare`, `Comp-Offs`, `Master Data`, `Rules`, `Audit Logs`.
  - Management buttons are visible: **"Generate Roster"**, **"Publish Roster"**, **"Accrue Comp-Offs"**, **"Export"**.

### Test 1.2: Pod Lead Scoped Login
- **Action**: Log out. Log in as `lead.a@example.test` / `TestPassword123!`.
- **Expected Result**:
  - Top navigation shows `Roster`, `Comp-Offs`, `Audit Logs`.
  - Notice that company-wide administrative controls (like global Master Data modifications and Final Publishing) are restricted or read-only.
  - The Pod Lead can view and execute local repairs for their pod.

### Test 1.3: Regular Employee Self-Service Login
- **Action**: Log out. Log in as `emp@example.test` / `TestPassword123!`.
- **Expected Result**:
  - Linked to **EMP-007 (Riya Shah)**.
  - Management controls are completely hidden: **No Generate button, no Publish button, no cell edit tools**.
  - The employee sees their **personal monthly calendar** and their **comp-off credit balance**.

---

## 2. Roster Generation (CP-SAT Solver)

*Perform as `ops@example.test`.*

### Test 2.1: Generate Draft Roster for December 2026
- **Action**:
  1. Navigate to **Roster** (`/roster`).
  2. Select Month: **`2026-12`**.
  3. Click **"Generate Roster"**.
- **Expected UI Behavior**:
  - A modal opens showing generation options (Seed: `42`, Time Limit: `20s`).
  - Click **"Run Generator"**.
  - Loading skeleton displays while solving.
  - Within 0.5–1.5 seconds, the page renders **Draft Version 1**.
  - Summary KPI Header displays:
    - **Status badge**: `DRAFT` (v1)
    - **Coverage %**: Expected $> 90\%$
    - **Blocking Conflicts count**: (Flags mandatory constraints such as Orion Friday offs)
    - **Warnings count**: (Flags Single Point of Failure or weekend spreads)
- **Database Verification in pgAdmin**:
  ```sql
  SELECT id, version, status, solver_status, generation_params 
  FROM roster_periods WHERE month = '2026-12-01';
  ```
  *(1 row returned with `status = 'DRAFT'` and `solver_status = 'OPTIMAL'`)*.

---

## 3. Interactive Grid Navigation & Accessibility

### Test 3.1: View Modes & Filtering
- **Action**:
  - Toggle between **"By Employee"** view and **"By Brand"** view.
  - Use the Pod filter dropdown to filter by **Pod A**, **Pod B**, etc.
  - Use the Search box to search for *"Riya"* or *"Aurora"*.
- **Expected Result**:
  - Table instantly filters to show only the matching rows.
  - "By Brand" groups rows under brand process headers (e.g. `Aurora - Customer Support`).
  - "By Employee" lists each employee with their role and pod badge.

### Test 3.2: Grid Keyboard Navigation (Roving Tabindex)
- **Action**:
  - Click on any shift cell in the grid.
  - Press `Right Arrow`, `Left Arrow`, `Down Arrow`, `Up Arrow`.
- **Expected Result**:
  - Blue focus border smoothly moves across the grid (`role="grid"` compliance).
  - Status letters are clearly legible:
    - **`W`** (Work)
    - **`WO`** (Weekly Off)
    - **`HW`** (Holiday Work — check Dec 25 Christmas for Solace)
    - **`L`** (Approved Leave)
    - **`CO`** (Comp-Off)

---

## 4. Live Cell Editing & Optimistic Updates

### Test 4.1: Manual Status Change & Instant Validation
- **Action**:
  1. Locate employee **EMP-015 (Aarav Patel)** on Wednesday **2026-12-09**.
  2. Click the cell and select **`WEEKLY_OFF`** from the edit popover.
  3. Enter note: *"Scheduled weekly off"*.
  4. Click **Save**.
- **Expected Result**:
  - **Optimistic update**: The cell changes instantly without full-page reload.
  - **Live validation re-run**: The right-hand Conflicts drawer immediately updates to show an `E001 NO_COVERAGE` conflict on Nova Abandoned Cart for Dec 9.
  - Toast notification appears: *"Entry updated"*.

### Test 4.2: Cell Locking / Freezing (Constraint H1)
- **Action**:
  1. On any cell, click the **Lock / Freeze** icon.
  2. Confirm cell displays a small padlock indicator.
  3. Click **"Generate Roster"** again to create Version 2.
- **Expected Result**:
  - The CP-SAT solver respects the frozen cell (Invariant H1: locked cells are immutable to the solver).

---

## 5. Conflict Panel, Root Causes & Suggestion Engine

### Test 5.1: Review Conflict Details
- **Action**: Click the **Conflicts** button on the top right to open the drawer.
- **Filter**: Click **"Blocking Only"**.
- **Inspect**: Click on any `E001 NO_COVERAGE` or `E002 UNDER_STAFFED` conflict.
- **Expected Result**:
  - Clear plain-English explanation (e.g. *"Nova - Abandoned Cart has 0 staff on Wed 09 Dec. Minimum 1 required"*).
  - Root cause chips displayed: `[WEEKLY_OFF, LEAVE]`.
  - Severity badge: Red `BLOCKING`.

### Test 5.2: Apply Suggestion with Net Impact
- **Action**:
  1. Under the selected conflict, view the **Suggestions** list.
  2. Notice ranked suggestions:
     - Swap weekly off for Aarav Patel.
     - Assign Floater (EMP-033 Kabir Nair or EMP-034 Ananya Verma).
  3. Click **"Apply Suggestion"** on the top recommendation.
- **Expected Result**:
  - The recommended swap/assignment executes via API.
  - The conflict disappears or turns resolved.
  - The affected grid cells update automatically.

---

## 6. Holiday Work & Comp-Off Ledger Flow (Scenario S4)

### Test 6.1: Holiday Work Detection
- **Action**: Search for employee **EMP-008 (Karan Mehta)** on **2026-12-25** (Christmas).
- **Expected Result**:
  - Cell badge shows **`HW`** (`HOLIDAY_WORK`) because Solace operates 365 days.

### Test 6.2: Accrue Comp-Off Credit
- **Action**: Click **"Accrue Comp-Offs"** button on the Roster page header.
- **Expected Result**:
  - Success alert: *"Comp-offs accrued for holiday work"*.
  - In pgAdmin, run:
    ```sql
    SELECT * FROM comp_off_ledger WHERE employee_id = (SELECT id FROM employees WHERE code = 'EMP-008');
    ```
    *(Returns 1 row with `kind = 'EARNED'`, note citing Christmas 2026-12-25)*.

### Test 6.3: View Balance & Redeem Comp-Off
- **Action**:
  1. Navigate to **Comp-Offs** (`/comp-offs`).
  2. Search for **Karan Mehta**: Available balance shows **1 Credit**.
  3. Return to Roster view. On Karan Mehta's row for **2026-12-29**, change cell to **`COMP_OFF`**.
- **Expected Result**:
  - Cell changes to **`CO`**.
  - Validator checks balance: No `E009` overdraft conflict is raised.
  - Comp-Off balance decrements to 0.

---

## 7. Publish Gating & Version Immutability (Scenario S5)

### Test 7.1: Publish Blocked by Unresolved Conflicts
- **Action**: Click **"Publish Roster"** while unacknowledged blocking conflicts exist (e.g., Orion Friday mandatory offs).
- **Expected Result**:
  - A modal/error banner appears: **"Roster Blocked (HTTP 422)"**.
  - Message specifies: *"Cannot publish roster with unresolved BLOCKING conflicts"*.
  - Roster status remains **`DRAFT`**.

### Test 7.2: Acknowledge Blocking Conflicts & Successful Publish
- **Action**:
  1. In the Conflicts drawer, click **"Acknowledge"** on each remaining blocking conflict.
  2. Input reason: *"Approved operational exception by Ops Manager"*.
  3. Click **"Publish Roster"** again.
- **Expected Result**:
  - Status badge turns green: **`PUBLISHED`**.
  - All cells become **read-only** (published baselines are immutable).
  - Any subsequent edit automatically creates **Draft Version 2** for that month.
- **Database Verification in pgAdmin**:
  ```sql
  SELECT version, status FROM roster_periods WHERE month = '2026-12-01';
  ```
  *(Status is now `PUBLISHED`)*.

---

## 8. Version Comparison & Diffs

### Test 8.1: Side-by-Side Comparison
- **Action**:
  1. Generate or edit a second version (Draft v2).
  2. Navigate to **Compare** (`/roster/compare` or click "Compare Versions").
  3. Select **Version A** (Published v1) and **Version B** (Draft v2).
- **Expected Result**:
  - Side-by-side split grid renders.
  - Coverage delta metric displays (e.g. `+2.4%`).
  - Differences in individual employee cells are highlighted with colored pill diffs.

---

## 9. Export Engine

### Test 9.1: Excel (.xlsx) Download
- **Action**: Click **Export** $\to$ **Download Excel (.xlsx)**.
- **Expected Result**:
  - Browser downloads `roster-2026-12-v1.xlsx`.
  - Open in Excel:
    - Formatted header row with dates.
    - Color-coded cells (Green = Work, Gray = Weekly Off, Purple = Holiday Work, Red = Leave).
    - Summary column showing monthly work days and weekly offs per employee.

### Test 9.2: CSV Download
- **Action**: Click **Export** $\to$ **Download CSV**.
- **Expected Result**:
  - Browser downloads comma-separated values file readable in any text editor or spreadsheet program.

---

## 10. Audit Trail & Compliance

### Test 10.1: Inspect Immutable Audit Logs
- **Action**: Navigate to **Audit Logs** (`/audit-logs`).
- **Expected Result**:
  - A chronological table listing every action taken during your test:
    - `CREATE_ROSTER`
    - `UPDATE_ENTRIES`
    - `ACKNOWLEDGE_CONFLICT`
    - `PUBLISH_ROSTER`
  - Shows timestamp, acting user (`ops@example.test`), entity affected, and a clickable **"View Diff"** showing the exact before/after JSON state.
- **Database Verification in pgAdmin**:
  ```sql
  SELECT action, entity_type, created_at, after 
  FROM audit_logs 
  ORDER BY created_at DESC LIMIT 10;
  ```

