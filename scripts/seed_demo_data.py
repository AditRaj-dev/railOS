#!/usr/bin/env python3
"""CLI utility to re-seed or verify demo data for RailOS.

Usage:
    python scripts/seed_demo_data.py
    python scripts/seed_demo_data.py --url http://127.0.0.1:8000
"""

import argparse
import json
import sys
import urllib.request
import urllib.error

def main():
    parser = argparse.ArgumentParser(description="Seed RailOS demonstration data (Tickets, Work Steps, Evidence)")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="RailOS API base URL (default: http://127.0.0.1:8000)")
    args = parser.parse_args()

    endpoint = f"{args.url.rstrip('/')}/api/v1/demo/seed"
    print(f"Triggering demo seed at: {endpoint} ...")

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
            print("Successfully seeded demonstration data!")
            print(json.dumps(data, indent=2))
    except urllib.error.URLError as exc:
        print(f"Failed to connect to RailOS API: {exc}", file=sys.stderr)
        print("Note: Ensure the API server is running (e.g. uvicorn railos_api.main:app --port 8000)", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
