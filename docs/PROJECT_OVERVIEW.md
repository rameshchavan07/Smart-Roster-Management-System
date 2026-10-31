# Project Overview — Smart Roster Management System

> Status: **Draft v0.1** · Source: Datastraw Tech Internship Assessment brief · Legend: **[Doc]** = stated in the brief, **[Rec]** = our recommendation

## 1. Introduction

A growing customer-experience and operations company runs support and operational processes (Customer Support, Abandoned Cart Conversions, Retention, NDR, …) for multiple D2C brands. At least 30 employees are spread across brands, processes and pods; each pod has a pod lead. **[Doc]**

Every month the operations team builds a roster. Today this is manual and breaks down as the team grows, because:

- Brands operate on different calendars (365 days / every day except public holidays / Sundays and public holidays off). **[Doc]**
- About **80% of brands have one dedicated employee** for all of that brand's processes; the rest have 2–3. **[Doc]**
- One weekly off or leave can leave a whole brand uncovered, and one change can ripple across several brands. **[Doc]**

## 2. Objective

Build a working, browser-based **roster management application** that helps an operations manager **plan, generate, validate and manage monthly rosters** across brands, processes and pods. **[Doc]**

The brief is explicit: *solve the scheduling problem, not just build a calendar or digitise a spreadsheet.* Reliable scheduling and clear conflict detection outrank visual polish. **[Doc]**

## 3. Scope

### In scope
| Area | Notes | Source |
|---|---|---|
| Master data (employees, brands, processes, pods, leads, allocations) | Editable without code changes | Doc |
| Brand/process working rules and coverage minimums | Calendar types, per-weekday and per-date minimums | Doc |
| Availability: weekly offs, leaves, comp-offs, public holidays | | Doc |
| Monthly roster generation | Deterministic + solver | Doc |
| Conflict detection with mandatory-vs-preference distinction | | Doc |
| Five views: company, pod, brand, process, employee | | Doc |
| Manual editing with live validation | | Doc |
| Change handling (at least one demonstrated) | Impact preview + resolution suggestions | Doc |
| Sample dataset (30+ employees, ~80% single-resource brands) | | Doc |
| Public deployment, GitHub repo, README, demo video, approach note | | Doc |
| Role-based login | | Rec |
| Draft → Published status, audit log | | Rec |
| CSV/XLSX export, fairness of weekly offs, backup recommendations | Optional list | Doc (optional) |

### Out of scope for v1 **[Rec]**
- Time-of-day shifts (day-level working/off only; schema is extensible — see `ASSUMPTIONS_AND_OPEN_QUESTIONS.md`).
- Payroll, attendance tracking, biometric integration.
- Email/Slack notifications and multi-level approval workflows (stretch only).
- Native mobile apps.

## 4. Expected outcomes

1. An ops manager selects a month, clicks **Generate**, and gets a roster plus a **conflict report** — never a silently invalid roster.
2. Every brand/process/day shows required vs actual coverage (OK / under-staffed / uncovered).
3. Editing a cell or adding a leave shows its **impact** (new and resolved conflicts) before it is applied, with ranked **resolution suggestions**.
4. The system works with a realistic seeded dataset and is reachable at a public URL.

## 5. Stakeholders

| Stakeholder | Interest |
|---|---|
| Operations Manager (primary user) | Plans, validates, publishes rosters |
| Pod Lead | Reviews their pod's roster |
| Employee | Sees own schedule (read-only; optional leave request) |
| Datastraw evaluators | Judge modelling, scheduling logic, explainability, deployment |

## 6. Success criteria

- Generated roster passes the independent validator (no BLOCKING conflicts) whenever a valid roster exists.
- When none exists, the report names the exact brand/process/date and cause.
- The five documented demo scenarios all behave as specified (`SAMPLE_DATA.md`).
- Generation for 36 employees × 31 days completes in under ~15 s.
- New brand/process/rule can be added through the UI with no code change.

## 7. Glossary

| Term | Meaning |
|---|---|
| Brand-process | A process (e.g. CS) run for a brand; the unit of coverage |
| Operating calendar | Which dates a brand-process must be staffed |
| Demand | Required minimum staff per brand-process per date |
| Supply | Employees available to work on a date |
| Roster entry | One employee on one date with a status |
| Weekly off (WO) | Recurring rest day |
| Comp-off | Rest day earned by working a holiday/weekly off |
| Floater / backup | Employee able to cover other employees' brand-processes |
| Mandatory constraint | Must hold (coverage, leave, weekly-off entitlement) |
| Preference | Nice-to-have (preferred off day); yields to mandatory |

## 8. Deliverable mapping (from the brief)

| Brief deliverable | Where it comes from |
|---|---|
| Working URL | `DEPLOYMENT.md` |
| GitHub repo + README + `.env.example` | `FOLDER_STRUCTURE.md`, README |
| 3–5 min demo video | `SAMPLE_DATA.md` demo scenarios |
| Approach note + 8 "How do you think" answers | `SCHEDULING_ENGINE.md`, `ASSUMPTIONS_AND_OPEN_QUESTIONS.md` |
| LinkedIn link | Submission email |
