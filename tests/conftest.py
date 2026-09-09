import os
import pathlib

# Set before railos_api is imported anywhere. The API refuses to start without
# a JWT secret (it used to fall back to one hardcoded in the source), and the
# header auth path is off unless a deployment opts in. Tests get a random
# per-process secret and the header path explicitly enabled, because most of
# them authenticate with X-RailOS-Role rather than a login.
os.environ.setdefault("RAILOS_ALLOW_EPHEMERAL_JWT_SECRET", "true")
os.environ.setdefault("ENABLE_SYNTHETIC_AUTH", "true")
# Evidence signatures are verified within the process; a real deployment must
# supply a key that outlives it (RAILOS_EVIDENCE_SIGNING_KEY).
os.environ.setdefault("RAILOS_ALLOW_EPHEMERAL_SIGNING_KEY", "true")

import pytest

from railos_data import load_world

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def world():
    return load_world(ROOT / "datasets")


@pytest.fixture(scope="session")
def plan(world):
    from optimizer import solve

    return solve(world)


# The four seeded accounts (EMP001/EMP901-903) were deleted from the source:
# they shipped real passwords and were identical on every deployment. The
# tests that exercise login, supervisor admin and the field evidence chain
# still need accounts, so they provision their own here.
TEST_ACCOUNTS = [
    ("admin-01", "EMP001", "Chief Controller", "ADMIN", None, "Admin@123"),
    ("sup-01", "EMP901", "Rajesh Kumar (SSE/P-Way)", "SUPERVISOR", "ENGG", "Field@123"),
    ("sup-02", "EMP902", "Meena Iyer (SSE/Signal)", "SUPERVISOR", "SNT", "Field@123"),
    ("sup-03", "EMP903", "Arjun Nair (SSE/TRD)", "SUPERVISOR", "TRD", "Field@123"),
]
TEST_SECTIONS = ["SEC_GZB_DER", "SEC_DER_KRJ", "SEC_KRJ_SMQ", "SEC_SMQ_ALJN"]


@pytest.fixture(scope="session", autouse=True)
def test_accounts():
    """Seed the directory once per session (Argon2 hashing is deliberately slow)."""
    from railos_api.auth import hash_password
    from railos_api.evidence_routes import evidence_state

    for user_id, employee_id, name, role, department, password in TEST_ACCOUNTS:
        evidence_state.users[user_id] = {
            "userId": user_id,
            "employeeId": employee_id,
            "name": name,
            "role": role,
            "department": department,
            "passwordHash": hash_password(password),
            "email": f"{employee_id.lower()}@railos.test",
            "phone": None,
            "active": True,
        }
        evidence_state.assignments[user_id] = list(TEST_SECTIONS)
    yield
    for user_id, *_ in TEST_ACCOUNTS:
        evidence_state.users.pop(user_id, None)
        evidence_state.assignments.pop(user_id, None)
