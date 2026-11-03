#!/bin/bash
set -e

echo "==> Running database migrations..."
alembic upgrade head

echo "==> Checking if seeding is required..."
SEED_CHECK=$(python -c "
from app.core.config import get_settings
from sqlalchemy import create_engine, select, func
from app.models.auth import User
try:
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL.replace('+asyncpg', ''))
    with engine.connect() as conn:
        count = conn.execute(select(func.count(User.id))).scalar()
        print('SEED_NEEDED' if count == 0 else 'ALREADY_SEEDED')
except Exception as e:
    print('SEED_NEEDED')
")

if [ "$SEED_CHECK" = "SEED_NEEDED" ]; then
    echo "==> Seeding database with demo data..."
    python -m app.seed
else
    echo "==> Database already seeded ($SEED_CHECK)."
fi

PORT="${PORT:-8000}"
echo "==> Starting Uvicorn server on 0.0.0.0:$PORT..."
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
