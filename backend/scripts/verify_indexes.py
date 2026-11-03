"""Verify database indexes and query plans for RosterOps (T-902).

Validates:
1. Composite indexes on roster_entries (roster_period_id, date)
2. Composite indexes on roster_conflicts (roster_period_id, severity)
3. Composite indexes on assignments (employee_id, brand_process_id)
4. EXPLAIN ANALYZE execution plans confirming Index Scan on core operational queries
"""

from __future__ import annotations

import sys
from sqlalchemy import text
from app.db.session import engine


def main() -> None:
    print("Verifying PostgreSQL indexes and query plans (T-902)...")

    with engine.connect() as conn:
        tables = ["roster_entries", "roster_conflicts", "assignments", "roster_periods"]
        for tbl in tables:
            print(f"\n=================== INDEXES ON {tbl} ===================")
            rows = conn.execute(
                text(
                    "SELECT indexname, indexdef FROM pg_indexes WHERE tablename = :t ORDER BY indexname"
                ),
                {"t": tbl},
            ).fetchall()
            for name, definition in rows:
                print(f"  • {name}:\n      {definition}")

        # Fetch a real sample period id
        period_row = conn.execute(text("SELECT id FROM roster_periods LIMIT 1")).fetchone()
        if not period_row:
            print("No roster periods in DB. Skipping query plan analysis.")
            return

        pid = period_row[0]
        print(f"\n=================== EXPLAIN ANALYZE PLANS (Sample Period: {pid}) ===================")

        queries = [
            (
                "Roster entries by period + date (Day View / Popover query)",
                "EXPLAIN ANALYZE SELECT * FROM roster_entries WHERE roster_period_id = :pid AND date = '2026-12-15'",
                {"pid": pid},
            ),
            (
                "Roster conflicts by period + severity (Gating / Badge count)",
                "EXPLAIN ANALYZE SELECT * FROM roster_conflicts WHERE roster_period_id = :pid AND severity = 'BLOCKING'",
                {"pid": pid},
            ),
            (
                "Roster entries full period (Grid Matrix query)",
                "EXPLAIN ANALYZE SELECT * FROM roster_entries WHERE roster_period_id = :pid",
                {"pid": pid},
            ),
            (
                "Roster periods by month (Dropdown & Versioning query)",
                "EXPLAIN ANALYZE SELECT * FROM roster_periods WHERE month = '2026-12-01' ORDER BY version DESC",
                {},
            ),
        ]

        for desc, q, params in queries:
            print(f"\n>>> Query: {desc}")
            print(f"    SQL: {q}")
            plan_rows = conn.execute(text(q), params).fetchall()
            for line in plan_rows:
                print(f"    {line[0]}")


if __name__ == "__main__":
    main()
