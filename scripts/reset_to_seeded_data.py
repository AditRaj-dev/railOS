#!/usr/bin/env python3
"""CLI utility to reset RailOS state to only the clean seeded baseline data.

Purges all dynamically generated plans, optimization runs, emergencies,
possessions, and temporary work assignments, leaving only the authoritative
seeded baseline data (from datasets/*.json).

Usage:
    python scripts/reset_to_seeded_data.py
    python scripts/reset_to_seeded_data.py --url http://127.0.0.1:8000
"""

import argparse
import json
import sys
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser(
        description="Reset RailOS database/state to only core seeded baseline data"
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000",
        help="RailOS API base URL (default: http://127.0.0.1:8000)",
    )
    args = parser.parse_args()

    endpoint = f"{args.url.rstrip('/')}/api/v1/demo/reset"
    print(f"Triggering clean database reset at: {endpoint} ...")

    req = urllib.request.Request(
        endpoint,
        data=b"{}",
        headers={
            "Content-Type": "application/json",
            "X-RailOS-Role": "ADMIN",
            "X-RailOS-User": "admin-01",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print("Successfully purged all runtime/synthetic data!")
            print("Database is now reset to clean seeded baseline:")
            print(json.dumps(data, indent=2))
    except urllib.error.URLError as exc:
        print(f"Failed to connect to RailOS API: {exc}", file=sys.stderr)
        print(
            "Note: Ensure the API server is running (e.g. uvicorn apps.api.railos_api.main:app --port 8000)",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
