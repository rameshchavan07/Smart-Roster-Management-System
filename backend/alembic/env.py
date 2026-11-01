from logging.config import fileConfig

from alembic import context
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import create_db_engine

# Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Ensure all models are registered on Base.metadata
import app.models  # noqa: F401, E402

# Model's MetaData object for 'autogenerate' support
target_metadata = Base.metadata


def get_url() -> str:
    """Return database URL from alembic config if overridden, else application settings."""
    x_args = context.get_x_argument(as_dictionary=True)
    if "url" in x_args:
        return x_args["url"]
    cfg_url = config.get_main_option("sqlalchemy.url")
    if cfg_url and not cfg_url.startswith("%") and not cfg_url.startswith("driver://"):
        return cfg_url
    return get_settings().DATABASE_URL


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Use our application's engine with connection pooling and dialect support
    url = get_url()
    connectable = create_db_engine(url)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
