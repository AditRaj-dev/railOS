#!/usr/bin/env python
"""Import the railway reference data into the database, once.

Reference data is the network itself: corridors, sections, assets, resources.
It used to be read from datasets/*.json into memory on every process start, so
a restart silently rebuilt the world and nothing an operator entered outlived
it. This imports those files into railos_entity as durable rows; after that the
API reads the database and the dataset files are just an input you can re-run.

Operational records (maintenance tasks, defects, train movements, block
windows, goods forecasts) are NOT imported by default: in a real deployment
they arrive through the API or the ingestion adapters. Pass
--include-operational to load them too, which is what a demo environment wants.

    python scripts/import_reference_data.py --status
    python scripts/import_reference_data.py
    python scripts/import_reference_data.py --include-operational

Requires DATABASE_URL and RAILOS_STORAGE_BACKEND=postgres.
Run scripts/migrate.py first.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT / "apps" / "api"),
    *(str(p) for p in (ROOT / "packages").iterdir() if p.is_dir()),
    str(ROOT),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include-operational",
        action="store_true",
        help="also import tasks, defects, trains, windows and goods forecasts",
    )
    parser.add_argument("--status", action="store_true", help="report row counts and exit")
    parser.add_argument(
        "--force",
        action="store_true",
        help="import even though reference rows already exist (overwrites by id)",
    )
    args = parser.parse_args()

    os.environ.setdefault("RAILOS_STORAGE_BACKEND", "postgres")
    if os.environ["RAILOS_STORAGE_BACKEND"] != "postgres":
        sys.exit("this script imports into Postgres; set RAILOS_STORAGE_BACKEND=postgres")
    if not (os.getenv("DATABASE_URL") or os.getenv("RAILOS_DATABASE_URL")):
        sys.exit("DATABASE_URL (or RAILOS_DATABASE_URL) is required")

    # Imported here so the path setup above is in effect.
    from railos_api.main import PostgresRepository, load_reference_data

    repo = PostgresRepository()

    existing = {name: len(getattr(repo, name, {}) or {}) for name in ("corridors", "assets", "resources")}
    if args.status:
        print("current reference rows:")
        for name, count in existing.items():
            print(f"  {name:12} {count}")
        print(f"  {'network zones':12} {len(repo.network.zones)}")
        return 0

    if any(existing.values()) and not args.force:
        sys.exit(
            "reference data is already present "
            f"({', '.join(f'{k}={v}' for k, v in existing.items())}). "
            "Re-run with --force to overwrite it."
        )

    counts = load_reference_data(repo, include_operational=args.include_operational)
    repo.commit()

    print("imported:")
    for name, count in sorted(counts.items()):
        print(f"  {name:14} {count}")
    if not args.include_operational:
        print(
            "\nOperational records were not imported. Create them through the API, "
            "or re-run with --include-operational for a demo environment."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
