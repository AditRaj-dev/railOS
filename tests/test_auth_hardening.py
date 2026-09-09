"""The header auth path must not be reachable unless a deployment opts in.

`main.auth()` accepts X-RailOS-User plus X-RailOS-Role with no credentials at
all. It was ungated - unlike auth.py's equivalent and the WebSocket path - so
any caller could send `X-RailOS-Role: ADMIN` and approve plans, sign sanctions
and drive possessions on a deployed instance. render.yaml shipped with the flag
enabled.
"""

import importlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "apps" / "api"), str(ROOT / "packages" / "railos_model"), str(ROOT / "packages" / "shared"), str(ROOT / "packages" / "optimizer"), str(ROOT)]

from fastapi.testclient import TestClient

from railos_api import auth as auth_module
from railos_api import main


ADMIN_HEADERS = {"X-RailOS-User": "anyone", "X-RailOS-Role": "ADMIN"}


class SyntheticAuthDisabledTests(unittest.TestCase):
    """With the flag off, header identities are refused everywhere."""

    def setUp(self):
        self._previous = main.ENABLE_SYNTHETIC_AUTH
        main.ENABLE_SYNTHETIC_AUTH = False
        main.state = main.Repository()
        self.client = TestClient(main.app)

    def tearDown(self):
        main.ENABLE_SYNTHETIC_AUTH = self._previous

    def test_header_admin_cannot_read_the_planning_api(self):
        response = self.client.get("/api/v1/block-requests", headers=ADMIN_HEADERS)
        self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(response.json()["error"]["code"], "UNAUTHENTICATED")

    def test_header_admin_cannot_create_a_ticket(self):
        response = self.client.post(
            "/api/v1/block-requests", headers=ADMIN_HEADERS,
            json={
                "department": "ENGG", "corridorId": "GZB-ALJN", "sectionId": "SEC_GZB_DER",
                "track": "UP", "kmStart": 1.0, "kmEnd": 2.0, "taskType": "TAMPING",
                "severity": 5, "estimatedDuration": 150, "requestedStart": 60,
                "requestedEnd": 300, "blockType": "TRAFFIC",
            },
        )
        self.assertEqual(response.status_code, 401, response.text)

    def test_header_admin_cannot_approve_a_plan(self):
        # Authentication runs before the handler, so an unknown plan id still
        # gets 401 rather than 404 - the header never reaches the authority layer.
        response = self.client.post(
            "/api/v1/block-plans/PLAN-does-not-exist/approve",
            headers=ADMIN_HEADERS, json={"reason": "approved"},
        )
        self.assertEqual(response.status_code, 401, response.text)

    def test_a_real_bearer_token_still_works(self):
        # Closing the header path must not close the login path with it.
        login = self.client.post(
            "/api/v1/auth/login", json={"employeeId": "EMP001", "password": "Admin@123"},
        )
        self.assertEqual(login.status_code, 200, login.text)
        listed = self.client.get(
            "/api/v1/block-requests",
            headers={"Authorization": f"Bearer {login.json()['accessToken']}"},
        )
        self.assertEqual(listed.status_code, 200, listed.text)


class ShippedCredentialTests(unittest.TestCase):
    """The source must not contain any account.

    The directory used to seed four accounts with passwords written in the
    module (EMP001/Admin@123 and three EMP90x supervisors), identical on every
    deployment and restored on every restart. Accounts now come from the
    database; the ones these tests log in with are created by a conftest
    fixture, not by the application.
    """

    def test_a_fresh_directory_has_no_accounts(self):
        from railos_api.evidence_routes import FieldEvidenceState

        self.assertEqual(dict(FieldEvidenceState().users), {})

    def test_the_signing_key_is_not_regenerated_per_process(self):
        # A keyless ManifestSigner() invents a new keypair, so a restart
        # silently invalidated every signature written before it.
        import os

        from railos_api.verification import _configured_signer

        previous = os.environ.pop("RAILOS_ALLOW_EPHEMERAL_SIGNING_KEY", None)
        try:
            with self.assertRaises(RuntimeError) as caught:
                _configured_signer()
            self.assertIn("RAILOS_EVIDENCE_SIGNING_KEY", str(caught.exception))
        finally:
            if previous is not None:
                os.environ["RAILOS_ALLOW_EPHEMERAL_SIGNING_KEY"] = previous

    def test_a_configured_signing_key_survives_reconstruction(self):
        import base64
        import os

        seed = base64.b64encode(bytes(range(32))).decode()
        os.environ["RAILOS_EVIDENCE_SIGNING_KEY"] = seed
        try:
            self.assertEqual(
                _configured_signer_public(), _configured_signer_public(),
            )
        finally:
            os.environ.pop("RAILOS_EVIDENCE_SIGNING_KEY", None)


def _configured_signer_public() -> bytes:
    from railos_api.verification import _configured_signer

    return _configured_signer().public_bytes


class JwtSecretTests(unittest.TestCase):
    def test_startup_refuses_a_missing_secret(self):
        # The module used to fall back to a secret published in the source tree.
        import os

        previous = {k: os.environ.get(k) for k in ("RAILOS_JWT_SECRET", "RAILOS_ALLOW_EPHEMERAL_JWT_SECRET")}
        os.environ.pop("RAILOS_JWT_SECRET", None)
        os.environ.pop("RAILOS_ALLOW_EPHEMERAL_JWT_SECRET", None)
        try:
            with self.assertRaises(RuntimeError) as caught:
                importlib.reload(auth_module)
            self.assertIn("RAILOS_JWT_SECRET", str(caught.exception))
        finally:
            for key, value in previous.items():
                if value is not None:
                    os.environ[key] = value
            importlib.reload(auth_module)

    def test_a_short_secret_is_refused(self):
        import os

        previous = os.environ.get("RAILOS_JWT_SECRET")
        os.environ["RAILOS_JWT_SECRET"] = "too-short"
        try:
            with self.assertRaises(RuntimeError):
                importlib.reload(auth_module)
        finally:
            if previous is None:
                os.environ.pop("RAILOS_JWT_SECRET", None)
            else:
                os.environ["RAILOS_JWT_SECRET"] = previous
            importlib.reload(auth_module)


if __name__ == "__main__":
    unittest.main()
