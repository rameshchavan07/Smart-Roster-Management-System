# User Flows

## 1. Roles and permissions

| Capability | Ops Manager | Pod Lead | Employee |
|---|---|---|---|
| Manage master data | ✔ | own pod only | – |
| Manage rules/holidays | ✔ | read | – |
| Enter/approve leave | ✔ | recommend for own pod | request own (stretch) |
| Generate / edit roster | ✔ | edit own pod cells (draft) | – |
| Publish roster | ✔ | – | – |
| Acknowledge blocking conflicts | ✔ | – | – |
| View company roster | ✔ | ✔ | – |
| View own roster | ✔ | ✔ | ✔ |
| Settings, users, audit | ✔ | – | – |

## 2. Primary journey — monthly planning (Ops Manager)

```mermaid
flowchart TD
    A[Login] --> B[Dashboard: choose month]
    B --> C{Master data & rules ready?}
    C -- no --> C1[Fix data: assignments, rules, holidays] --> C
    C -- yes --> D[Enter / approve leaves & comp-offs]
    D --> E[Generate roster]
    E --> F[Review conflict report & coverage heatmap]
    F --> G{Blocking conflicts?}
    G -- yes --> H[Open conflict drawer → read explanation]
    H --> I{Resolve how?}
    I -- apply suggestion --> J[Impact preview → Apply]
    I -- manual edit --> K[Edit cell → live impact → Apply]
    I -- cannot resolve --> L[Acknowledge with reason]
    J --> F
    K --> F
    L --> F
    G -- no --> M[Pod leads review pod views]
    M --> N[Publish]
    N --> O[Export CSV/XLSX]
```

## 3. Change-after-publish journey

```mermaid
flowchart TD
    A[New leave request / availability change] --> B[Impact simulator]
    B --> C{New blocking gaps?}
    C -- no --> D[Approve → roster updated, audit logged]
    C -- yes --> E[Show gaps per brand-process + ranked suggestions]
    E --> F{Manager choice}
    F -- backup/floater --> G[Apply suggestion]
    F -- local repair --> H[Re-solve affected window only]
    F -- reject leave --> I[Reject / negotiate]
    G --> J[New draft version vN+1 → validate → publish]
    H --> J
```

## 4. Journey: single-resource brand
1. Manager opens **Brand view → Aurora**.
2. Sees one employee, process rows CS/ACC/NDR, a ⚠ **single point of failure** badge.
3. Adds leave 13–15 Dec (Sun–Tue) in the simulator → red gaps on CS and ACC for all three days (both operate on Sunday) and on NDR only for Mon–Tue (NDR is closed on Sundays).
4. Drawer lists backups (floater Kabir: free on those days; fixes 3, opens 0).
5. Applies → Kabir shows as covering; audit entry records who/why.

## 5. Journey: three-person brand
1. Brand view → Nova: three employees (CS, ACC, NDR).
2. One goes on leave → matrix "remaining two vs demand per day" shows days still covered (green) and days not (red) with cause.
3. Manager reallocates a process temporarily or swaps a weekly off.

## 6. Journey: Pod Lead
Login → Roster (pod view locked to own pod) → review days/conflicts for team → comment/suggest edits (draft) → Ops Manager publishes.

## 7. Journey: Employee
Login → My Roster → sees statuses, holidays, comp-off balance → (stretch) request leave.

## 8. Navigation rules
- Month and view selection persist in the URL (`/roster?month=2026-12&view=brand&ref=aurora`) so links can be shared.
- Conflicts deep-link into the grid scrolled to the affected cell.
- Browser back returns to the previous view state.
- Unsaved edits prompt before leaving.

## 9. Error and edge flows
| Situation | Behaviour |
|---|---|
| Generation exceeds time limit | Show best-so-far roster labelled "time-limited" with conflicts |
| Solver unavailable | Fallback generator, banner explains |
| Edit on published roster | Creates new draft version; original untouched |
| Concurrent edit | 409 → "Roster changed by Priya at 10:42 — reload" |
| Session expired | Silent refresh once, else redirect to login preserving the route |
