# Requirements

Legend: **[Doc]** stated in the brief · **[Rec]** our recommendation · Priority: **M** = MVP, **S** = Stretch

## 1. Functional requirements

### 1.1 Team, brand, process management (brief §3A)
| ID | Requirement | Src | Pri |
|---|---|---|---|
| FR-MD-01 | CRUD for pods, with one pod lead per pod | Doc | M |
| FR-MD-02 | CRUD for employees (name, pod, role, active flag, floater flag, weekly-off count, max consecutive days) | Doc/Rec | M |
| FR-MD-03 | CRUD for processes (catalog: CS, ACC, Retention, NDR, …) and brands | Doc | M |
| FR-MD-04 | Enable a process for a brand (**brand-process**) with its own calendar and coverage rules | Doc | M |
| FR-MD-05 | Assign employees to brand-processes (many-to-many), type PRIMARY or BACKUP, with effective dates | Doc | M |
| FR-MD-06 | An employee may be assigned to multiple brands/processes | Doc | M |
| FR-MD-07 | Sample dataset ≥ 30 employees, ~80% single-resource brands | Doc | M |
| FR-MD-08 | Soft-delete/deactivate rather than hard-delete when history exists | Rec | M |

### 1.2 Working rules (brief §3B)
| ID | Requirement | Src | Pri |
|---|---|---|---|
| FR-RL-01 | Calendar types per brand-process: `ALL_365`, `ALL_EXCEPT_HOLIDAYS`, `EXCLUDE_SUNDAY_AND_HOLIDAYS` | Doc | M |
| FR-RL-02 | Default minimum coverage per brand-process | Doc | M |
| FR-RL-03 | Override minimum coverage by weekday and by specific date | Doc | M |
| FR-RL-04 | Different weekly-off patterns for employees on the same brand | Doc | M |
| FR-RL-05 | Brand's operating calendar kept separate from employee's working schedule | Doc | M |
| FR-RL-06 | Custom operating-day sets (e.g. Mon–Sat) beyond the three presets | Rec | S |

### 1.3 Availability (brief §2, §3C)
| ID | Requirement | Src | Pri |
|---|---|---|---|
| FR-AV-01 | Public holiday calendar (global, optionally brand-specific) | Doc | M |
| FR-AV-02 | Planned leaves (date range, type, status) | Doc | M |
| FR-AV-03 | Comp-offs: earned by working a holiday/weekly off; ledger with balance and approved redemption | Doc | M |
| FR-AV-04 | Weekly-off rule per employee: fixed weekdays, rotating, or "any" | Doc/Rec | M |
| FR-AV-05 | Employee preferences (preferred off weekdays/dates), flagged as preference not mandatory | Doc | M |

### 1.4 Roster generation (brief §3C)
| ID | Requirement | Src | Pri |
|---|---|---|---|
| FR-GN-01 | Select a month and generate a roster for all active employees | Doc | M |
| FR-GN-02 | Honour calendars, assignments, weekly offs, holidays, leaves, comp-offs, minimum coverage | Doc | M |
| FR-GN-03 | Handle employees across multiple brands/processes | Doc | M |
| FR-GN-04 | Never assume identical schedules or calendars | Doc | M |
| FR-GN-05 | If not all requirements can be met: produce the best roster **and** list each unmet requirement with cause | Doc/Rec | M |
| FR-GN-06 | Roster shows working/off per person and coverage adequacy per brand-process-day | Doc | M |
| FR-GN-07 | Fair distribution of weekly offs (including weekend offs) | Doc (opt) | S |
| FR-GN-08 | Preference-based scheduling | Doc (opt) | M |
| FR-GN-09 | Locked cells preserved across regeneration | Rec | M |
| FR-GN-10 | Alternative plan generation and comparison | Doc (opt) | S |

### 1.5 Validation and conflict detection (brief §3D)
| ID | Requirement | Src | Pri |
|---|---|---|---|
| FR-VL-01 | Detect required coverage with no available employee | Doc | M |
| FR-VL-02 | Detect insufficient staffing vs minimum | Doc | M |
| FR-VL-03 | Detect weekly off / leave / comp-off conflicting with required coverage | Doc | M |
| FR-VL-04 | Detect overlapping or overloaded responsibilities (employee counted on too many brand-processes) | Doc | M |
| FR-VL-05 | Detect changes creating gaps across multiple brands | Doc | M |
| FR-VL-06 | Detect rule/preference violations; classify BLOCKING / WARNING / INFO | Doc | M |
| FR-VL-07 | Mandatory vs preference: mandatory always wins | Doc | M |
| FR-VL-08 | Unresolvable conflicts clearly flagged with plain-language explanation | Doc | M |
| FR-VL-09 | Validator is independent of the generator and runs on any roster, including manually edited | Rec | M |

### 1.6 Views and editing (brief §3E)
| ID | Requirement | Src | Pri |
|---|---|---|---|
| FR-VW-01 | Company, pod, brand, process, employee views | Doc | M |
| FR-VW-02 | "Who is working on date X" lookup with coverage status | Doc | M |
| FR-VW-03 | Edit a cell (status change) with live validation and impact preview | Doc | M |
| FR-VW-04 | Bulk operations (swap two employees' days, copy week) | Rec | S |
| FR-VW-05 | Draft → Published status; published roster edits create a new version | Rec | M |

### 1.7 Handling changes (brief §3F)
| ID | Requirement | Src | Pri |
|---|---|---|---|
| FR-CH-01 | Adding/changing leave or availability after generation re-validates only affected dates | Doc | M |
| FR-CH-02 | Flag resulting coverage gaps, per brand-process | Doc | M |
| FR-CH-03 | Rank suggested resolutions (backup, weekly-off swap, comp-off shift) | Doc | M |
| FR-CH-04 | Evaluate whether remaining employees on a multi-person brand can still cover | Doc | M |
| FR-CH-05 | Local repair that leaves unaffected entries unchanged | Rec | S |
| FR-CH-06 | Brand requirement changes (e.g. new minimum) trigger re-validation | Doc | M |

### 1.8 Platform
| ID | Requirement | Src | Pri |
|---|---|---|---|
| FR-PL-01 | Login with roles: Ops Manager, Pod Lead, Employee | Rec | M |
| FR-PL-02 | Audit log of data and roster changes | Rec | M |
| FR-PL-03 | Export CSV / XLSX | Doc (opt) | S |
| FR-PL-04 | AI-assisted conflict explanations | Doc (opt) | S (last) |

## 2. Non-functional requirements

| ID | Requirement | Src |
|---|---|---|
| NFR-01 | Correctness first: no invalid roster presented as valid | Doc |
| NFR-02 | Flexibility: new brands/processes/employees/rules via UI/config, no code change | Doc |
| NFR-03 | Scales in design to 2× employees and brands (see engine doc) | Doc |
| NFR-04 | Publicly accessible deployment with seeded data | Doc |
| NFR-05 | Explainability: every conflict and every auto-decision has a reason | Doc |
| NFR-06 | Performance: generate ≤ 15 s (36 emp × 31 d); validate edit ≤ 500 ms; page loads ≤ 2 s | Rec |
| NFR-07 | Security: authenticated API, RBAC, validated input, hashed passwords, no secrets in repo | Rec |
| NFR-08 | Reliability: deterministic output for the same input + seed | Rec |
| NFR-09 | Maintainability: layered architecture, typed code, linted, tested | Rec |
| NFR-10 | Accessibility: WCAG 2.1 AA contrast, keyboard operable grid | Rec |
| NFR-11 | Responsive: desktop-first, usable on tablet and mobile (agenda view) | Rec |
| NFR-12 | Observability: structured logs, `/health` | Rec |

## 3. Acceptance criteria (summary)

1. Seed → Generate (any month) → zero BLOCKING conflicts, or each remaining conflict is explained.
2. Single-resource 365-day brand + weekly off → engine either uses a floater or reports `E001` for that date; never hides it.
3. Adding a leave to a 3-employee brand shows "remaining employees can/cannot cover" per day.
4. A manual edit that breaks coverage shows the new conflict before saving; confirming saves with an audit entry.
5. Validator catches every injected fault in the validator test-suite.
