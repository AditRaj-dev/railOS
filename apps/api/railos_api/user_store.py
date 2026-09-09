"""Durable user directory.

The user directory used to be four hardcoded accounts in a module-level dict:
shipped passwords, reset on every restart, identical on every deployment.
Accounts now live in the `users` / `refresh_tokens` tables from migration
005, with a memory backend for tests and local runs.

The stores expose a mapping interface because that is what the auth routes
already used; swapping the backing dict for a table kept those call sites
unchanged. Rows are small and read on nearly every request, so the postgres
backend queries per call rather than caching - correctness over a round trip.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Iterator, MutableMapping


def _now():
    return datetime.now(timezone.utc)

# Columns of `users` that the routes address by camelCase key.
_USER_COLUMNS = (
    ("userId", "id"),
    ("employeeId", "employee_id"),
    ("name", "name"),
    ("email", "email"),
    ("phone", "phone"),
    ("role", "role"),
    ("department", "department"),
    ("passwordHash", "password_hash"),
    ("active", "active"),
    ("createdAt", "created_at"),
)


class MemoryUserStore:
    """Dict-backed directory. No seeded accounts - an empty deployment has no
    way in until `scripts/create_admin.py` creates the first one."""

    def __init__(self):
        self.users: MutableMapping[str, dict[str, Any]] = {}
        self.refresh_tokens: MutableMapping[str, dict[str, Any]] = {}
        self.assignments: MutableMapping[str, list[str]] = {}


class _UsersTable(MutableMapping):
    def __init__(self, connection):
        self._c = connection

    @staticmethod
    def _row(row) -> dict[str, Any]:
        record = {key: value for (key, _), value in zip(_USER_COLUMNS, row)}
        created = record.get("createdAt")
        if hasattr(created, "isoformat"):
            record["createdAt"] = created.isoformat()
        return record

    def _select(self, where: str = "", params: tuple = ()):
        columns = ",".join(column for _, column in _USER_COLUMNS)
        return self._c.execute(f"SELECT {columns} FROM users {where}", params)

    def __getitem__(self, key):
        row = self._select("WHERE id=%s", (key,)).fetchone()
        if row is None:
            raise KeyError(key)
        return self._row(row)

    def __setitem__(self, key, value):
        self._c.execute(
            "INSERT INTO users(id,employee_id,name,email,phone,role,department,"
            "password_hash,active) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT(id) DO UPDATE SET employee_id=EXCLUDED.employee_id,"
            "name=EXCLUDED.name,email=EXCLUDED.email,phone=EXCLUDED.phone,"
            "role=EXCLUDED.role,department=EXCLUDED.department,"
            "password_hash=EXCLUDED.password_hash,active=EXCLUDED.active,"
            "updated_at=now()",
            (
                key, value["employeeId"], value["name"], value.get("email"),
                value.get("phone"), value["role"], value.get("department"),
                value["passwordHash"], value.get("active", True),
            ),
        )

    def __delitem__(self, key):
        self._c.execute("DELETE FROM users WHERE id=%s", (key,))

    def __iter__(self) -> Iterator[str]:
        return iter([row[0] for row in self._c.execute("SELECT id FROM users").fetchall()])

    def __len__(self) -> int:
        return self._c.execute("SELECT count(*) FROM users").fetchone()[0]

    def values(self):
        return [self._row(row) for row in self._select().fetchall()]

    def items(self):
        return [(record["userId"], record) for record in self.values()]


class _RefreshTokensTable(MutableMapping):
    """`revoked` is stored as `revoked_at`; the routes only ever read the flag."""

    def __init__(self, connection):
        self._c = connection

    def __getitem__(self, key):
        row = self._c.execute(
            "SELECT user_id,expires_at,revoked_at FROM refresh_tokens WHERE token_hash=%s",
            (key,),
        ).fetchone()
        if row is None:
            raise KeyError(key)
        return {
            "userId": row[0],
            "expiresAt": row[1].isoformat() if hasattr(row[1], "isoformat") else row[1],
            "revoked": row[2] is not None,
        }

    def __setitem__(self, key, value):
        self._c.execute(
            "INSERT INTO refresh_tokens(token_hash,user_id,expires_at,revoked_at) "
            "VALUES(%s,%s,%s,%s) ON CONFLICT(token_hash) DO UPDATE SET "
            "revoked_at=EXCLUDED.revoked_at",
            (
                key, value["userId"], value["expiresAt"],
                _now() if value.get("revoked") else None,
            ),
        )

    def __delitem__(self, key):
        self._c.execute("DELETE FROM refresh_tokens WHERE token_hash=%s", (key,))

    def __iter__(self) -> Iterator[str]:
        return iter([
            row[0] for row in
            self._c.execute("SELECT token_hash FROM refresh_tokens").fetchall()
        ])

    def __len__(self) -> int:
        return self._c.execute("SELECT count(*) FROM refresh_tokens").fetchone()[0]


class _AssignmentsView(MutableMapping):
    """Section assignments are a column on the user row, not a table."""

    def __init__(self, connection):
        self._c = connection

    def __getitem__(self, key):
        row = self._c.execute(
            "SELECT assigned_section_codes FROM users WHERE id=%s", (key,)
        ).fetchone()
        if row is None:
            raise KeyError(key)
        return list(row[0] or [])

    def __setitem__(self, key, value):
        self._c.execute(
            "UPDATE users SET assigned_section_codes=%s,updated_at=now() WHERE id=%s",
            (list(value), key),
        )

    def __delitem__(self, key):
        self[key] = []

    def __iter__(self) -> Iterator[str]:
        return iter([row[0] for row in self._c.execute("SELECT id FROM users").fetchall()])

    def __len__(self) -> int:
        return self._c.execute("SELECT count(*) FROM users").fetchone()[0]


class PostgresUserStore:
    def __init__(self, url: str):
        import psycopg

        self.connection = psycopg.connect(url, connect_timeout=3, autocommit=True)
        self.users = _UsersTable(self.connection)
        self.refresh_tokens = _RefreshTokensTable(self.connection)
        self.assignments = _AssignmentsView(self.connection)


def user_store_factory():
    backend = os.getenv("RAILOS_STORAGE_BACKEND", "memory").lower()
    if backend != "postgres":
        return MemoryUserStore()
    url = os.getenv("DATABASE_URL") or os.getenv("RAILOS_DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required for postgres backend")
    return PostgresUserStore(url)
