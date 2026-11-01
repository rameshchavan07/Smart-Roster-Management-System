"""Unit tests for Alembic configuration and migration environment."""

from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect

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


def test_alembic_upgrade_and_downgrade_lifecycle(tmp_path: Path) -> None:
    """Verify alembic upgrade head and downgrade base execute cleanly on all tables."""
    backend_dir = Path(__file__).resolve().parent.parent.parent
    ini_path = backend_dir / "alembic.ini"
    test_db = tmp_path / "migration_lifecycle_test.db"
    db_url = f"sqlite:///{test_db.as_posix()}"

    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    # 1. Upgrade to head
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(db_url)
    inspector = inspect(engine)
    created_tables = set(inspector.get_table_names())

    expected_tables = {
        "pods",
        "processes",
        "brands",
        "employees",
        "brand_processes",
        "comp_off_ledger",
        "employee_preferences",
        "holidays",
        "leaves",
        "users",
        "weekly_off_rules",
        "assignments",
        "audit_logs",
        "coverage_rules",
        "roster_periods",
        "roster_conflicts",
        "roster_entries",
    }
    assert expected_tables.issubset(created_tables)

    # 2. Downgrade back to base
    command.downgrade(alembic_cfg, "base")
    inspector = inspect(engine)
    remaining_tables = set(inspector.get_table_names())
    # Only alembic_version table should remain
    assert remaining_tables.issubset({"alembic_version"})

    # 3. Re-upgrade cleanly
    command.upgrade(alembic_cfg, "head")
    inspector = inspect(engine)
    recreated_tables = set(inspector.get_table_names())
    assert expected_tables.issubset(recreated_tables)

    # Base metadata check
    assert Base.metadata is not None
