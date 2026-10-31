# Deployment Guide

Goal: a **public URL with seeded demo data**, reproducible from the repo. (Brief §7)

## 1. Environments
| Env | Purpose | Database |
|---|---|---|
| local | Development | Docker Postgres 16 |
| test | Automated tests | Ephemeral Postgres (container / CI service) |
| production | Public demo for evaluators | Managed Postgres (Neon or Supabase) |

## 2. Configuration (`.env.example`)
```dotenv
# --- Backend ---
APP_ENV=production            # local | test | production
DATABASE_URL=postgresql+psycopg://user:password@host:5432/rosterops
JWT_SECRET=change-me-long-random-string
JWT_ACCESS_MINUTES=30
JWT_REFRESH_DAYS=7
CORS_ORIGINS=https://your-frontend.example   # comma-separated allow-list
SOLVER_TIME_LIMIT_S=20
SOLVER_SEED=42
LOG_LEVEL=INFO
SEED_ON_START=false           # true only for the first demo deploy
DEMO_PASSWORD=set-at-deploy-time

# --- Frontend (build-time) ---
VITE_API_BASE_URL=https://your-api.example/api/v1
```
Never commit real values; `.env.example` holds placeholders only.

## 3. Local setup
```bash
git clone <repo> && cd rosterops
cp .env.example .env
docker compose up -d db
cd backend && uv sync && uv run alembic upgrade head && uv run python -m app.seed
uv run uvicorn app.main:app --reload       # API on :8000, docs on /docs
cd ../frontend && npm install && npm run dev   # UI on :5173
```

## 4. Containers
- `backend/Dockerfile`: python:3.12-slim, install with uv, non-root user, `HEALTHCHECK` on `/health`, start with `uvicorn --host 0.0.0.0 --port $PORT`.
- `frontend/Dockerfile` (optional): build with Node, serve static output; or deploy as a static site without a container.
- `docker-compose.yml` for local: `db`, `api`, `web`.

OR-Tools wheels are large; keep the image on a slim base and avoid unneeded build tools.

## 5. Recommended hosting (free-tier friendly)
| Part | Option | Notes |
|---|---|---|
| Database | Neon or Supabase Postgres | Use the pooled connection string if offered |
| API | Render web service (Docker) | Free tier sleeps → first request is slow; see §8 |
| Frontend | Vercel or Netlify (static) | SPA fallback rewrite to `index.html`; set `VITE_API_BASE_URL` |

Single-host alternative: serve the built frontend from FastAPI static files (one deploy, no CORS) — acceptable if you prefer fewer moving parts.

## 6. Deploy steps
1. Provision Postgres; copy the connection string.
2. Create the API service from the repo; set environment variables from §2; build command = Docker build; **pre-deploy command:** `alembic upgrade head`.
3. First deploy only: run `python -m app.seed` (one-off job/shell) or set `SEED_ON_START=true` once, then turn it off.
4. Deploy frontend with the API URL; set the API's `CORS_ORIGINS` to the frontend URL.
5. Smoke test (§7).

## 7. Smoke test (T-1004)
```bash
curl -fsS https://<api>/health
# login → token → GET /rosters?month=2026-12 → POST /rosters → GET conflicts
```
Then open the UI in a private window and run the QA checklist in `TESTING_DOCUMENTATION.md`.

## 8. Operational notes
- **Cold start:** open the API URL a few minutes before recording the video or submitting; optionally add an uptime pinger hitting `/health`.
- **Solver limits:** keep `SOLVER_TIME_LIMIT_S` below the host's request timeout (e.g. 20 s vs 30–60 s).
- **Migrations** are forward-only in production; to roll back, restore from a DB snapshot or write a new migration.
- **Backups:** managed Postgres snapshots are enough for the demo.
- **Logs:** structured JSON to stdout; request id returned to clients in error bodies.

## 9. CI/CD (stretch)
GitHub Actions: on PR run ruff, mypy, pytest, frontend lint/build; on merge to `main` trigger host auto-deploy.

## 10. Release checklist
- [ ] All tests green, migrations applied
- [ ] `.env.example` up to date, no secrets in the repo history
- [ ] Demo accounts work; passwords delivered out-of-band or in the submission email
- [ ] Live URL verified from a fresh browser and a phone
- [ ] README, approach note and video link ready
