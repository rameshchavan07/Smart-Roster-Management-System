# Commands

Assumes the repo layout from `FOLDER_STRUCTURE.md` and the proposed stack (uv, Alembic, npm). Adjust if the owner changes a decision.

## One-time setup
```bash
cp .env.example .env
docker compose up -d db                      # Postgres 16
cd backend && uv sync                        # install Python deps
uv run alembic upgrade head                  # apply migrations
uv run python -m app.seed                    # deterministic demo data
cd ../frontend && npm install
```

## Run
```bash
cd backend && uv run uvicorn app.main:app --reload --port 8000   # API; docs at /docs
cd frontend && npm run dev                                       # UI on :5173
```

## Backend quality
```bash
cd backend
uv run ruff check . && uv run ruff format --check .
uv run mypy app/scheduler                    # strict on the engine
uv run pytest                                # all tests
uv run pytest tests/unit/scheduler -q        # engine only (fast)
uv run pytest tests/scenarios -q             # demo scenarios S1–S5
uv run pytest --cov=app/scheduler --cov-report=term-missing
```

## Database
```bash
uv run alembic revision --autogenerate -m "describe change"      # then review the file
uv run alembic upgrade head
uv run alembic downgrade -1                                      # local only
uv run python -m app.seed --scale 3                              # stress dataset (~110 employees)
```

## Frontend quality
```bash
cd frontend
npm run lint && npm run typecheck && npm run build
npm run test                                  # component tests (stretch)
npm run api:generate                          # regenerate typed client from /openapi.json
```

## Before every commit
```bash
cd backend && uv run ruff check . && uv run mypy app/scheduler && uv run pytest
cd ../frontend && npm run lint && npm run typecheck
```

## Dependency audit
```bash
cd backend && uv run pip-audit
cd ../frontend && npm audit
```
