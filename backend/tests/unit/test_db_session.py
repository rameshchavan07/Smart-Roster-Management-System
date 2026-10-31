"""Unit tests for database session and connection pooling configuration."""

import contextlib

from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import get_settings
from app.db.session import create_db_engine, get_db


def test_sqlite_engine_configuration() -> None:
    """Verify SQLite URLs use NullPool."""
    engine = create_db_engine("sqlite:///:memory:")
    assert isinstance(engine.pool, NullPool)
    engine.dispose()


def test_postgres_pool_configuration() -> None:
    """Verify PostgreSQL URLs configure QueuePool with settings."""
    settings = get_settings()
    engine = create_db_engine("postgresql+psycopg://test_user:test_pass@localhost:5432/test_db")
    assert isinstance(engine.pool, QueuePool)
    assert engine.pool.size() == settings.DB_POOL_SIZE
    assert engine.pool._max_overflow == settings.DB_MAX_OVERFLOW
    assert engine.pool._timeout == settings.DB_POOL_TIMEOUT_S
    assert engine.pool._recycle == settings.DB_POOL_RECYCLE_S
    assert engine.pool._pre_ping is True
    engine.dispose()


def test_get_db_session_lifecycle() -> None:
    """Verify get_db dependency yields a session and closes it."""
    db_gen = get_db()
    session = next(db_gen)
    assert session is not None
    assert session.is_active is True
    with contextlib.suppress(StopIteration):
        next(db_gen)
