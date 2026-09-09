#!/usr/bin/env python
"""Apply database/migrations/*.sql in order, once each.

There was no runner before this: the migration files existed but nothing ever
executed them, so the schema they describe had never been created. Each applied
file is recorded in schema_migrations, so re-running is safe.

    python scripts/migrate.py                 # apply pending migrations
    python scripts/migrate.py --status        # list applied/pending, apply nothing
    DATABASE_URL=postgres://... python scripts/migrate.py
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

MIGRATIONS = Path(__file__).resolve().parents[1] / "database" / "migrations"

LEDGER = """
CREATE TABLE IF NOT EXISTS schema_migrations (
  filename    text        PRIMARY KEY,
  checksum    text        NOT NULL,
  applied_at  timestamptz NOT NULL DEFAULT now()
)
"""


def database_url() -> str:
    url = os.getenv("DATABASE_URL") or os.getenv("RAILOS_DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL (or RAILOS_DATABASE_URL) is required")
    return url


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", action="store_true", help="show state without applying")
    args = parser.parse_args()

    try:
        import psycopg
    except ImportError:
        sys.exit("psycopg is required: pip install 'psycopg[binary]'")

    files = sorted(MIGRATIONS.glob("*.sql"))
    if not files:
        sys.exit(f"no migrations found in {MIGRATIONS}")

    with psycopg.connect(database_url(), autocommit=False) as conn:
        conn.execute(LEDGER)
        conn.commit()
        applied = {
            row[0]: row[1]
            for row in conn.execute("SELECT filename, checksum FROM schema_migrations").fetchall()
        }

        pending = []
        for path in files:
            body = path.read_text(encoding="utf-8")
            checksum = hashlib.sha256(body.encode("utf-8")).hexdigest()
            if path.name not in applied:
                pending.append((path, body, checksum))
            elif applied[path.name] != checksum:
                # Editing an applied migration silently diverges the schema from
                # what the file claims. Say so rather than skipping quietly.
                sys.exit(
                    f"{path.name} was already applied but its contents changed. "
                    "Add a new migration instead of editing an applied one."
                )

        if args.status:
            for path in files:
                print(f"  {'applied' if path.name in applied else 'PENDING'}  {path.name}")
            return 0

        if not pending:
            print(f"up to date — {len(applied)} migration(s) applied")
            return 0

        for path, body, checksum in pending:
            print(f"applying {path.name} …", flush=True)
            try:
                conn.execute(body)
                conn.execute(
                    "INSERT INTO schema_migrations (filename, checksum) VALUES (%s, %s)",
                    (path.name, checksum),
                )
                conn.commit()
            except Exception as exc:
                conn.rollback()
                sys.exit(f"{path.name} failed, rolled back: {exc}")

        print(f"applied {len(pending)} migration(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
