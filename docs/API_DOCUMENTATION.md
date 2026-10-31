# API Documentation

Base URL: `/api/v1` · Format: JSON · Docs UI: `/docs` (OpenAPI) · Dates: ISO `YYYY-MM-DD` · Months: `YYYY-MM`

## 1. Authentication
- `POST /auth/login` → `{access_token, refresh_token, expires_in, user}`
- Send `Authorization: Bearer <access_token>` on every other call.
- Access token lifetime 30 min; refresh token 7 days (rotated on use).
- Roles: `OPS_MANAGER` (full), `POD_LEAD` (read all, write own pod), `EMPLOYEE` (read own).

## 2. Conventions
- Pagination: `?limit=50&offset=0` → `{items, total, limit, offset}`.
- Filtering: query params (`?pod_id=…&is_active=true`).
- Idempotent PUT/DELETE; POST creates.
- IDs are UUIDs.

## 3. Error format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [{"field": "end_date", "issue": "must be on or after start_date"}],
    "request_id": "b1c7…"
  }
}
```
| HTTP | code | When |
|---|---|---|
| 400 | `BAD_REQUEST` | malformed input |
| 401 | `UNAUTHENTICATED` | missing/expired token |
| 403 | `FORBIDDEN` | role lacks permission |
| 404 | `NOT_FOUND` | unknown id |
| 409 | `CONFLICT` | duplicate/overlap/state conflict (e.g. roster already published) |
| 422 | `VALIDATION_ERROR` | schema/business validation |
| 422 | `ROSTER_BLOCKED` | publish attempted with BLOCKING conflicts |
| 429 | `RATE_LIMITED` | too many requests |
| 500 | `INTERNAL_ERROR` | unexpected |

## 4. Endpoints

### Auth
| Method | Path | Role | Description |
|---|---|---|---|
| POST | /auth/login | public | Email + password |
| POST | /auth/refresh | public | Rotate tokens |
| POST | /auth/logout | any | Revoke refresh token |
| GET | /auth/me | any | Current user |

### Master data (OPS_MANAGER write; POD_LEAD own-pod write; others read)
| Resource | Paths |
|---|---|
| Pods | `GET/POST /pods`, `GET/PUT/DELETE /pods/{id}` |
| Employees | `GET/POST /employees`, `GET/PUT/DELETE /employees/{id}` |
| Processes | `GET/POST /processes`, `PUT/DELETE /processes/{id}` |
| Brands | `GET/POST /brands`, `GET/PUT/DELETE /brands/{id}` |
| Brand-processes | `GET/POST /brand-processes`, `GET/PUT/DELETE /brand-processes/{id}` |
| Coverage rules | `GET/POST /brand-processes/{id}/coverage-rules`, `PUT/DELETE /coverage-rules/{id}` |
| Assignments | `GET/POST /assignments`, `PUT/DELETE /assignments/{id}` |
| Holidays | `GET/POST /holidays`, `PUT/DELETE /holidays/{id}` |
| Weekly-off rules | `GET/POST /employees/{id}/weekly-off-rules`, `PUT/DELETE /weekly-off-rules/{id}` |
| Preferences | `GET/POST /employees/{id}/preferences`, `PUT/DELETE /preferences/{id}` |

Deleting an entity that has history returns **409** and offers deactivation (`PUT … {is_active:false}`).

### Leave and comp-off
| Method | Path | Description |
|---|---|---|
| GET/POST | /leaves | list/create (status REQUESTED, or APPROVED if manager) |
| PUT | /leaves/{id} | edit |
| POST | /leaves/{id}/approve · /reject · /cancel | state changes; response includes **impact summary** on rosters |
| GET | /employees/{id}/comp-off-balance | earned, redeemed, available |
| POST | /comp-offs/redeem | redeem for a date |

### Roster
| Method | Path | Description |
|---|---|---|
| POST | /rosters | Create + generate for a month |
| GET | /rosters?month=YYYY-MM | List versions |
| GET | /rosters/{id} | Metadata, summary counts, solver status |
| GET | /rosters/{id}/grid?view=company\|pod\|brand\|process\|employee&ref_id=… | Grid data for the selected view |
| GET | /rosters/{id}/coverage?brand_process_id=… | Required vs actual per date |
| GET | /rosters/{id}/day?date=… | Who is working on a date, with coverage state |
| GET | /rosters/{id}/conflicts?severity=&brand_id=&date= | Conflict list |
| POST | /rosters/{id}/impact | Dry-run a change; returns conflict diff |
| PUT | /rosters/{id}/entries | Apply one or more cell changes (validated, audited) |
| POST | /rosters/{id}/entries/lock | Lock/unlock cells |
| GET | /rosters/{id}/suggestions?conflict_id=… | Ranked resolutions |
| POST | /rosters/{id}/repair | Local repair around affected employees/dates |
| POST | /rosters/{id}/acknowledge | Acknowledge a BLOCKING conflict with reason |
| POST | /rosters/{id}/publish | Publish if no unacknowledged BLOCKING conflicts |
| POST | /rosters/{id}/clone | New version / alternate plan |
| GET | /rosters/compare?a=…&b=… | Diff + conflict/fairness comparison |
| GET | /rosters/{id}/export?format=csv\|xlsx | Download |

### Misc
| GET | /audit-logs | filter by entity/date/user |
|---|---|---|
| GET | /health, /ready | liveness/readiness |

## 5. Key request/response examples

### Generate
`POST /rosters`
```json
{ "month": "2026-12", "options": { "seed": 42, "time_limit_s": 20, "base_roster_id": null } }
```
`201`
```json
{
  "id": "6f1e…", "month": "2026-12", "version": 1, "status": "DRAFT",
  "solver_status": "OPTIMAL",
  "summary": { "blocking": 2, "warnings": 5, "info": 3, "coverage_pct": 99.1 }
}
```

### Impact (what-if)
`POST /rosters/{id}/impact`
```json
{ "changes": [ { "type": "ADD_LEAVE", "employee_id": "…", "start_date": "2026-12-10", "end_date": "2026-12-11" } ] }
```
`200`
```json
{
  "new_conflicts": [
    { "code": "E001", "severity": "BLOCKING", "brand": "Aurora", "process": "CS",
      "date": "2026-12-10",
      "message": "Aurora CS has no coverage on 10 Dec. Its only assigned employee, Riya Shah, would be on leave.",
      "root_causes": ["LEAVE"],
      "suggestions": [ { "kind": "USE_BACKUP", "employee": "Kabir Nair", "net_effect": {"fixes": 1, "opens": 0} } ] }
  ],
  "resolved_conflicts": [],
  "unchanged": 4
}
```

### Cell edit
`PUT /rosters/{id}/entries`
```json
{ "entries": [ { "employee_id": "…", "date": "2026-12-14", "status": "WEEKLY_OFF", "reason": "Swap" } ],
  "acknowledge_blocking": false }
```
`200` returns updated entries plus the conflict diff; `422 ROSTER_BLOCKED` is **not** used here — edits are allowed in DRAFT even if they create conflicts (they are reported); only **publish** is gated.

### Publish blocked
`422`
```json
{ "error": { "code": "ROSTER_BLOCKED", "message": "2 blocking conflicts remain",
  "details": [ {"conflict_id": "…", "summary": "Aurora CS uncovered on 14 Dec"} ] } }
```

## 6. Versioning and compatibility
Path-versioned (`/v1`). Additive changes only within a version. Frontend uses a TypeScript client generated from `/openapi.json`.
