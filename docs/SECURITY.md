# Security

Scope: an internal operations tool holding employee names, emails and schedules (personal data), deployed publicly for evaluation.

## 1. Authentication
- Email + password; passwords hashed with **Argon2id** (argon2-cffi defaults, tuned to ~100 ms).
- **JWT** access tokens (30 min) and rotating refresh tokens (7 days). Refresh tokens stored hashed server-side so logout/revocation works.
- Frontend keeps the access token in memory and the refresh token in an `HttpOnly; Secure; SameSite=Lax` cookie (preferred over localStorage to limit XSS exposure).
- Login rate limit (e.g. 5 attempts/min per IP+email) and generic error text ("Invalid email or password").
- No self-registration; accounts are created by the Ops Manager or the seed script.

## 2. Authorisation (RBAC)
| Role | Scope |
|---|---|
| OPS_MANAGER | Everything |
| POD_LEAD | Read all rosters; write only own pod's employees/cells in DRAFT |
| EMPLOYEE | Read only own roster, leaves and comp-off balance |

Rules are enforced **server-side** in FastAPI dependencies (never only in the UI); object-level checks (pod ownership, "own record") live in the service layer. Every role-guarded route has a negative test (T-804).

## 3. Data protection
- TLS everywhere (host-provided HTTPS); HSTS header on the API.
- Database credentials only in environment variables; least-privilege DB user (no superuser).
- PII minimised: no phone numbers, addresses or government IDs stored. Demo data is fictional.
- Soft-delete with audit trail; audit entries record who changed what and when (before/after JSON), never passwords or tokens.
- Backups via managed Postgres snapshots; not exported to unsecured locations.

## 4. Input validation and injection
- Pydantic validates every request body, query and path parameter (types, ranges, enums, lengths, date ordering).
- SQL only through SQLAlchemy parameter binding; no string-built SQL.
- Output encoding handled by React; no `dangerouslySetInnerHTML`. Free-text notes are rendered as text.
- Request body size limits; cap on date ranges and batch sizes for roster edits.

## 5. Transport and browser protections
- CORS: explicit allow-list from `CORS_ORIGINS`; no wildcard with credentials.
- Security headers: `Content-Security-Policy` (self + API origin), `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`, `X-Frame-Options: DENY`.
- CSRF: access token sent via `Authorization` header; the refresh cookie is `SameSite=Lax` and its endpoint requires a custom header.

## 6. Availability and abuse
- Global rate limit per IP; stricter on `/auth/*` and on `POST /rosters` (solver is CPU-heavy).
- Solver bounded by time limit and a cap on problem size per request; one active generation per month.
- Generic 500 responses; stack traces only in logs, with a `request_id` for support.

## 7. Secrets and supply chain
- No secrets in the repo; `.env.example` holds placeholders; rotate `JWT_SECRET` if ever exposed.
- Pin dependency versions; run `pip-audit` and `npm audit` (T-905); enable Dependabot; minimal dependencies.
- Container runs as non-root, slim base image.

## 8. Logging and monitoring
Structured JSON logs with request id, user id and route; never log credentials, tokens or full request bodies. Alert on repeated 401/403 and 5xx in hosting dashboard.

## 9. Demo-environment caveats
Because the demo URL is public, seeded passwords are shared with evaluators only; the demo database contains fictional data only and can be reset by re-running the seed.

## 10. Security checklist (T-903 & T-905)
- [x] Argon2id hashing, token expiry, refresh rotation
- [x] RBAC negative tests pass across all routes
- [x] CORS allow-list and security headers verified (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, CSP)
- [x] Sliding-window rate limits on auth and generation (15 requests/min per IP)
- [x] No secrets in repo/history; `.env.example` complete
- [x] `pip-audit` / `npm audit` audited; dev tooling CVE exceptions documented
- [x] Error responses leak no internals (uniform error envelope with UUID `request_id`)
