"""Database engine, connection pooling, and session management."""

from collections.abc import Generator
from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import get_settings


def create_db_engine(db_url: str | None = None) -> Engine:
    """Create SQLAlchemy 2.0 engine with connection pooling."""
    settings = get_settings()
    url = db_url or settings.DATABASE_URL

    kwargs: dict[str, Any] = {
        "echo": settings.LOG_LEVEL.upper() == "DEBUG",
        "future": True,
    }

    if url.startswith("sqlite"):
        # SQLite uses NullPool or StaticPool for in-memory / local files
        kwargs["poolclass"] = NullPool
    else:
        # PostgreSQL uses QueuePool with configured limits
        kwargs.update(
            {
                "poolclass": QueuePool,
                "pool_size": settings.DB_POOL_SIZE,
                "max_overflow": settings.DB_MAX_OVERFLOW,
                "pool_timeout": settings.DB_POOL_TIMEOUT_S,
                "pool_recycle": settings.DB_POOL_RECYCLE_S,
                "pool_pre_ping": settings.DB_POOL_PRE_PING,
            }
        )

    return create_engine(url, **kwargs)


engine = create_db_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    future=True,
)


def get_db() -> Generator[Session, None, None]:
    """Dependency that provides a transactional database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
