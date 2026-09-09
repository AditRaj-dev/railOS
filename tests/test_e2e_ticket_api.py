import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "apps" / "api"), str(ROOT / "packages" / "railos_model"), str(ROOT / "packages" / "shared"), str(ROOT / "packages" / "optimizer"), str(ROOT)]

from fastapi.testclient import TestClient
from railos_api import main

ENGG_HEADERS = {"X-RailOS-User": "engg-1", "X-RailOS-Role": "ENGINEERING"}
SNT_HEADERS = {"X-RailOS-User": "snt-1", "X-RailOS-Role": "SIGNAL_TELECOM"}
TRD_HEADERS = {"X-RailOS-User": "trd-1", "X-RailOS-Role": "TRACTION"}
CONTROL_HEADERS = {"X-RailOS-User": "control-1", "X-RailOS-Role": "CONTROL_OFFICER"}
MANAGEMENT_HEADERS = {"X-RailOS-User": "mgmt-1", "X-RailOS-Role": "MANAGEMENT", "X-RailOS-Department": "ENGG"}
SUPERVISOR_HEADERS = {"X-RailOS-User": "sup-1", "X-RailOS-Role": "FIELD_SUPERVISOR", "X-RailOS-Department": "ENGG"}


def base_payload(**overrides):
    payload = {
        "department": "ENGG",
        "corridorId": "GZB-ALJN",
        "sectionId": "SEC_GZB_DER",
        "track": "UP",
        "kmStart": 1.0,
        "kmEnd": 2.0,
        "taskType": "TAMPING",
        "severity": 5,
        "estimatedDuration": 150,
        "requestedStart": 60,
        "requestedEnd": 300,
        "blockType": "TRAFFIC",
    }
    payload.update(overrides)
    return payload


class TicketApiTests(unittest.TestCase):
    def setUp(self):
        main.state = main.Repository()
        self.client = TestClient(main.app)

    def test_create_ticket_for_each_department(self):
        cases = [
            (ENGG_HEADERS, base_payload(department="ENGG", sectionId="SEC_GZB_DER", track="UP", taskType="TAMPING")),
            (SNT_HEADERS, base_payload(department="SNT", sectionId="SEC_GZB_DER", track="DOWN", taskType="SNT_RECONNECTION")),
            (TRD_HEADERS, base_payload(department="TRD", sectionId="SEC_GZB_DER", track="UP", taskType="OHE_INSPECTION")),
        ]
        for headers, payload in cases:
            response = self.client.post("/api/v1/block-requests", headers=headers, json=payload)
            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            self.assertEqual(body["status"], "REQUESTED")
            self.assertTrue(body["linkedTaskId"].startswith("TKT-"))
            self.assertIsNotNone(body["linkedTask"])

            tasks = self.client.get("/api/v1/maintenance/tasks", headers=headers).json()
            task_ids = [t["taskId"] for t in tasks["items"]]
            self.assertIn(body["linkedTaskId"], task_ids)

    def test_cross_department_forbidden(self):
        payload = base_payload(department="ENGG")
        response = self.client.post("/api/v1/block-requests", headers=SNT_HEADERS, json=payload)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "DEPARTMENT_FORBIDDEN")

    def test_task_type_department_mismatch(self):
        payload = base_payload(department="ENGG", taskType="POINT_MACHINE_MAINT")
        response = self.client.post("/api/v1/block-requests", headers=ENGG_HEADERS, json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "TASK_TYPE_DEPARTMENT_MISMATCH")

    def test_track_not_on_section_is_named_as_such(self):
        # The demo network is double line; a THIRD-track request is a track
        # problem and must not be reported as a missing asset.
        response = self.client.post("/api/v1/block-requests", headers=ENGG_HEADERS, json=base_payload(track="THIRD"))
        self.assertEqual(response.status_code, 422)
        error = response.json()["error"]
        self.assertEqual(error["code"], "TRACK_NOT_ON_SECTION")
        self.assertEqual(sorted(error["details"]["tracks"]), ["DOWN", "UP"])

    def test_overview_only_section_is_refused_before_the_asset_question(self):
        response = self.client.post(
            "/api/v1/block-requests", headers=ENGG_HEADERS,
            json=base_payload(sectionId="DEMO_FZR_LDH"),
        )
        self.assertEqual(response.status_code, 422)
        error = response.json()["error"]
        self.assertEqual(error["code"], "SECTION_CORRIDOR_MISMATCH")
        self.assertIn("SEC_GZB_DER", error["details"]["sectionIds"])

    def test_asset_required_when_no_candidate_matches(self):
        # Point work where the section and track hold no point machine.
        response = self.client.post(
            "/api/v1/block-requests", headers=SNT_HEADERS,
            json=base_payload(department="SNT", taskType="POINT_MACHINE_MAINT", estimatedDuration=120),
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "ASSET_REQUIRED")

    def test_km_out_of_section(self):
        payload = base_payload(assetId="TRACK_SEC_GZB_DER_UP", kmStart=1.0, kmEnd=25.0)
        response = self.client.post("/api/v1/block-requests", headers=ENGG_HEADERS, json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "KM_OUT_OF_SECTION")

    def test_idempotent_replay_returns_same_request_and_single_task(self):
        payload = base_payload()
        headers = ENGG_HEADERS | {"Idempotency-Key": "ticket-1"}
        first = self.client.post("/api/v1/block-requests", headers=headers, json=payload)
        self.assertEqual(first.status_code, 200, first.text)
        second = self.client.post("/api/v1/block-requests", headers=headers, json=payload)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["requestId"], second.json()["requestId"])

        tasks = self.client.get("/api/v1/maintenance/tasks", headers=ENGG_HEADERS).json()
        matching = [t for t in tasks["items"] if t["taskId"] == first.json()["linkedTaskId"]]
        self.assertEqual(len(matching), 1)

        conflict = self.client.post(
            "/api/v1/block-requests",
            headers=headers,
            json=base_payload(severity=9),
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["error"]["code"], "IDEMPOTENCY_CONFLICT")

    def test_list_filters_by_department_and_forces_scope(self):
        self.client.post("/api/v1/block-requests", headers=ENGG_HEADERS, json=base_payload(department="ENGG", sectionId="SEC_GZB_DER", track="UP", taskType="TAMPING"))
        self.client.post("/api/v1/block-requests", headers=SNT_HEADERS, json=base_payload(department="SNT", sectionId="SEC_GZB_DER", track="DOWN", taskType="SNT_RECONNECTION"))

        broad = self.client.get("/api/v1/block-requests", headers=CONTROL_HEADERS, params={"department": "ENGG"})
        self.assertEqual(broad.status_code, 200)
        self.assertTrue(all(item["department"] == "ENGG" for item in broad.json()["items"]))

        scoped = self.client.get("/api/v1/block-requests", headers=SNT_HEADERS)
        self.assertEqual(scoped.status_code, 200)
        self.assertTrue(all(item["department"] == "SNT" for item in scoped.json()["items"]))
        self.assertTrue(len(scoped.json()["items"]) >= 1)

    def test_task_type_catalog_carries_statutory_duration_floors(self):
        response = self.client.get("/api/v1/block-requests/task-types", headers=ENGG_HEADERS)
        self.assertEqual(response.status_code, 200)
        by_type = {item["taskType"]: item for item in response.json()["items"]}
        # TAMPING runs a CSM (150 min floor), OHE_INSPECTION a tower wagon (120).
        self.assertEqual(by_type["TAMPING"]["minDurationMinutes"], 150)
        self.assertEqual(by_type["TAMPING"]["department"], "ENGG")
        self.assertEqual(by_type["OHE_INSPECTION"]["minDurationMinutes"], 120)
        self.assertTrue(by_type["POINT_MACHINE_MAINT"]["requiresT351"])
        # The composer picks the asset list off this: point work is identified
        # by a POINT, plain track work by the track section itself.
        self.assertEqual(by_type["POINT_MACHINE_MAINT"]["assetType"], "POINT")
        self.assertEqual(by_type["TAMPING"]["assetType"], "TRACK_SECTION")

    def test_short_duration_error_names_the_floor_in_prose(self):
        response = self.client.post(
            "/api/v1/block-requests",
            headers=ENGG_HEADERS,
            json=base_payload(taskType="TAMPING", estimatedDuration=90),
        )
        self.assertEqual(response.status_code, 422)
        error = response.json()["error"]
        self.assertEqual(error["code"], "TASK_CONSTRAINT_INVALID")
        self.assertIn("at least 150 minutes", error["message"])
        self.assertNotIn("pydantic", error["message"].lower())
        self.assertEqual(error["details"]["minDurationMinutes"], 150)

    # --- constraints that used to escape as an uncaught pydantic ValidationError
    # and surface as a 500 with no error envelope the composer could read. ---

    def test_zero_length_km_range_is_a_field_error_not_a_500(self):
        # The composer permitted kmEnd == kmStart; BlockRequest's validator does not.
        response = self.client.post(
            "/api/v1/block-requests", headers=ENGG_HEADERS,
            json=base_payload(kmStart=2.0, kmEnd=2.0),
        )
        self.assertEqual(response.status_code, 422, response.text)
        error = response.json()["error"]
        self.assertEqual(error["code"], "KM_RANGE_INVALID")
        self.assertEqual(error["details"]["field"], "kmEnd")

    def test_duration_larger_than_requested_window_is_a_field_error(self):
        # TAMPING's 150-minute HC-002 floor inside a 120-minute window: both
        # values are individually legal, only their combination is not.
        response = self.client.post(
            "/api/v1/block-requests", headers=ENGG_HEADERS,
            json=base_payload(requestedStart=60, requestedEnd=180),
        )
        self.assertEqual(response.status_code, 422, response.text)
        error = response.json()["error"]
        self.assertEqual(error["code"], "DURATION_EXCEEDS_WINDOW")
        self.assertEqual(error["details"]["field"], "estimatedDuration")
        self.assertEqual(error["details"]["windowMinutes"], 120)

    def test_due_minute_before_window_end_is_a_field_error(self):
        response = self.client.post(
            "/api/v1/block-requests", headers=ENGG_HEADERS,
            json=base_payload(dueMinute=100),
        )
        self.assertEqual(response.status_code, 422, response.text)
        error = response.json()["error"]
        self.assertEqual(error["code"], "DUE_BEFORE_WINDOW_END")
        self.assertEqual(error["details"]["field"], "dueMinute")

    def test_every_rejection_carries_a_mappable_field(self):
        # errorDetails() in TicketComposer highlights the offending step from
        # details.field. A rejection without one leaves the operator with a
        # banner and no idea which of six steps to go back to.
        cases = [
            base_payload(kmStart=2.0, kmEnd=2.0),
            base_payload(requestedStart=60, requestedEnd=180),
            base_payload(dueMinute=100),
            base_payload(track="THIRD"),
            base_payload(kmStart=1.0, kmEnd=25.0, assetId="TRACK_SEC_GZB_DER_UP"),
            base_payload(taskType="POINT_MACHINE_MAINT"),
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                response = self.client.post("/api/v1/block-requests", headers=ENGG_HEADERS, json=payload)
                self.assertEqual(response.status_code, 422, response.text)
                details = response.json()["error"]["details"]
                self.assertIn("field", details, response.text)

    # --- role gating: the UI offers the composer to these roles, so the API
    # must accept them rather than 403 after six steps of form. ---

    def test_management_may_submit_a_ticket(self):
        response = self.client.post(
            "/api/v1/block-requests", headers=MANAGEMENT_HEADERS, json=base_payload(),
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "REQUESTED")

    def test_field_supervisor_with_a_department_may_submit(self):
        response = self.client.post(
            "/api/v1/block-requests", headers=SUPERVISOR_HEADERS, json=base_payload(),
        )
        self.assertEqual(response.status_code, 200, response.text)

    def test_field_supervisor_without_a_department_is_told_why(self):
        # A supervisor's department comes from their account, not their role.
        # An account created without one can never file a ticket, so the API
        # says so explicitly instead of failing an obscure scope check.
        response = self.client.post(
            "/api/v1/block-requests",
            headers={"X-RailOS-User": "sup-2", "X-RailOS-Role": "FIELD_SUPERVISOR"},
            json=base_payload(),
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "DEPARTMENT_SCOPE_REQUIRED")

    def test_network_sections_carry_the_km_bounds_the_server_enforces(self):
        # The composer cannot warn about chainage it was never told. These are
        # the same BlockSection bounds _validate_request_location rejects on.
        catalog = self.client.get("/api/v1/network/catalog", headers=ENGG_HEADERS)
        self.assertEqual(catalog.status_code, 200, catalog.text)
        by_id = {s["sectionId"]: s for s in catalog.json()["sections"]}
        self.assertIn("SEC_GZB_DER", by_id)
        self.assertEqual(by_id["SEC_GZB_DER"]["minKm"], 0)
        self.assertEqual(by_id["SEC_GZB_DER"]["maxKm"], 24)

        # And a request outside them is refused, so the two agree.
        rejected = self.client.post(
            "/api/v1/block-requests", headers=ENGG_HEADERS,
            json=base_payload(kmStart=1.0, kmEnd=25.0, assetId="TRACK_SEC_GZB_DER_UP"),
        )
        self.assertEqual(rejected.status_code, 422)
        self.assertEqual(rejected.json()["error"]["details"]["maxKm"], 24)

    def test_snake_case_body_is_rejected_with_a_readable_error(self):
        # BlockRequestCreate is populate_by_name=False, extra="forbid": a
        # snake_case body yields both "missing" and "extra" errors at once.
        response = self.client.post(
            "/api/v1/block-requests", headers=ENGG_HEADERS,
            json={
                "department": "ENGG", "section_id": "SEC_GZB_DER", "track": "UP",
                "km_start": 1.0, "km_end": 2.0, "task_type": "TAMPING", "severity": 5,
                "estimated_duration": 150, "requested_start": 60, "requested_end": 300,
            },
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "VALIDATION_ERROR")

    def test_get_detail_not_found(self):
        response = self.client.get("/api/v1/block-requests/REQ-DOES-NOT-EXIST", headers=ENGG_HEADERS)
        self.assertEqual(response.status_code, 404)

    def test_ticket_status_actions_are_authorized_and_audited(self):
        response = self.client.post("/api/v1/block-requests", headers=ENGG_HEADERS, json=base_payload())
        self.assertEqual(response.status_code, 200, response.text)
        request_id = response.json()["requestId"]
        self.assertEqual(response.json()["allowedActions"], ["CANCEL"])
        control_view = self.client.get(f"/api/v1/block-requests/{request_id}", headers=CONTROL_HEADERS)
        self.assertIn("ACCEPT", control_view.json()["allowedActions"])

        missing_reason = self.client.patch(
            f"/api/v1/block-requests/{request_id}/status", headers=CONTROL_HEADERS,
            json={"status": "READY", "reason": " "},
        )
        self.assertEqual(missing_reason.status_code, 422)
        self.assertEqual(missing_reason.json()["error"]["code"], "REASON_REQUIRED")

        accepted = self.client.patch(
            f"/api/v1/block-requests/{request_id}/status", headers=CONTROL_HEADERS,
            json={"status": "READY", "reason": "Control reviewed the request"},
        )
        self.assertEqual(accepted.status_code, 200, accepted.text)
        self.assertEqual(accepted.json()["status"], "READY")
        self.assertEqual(accepted.json()["allowedActions"], ["CANCEL"])
        self.assertTrue(any(event["type"] == "BLOCK_REQUEST_STATUS_UPDATED" and event["entityId"] == request_id for event in main.state.events))

        forbidden = self.client.patch(
            f"/api/v1/block-requests/{request_id}/status", headers=SNT_HEADERS,
            json={"status": "CANCELLED", "reason": "Wrong department"},
        )
        self.assertEqual(forbidden.status_code, 403)


if __name__ == "__main__":
    unittest.main()
