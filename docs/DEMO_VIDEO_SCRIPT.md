# Smart Roster Management System (RosterOps) — Demo Video Script (3–5 Minutes)

> **Goal**: A concise, polished 3–5 minute video demonstration showcasing all key features, the scheduling engine, conflict explainability, what-if impact simulation, and role-based access control.

---

## Video Timeline & Walkthrough

### Part 1: Introduction & Operational Context (0:00 – 0:45)
- **Visual**: Start on the **Dashboard** (`http://localhost:5173/dashboard`) logged in as **Ops Manager** (`ops@example.test`).
- **Narration**:
  > *"Welcome to RosterOps, an intelligent operations scheduling platform designed for complex multi-brand, multi-process teams. 
  > In this system, we manage 25 e-commerce brands across 38 operating processes and 6 pods, staffed by 36 employees. 
  > Over 80% of our brands are single-resource brands operating 365 days a year. Our core philosophy is Demand vs. Supply: the system never fakes coverage or presents an invalid schedule as valid."*
- **Actions**:
  - Point to the KPI Strip: **Coverage %**, **Single-Point Brands (20)**, **Needs Attention list**.
  - Show the **Workload Distribution chart** by pod.

---

### Part 2: Deterministic Solver Run & Interactive Grid (0:45 – 1:30)
- **Visual**: Navigate to **Roster Workspace** (`/roster`).
- **Narration**:
  > *"Let's generate the monthly schedule for December 2026. The backend runs Google OR-Tools CP-SAT with mathematical optimization. 
  > Notice that hard constraints like mandatory weekly offs and approved leaves strictly dominate soft preferences."*
- **Actions**:
  - Click **"Generate Roster"** &rarr; modal opens with Seed (42) and Time Limit (20s).
  - Click **"Start Generation"** &rarr; in 1–2 seconds, the 1,116 shift cells render with status `DRAFT v1`.
  - Demonstrate view switching:
    - **`Company`**: Full 36-person matrix with virtualized scrolling.
    - **`Pod`**: Filter by Pod A.
    - **`Brand`**: Grouped under brand processes (e.g. Aurora CS, Nova ACC).
    - **`Employee`**: Switch to Riya Shah (`EMP-007`) showing her personal 31-day shift schedule.
  - Click a cell &rarr; show **Cell Edit Popover** (optimistic update with live validation).

---

### Part 3: Conflict Explainability & 1-Click Floaters (1:30 – 2:30)
- **Visual**: Navigate to **Conflicts** (`/conflicts`).
- **Narration**:
  > *"Here is Scenario S1: Brand Aurora is a single-resource brand whose sole employee, Riya Shah, is on approved leave from Dec 13 to 15. 
  > Because Aurora requires 365-day coverage, the validator immediately flags E001 NO_COVERAGE gaps with root cause LEAVE. 
  > The engine doesn't just complain — it calculates second-order net impact and surfaces ranked recommendations."*
- **Actions**:
  - Click on **Aurora – Customer Support (14 Dec)**.
  - Show the right-hand flyout: plain-language explanation and root causes.
  - Point out Floater **`EMP-033 Kabir Nair`** with score and *"fixes 1 gap, opens 0"*.
  - Click **"Apply Suggestion"** &rarr; the floater is assigned, the schedule re-validates, and the conflict disappears.

---

### Part 4: What-If Impact Simulator & Local Repair (2:30 – 3:15)
- **Visual**: Navigate to **Impact Simulator** (`/simulator`).
- **Narration**:
  > *"What happens when an employee requests unplanned leave? Let's simulate before touching live data. 
  > On Scenario S2 (Brand Nova), let's simulate adding leave for Aarav Patel on Dec 9."*
- **Actions**:
  - Select employee **Aarav Patel**, type **Add Leave**, date **2026-12-09**.
  - Click **"Simulate Impact"** &rarr; view the diff highlighting the new `E001` conflict on Nova Abandoned Cart.
  - Click **"Apply & Repair"** &rarr; the solver freezes all unaffected cells and repairs the impacted window automatically!

---

### Part 5: Holiday Work & Comp-Off Ledger (3:15 – 4:00)
- **Visual**: Go to **Leaves & Comp-offs** (`/leaves`).
- **Narration**:
  > *"Scenario S4 handles holiday work and comp-offs. On December 25 (Christmas), Brand Solace operates 365 days. 
  > Karan Mehta (EMP-008) works a holiday shift, recorded as HW."*
- **Actions**:
  - Click **"Accrue Holiday Work Comp-Offs"** in the top bar.
  - Show the success alert: Karan Mehta's ledger balance increments to **1 Credit**.
  - Point out that when Karan redeems comp-off on Dec 29, the validator checks the ledger to prevent overdrafts (`E009`).

---

### Part 6: Publish Gating (Rule A-13) & Role-Based Access Control (4:00 – 4:45)
- **Visual**: Return to **Roster Workspace** &rarr; **Publish**.
- **Narration**:
  > *"In Scenario S5, Brand Orion has dual mandatory Friday offs. Attempting to publish while unacknowledged blocking conflicts exist triggers Rule A-13 publish gating."*
- **Actions**:
  - Click **"Publish Roster"** &rarr; notice the modal highlights remaining blocking conflicts and disables publish.
  - Acknowledge with reason: *"Approved operational exception"*.
  - Click **"Publish"** &rarr; status updates to green **`PUBLISHED`** and cells become immutable.
  - Log out and log in as **`emp@example.test`** (`TestPassword123!`):
    - Verify role badge **`Role: EMPLOYEE`**.
    - Show clean self-service view: personal calendar, leave request modal, comp-off balance.
    - Show that administrative tools and publishing are strictly guarded.

---

### Part 7: Conclusion & Wrap-Up (4:45 – 5:00)
- **Visual**: Show GitHub repo with 226 tests passing, Dockerfiles, and documentation.
- **Narration**:
  > *"In summary, RosterOps pairs mathematical rigor with intuitive operational workflows: CP-SAT solver, pure-Python validator, full auditability, and 226 automated tests. Thank you!"*
