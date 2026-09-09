#!/usr/bin/env python
"""Create the first administrator account.

The four seeded accounts (EMP001/Admin@123 and the EMP901-903 supervisors)
were removed - they shipped in the source, were identical on every
deployment and reset on every restart. A fresh database therefore has no
users at all, and this is the only way in.

    RAILOS_ADMIN_PASSWORD=... python scripts/create_admin.py --employee-id EMP001 --name "Chief Controller"
    python scripts/create_admin.py --employee-id EMP001 --name "Chief Controller"   # prompts

Requires DATABASE_URL and RAILOS_STORAGE_BACKEND=postgres.
Run scripts/migrate.py first.
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT / "apps" / "api"),
    *(str(p) for p in (ROOT / "packages").iterdir() if p.is_dir()),
    str(ROOT),
]

MIN_PASSWORD_LENGTH = 12


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--employee-id", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--email")
    parser.add_argument(
        "--role", default="ADMIN", choices=["ADMIN", "DISPATCHER", "INSPECTOR"],
        help="SUPERVISOR accounts need a department; create those through the admin API",
    )
    args = parser.parse_args()

    os.environ.setdefault("RAILOS_STORAGE_BACKEND", "postgres")
    if os.environ["RAILOS_STORAGE_BACKEND"] != "postgres":
        sys.exit("this script writes to Postgres; set RAILOS_STORAGE_BACKEND=postgres")
    if not (os.getenv("DATABASE_URL") or os.getenv("RAILOS_DATABASE_URL")):
        sys.exit("DATABASE_URL (or RAILOS_DATABASE_URL) is required")
    # The account is useless if the API cannot verify tokens it later issues.
    os.environ.setdefault("RAILOS_ALLOW_EPHEMERAL_JWT_SECRET", "true")

    password = os.getenv("RAILOS_ADMIN_PASSWORD")
    if not password:
        password = getpass.getpass("Password: ")
        if password != getpass.getpass("Confirm: "):
            sys.exit("passwords do not match")
    if len(password) < MIN_PASSWORD_LENGTH:
        sys.exit(f"password must be at least {MIN_PASSWORD_LENGTH} characters")

    # Imported here so the path setup above is in effect.
    from railos_api.auth import hash_password
    from railos_api.user_store import user_store_factory

    store = user_store_factory()
    if any(u.get("employeeId") == args.employee_id for u in store.users.values()):
        sys.exit(f"employee ID {args.employee_id} already exists")

    user_id = f"adm-{uuid.uuid4().hex[:8]}"
    store.users[user_id] = {
        "userId": user_id,
        "employeeId": args.employee_id,
        "name": args.name,
        "role": args.role,
        "department": None,
        "passwordHash": hash_password(password),
        "email": args.email,
        "phone": None,
        "active": True,
    }
    print(f"created {args.role} {args.employee_id} ({user_id})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
