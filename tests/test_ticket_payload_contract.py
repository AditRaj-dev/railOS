"""The composer's payload and the API's schema must not drift apart.

BlockRequestCreate is populate_by_name=False with extra="forbid": a key the
schema does not declare is a hard 422, and so is a missing required one. The
composer had no test that its payload actually satisfied the schema — every
frontend ticket test mocks the mutation away — so a rename on either side
surfaced only as an unmappable validation error in front of an operator.
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "apps" / "api"), str(ROOT / "packages" / "railos_model"), str(ROOT / "packages" / "shared"), str(ROOT / "packages" / "optimizer"), str(ROOT)]

from railos_api import main

# Mirrors createPayload() in apps/control-center/src/components/TicketComposer.tsx.
# TicketComposer.test.tsx asserts the composer emits exactly this set.
COMPOSER_PAYLOAD_KEYS = {
    "department", "corridorId", "sectionId", "assetId", "track",
    "kmStart", "kmEnd", "taskType", "severity", "estimatedDuration",
    "blockType", "requestedStart", "requestedEnd",
}

# Server-derived optimizer flags. The composer must never send these.
SERVER_OWNED_KEYS = {
    "requiresPTW", "requiresT351", "requiresCorrespondenceTest", "machineType",
}


class TicketPayloadContractTests(unittest.TestCase):
    def test_composer_sends_only_keys_the_schema_accepts(self):
        unknown = COMPOSER_PAYLOAD_KEYS - main.BLOCK_REQUEST_CREATE_FIELDS
        self.assertEqual(unknown, set(), f"composer sends keys the API forbids: {unknown}")

    def test_composer_supplies_every_required_key(self):
        required = {
            field.alias or name
            for name, field in main.BlockRequestCreate.model_fields.items()
            if field.is_required()
        }
        missing = required - COMPOSER_PAYLOAD_KEYS
        self.assertEqual(missing, set(), f"composer omits required keys: {missing}")

    def test_server_owned_flags_are_not_client_settable(self):
        leaked = SERVER_OWNED_KEYS & main.BLOCK_REQUEST_CREATE_FIELDS
        self.assertEqual(leaked, set(), f"optimizer flags must stay server-derived: {leaked}")

    def test_schema_is_camel_case_only(self):
        # populate_by_name=False means a snake_case body is rejected even when
        # the field names match. Nothing may quietly relax that.
        self.assertFalse(main.BlockRequestCreate.model_config["populate_by_name"])
        self.assertEqual(main.BlockRequestCreate.model_config["extra"], "forbid")
        snake = {f for f in main.BLOCK_REQUEST_CREATE_FIELDS if "_" in f}
        self.assertEqual(snake, set())


if __name__ == "__main__":
    unittest.main()
