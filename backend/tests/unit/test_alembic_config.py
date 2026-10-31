"""Unit tests for Alembic configuration and migration environment."""

from pathlib import Path

from alembic.config import Config

from alembic import command
from app.db.base import Base


def test_alembic_config_loads() -> None:
    """Verify alembic.ini is discovered and loads valid configuration."""
    backend_dir = Path(__file__).resolve().parent.parent.parent
    ini_path = backend_dir / "alembic.ini"
    assert ini_path.exists(), "alembic.ini must exist in backend directory"

    alembic_cfg = Config(str(ini_path))
    script_loc = alembic_cfg.get_main_option("script_location")
    assert script_loc is not None


def test_alembic_upgrade_head_on_test_db(tmp_path: Path) -> None:
    """Verify alembic upgrade head executes cleanly against a test database."""
    backend_dir = Path(__file__).resolve().parent.parent.parent
    ini_path = backend_dir / "alembic.ini"
    test_db = tmp_path / "migration_test.db"
    db_url = f"sqlite:///{test_db.as_posix()}"

    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    # Test upgrade head runs without exception
    command.upgrade(alembic_cfg, "head")

    # Verify Base metadata is valid and accessible
    assert Base.metadata is not None
