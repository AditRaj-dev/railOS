"""End-to-end proof of the complete RailOS ticket-to-evidence chain against
the real FastAPI app (TestClient, no mocks), covering all nine lifecycle
stages:

  1. Department ticket creation (POST /api/v1/block-requests) -> linked
     maintenance task (TKT-*)
  2. Optimizer time-block plan generation (POST /api/v1/optimization/generate)
     -- the ticket-derived task must appear either in a plan's assignments or
     in an explicit unassigned/warning list (no specific time is asserted)
  3. Sanction chain (role-based signatures via /api/v1/block-plans/{id}/
     approve, a convenience alias for /sanctions) until the plan is APPROVED
     and a possession is materialised
  4. Possession lifecycle transitions (convenience POST aliases:
     request-clearance, grant-clearance, plant-protection, start-work) up to
     LIVE
  5. Field work: POST /api/v1/work/{taskId}/update with status STARTED --
     rejected 409 POSSESSION_NOT_LIVE before the possession is LIVE, and
     accepted once it is
  6. Real JWT auth (POST /api/v1/auth/login) for the field supervisor
  7. Evidence upload: multipart initiate/presign/complete against the
     ticket-derived task's work step
  8. Evidence finalize (POST /api/v1/evidence/{id}:finalize) producing
     VERIFIED
  9. Terminal state assertion on the VERIFIED evidence record (control-officer
     review is exercised only if evidence comes back FLAGGED_REVIEW)

The synthetic X-RailOS-User/X-RailOS-Role headers authorize the ticket,
optimizer, sanction, possession, and work-assignment routes in main.py; the
evidence_routes.py router is a separate auth surface that requires a real
bearer JWT obtained from /api/v1/auth/login. This test carries both kinds of
credentials, using each where the corresponding router demands it.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT / "apps" / "api"),
    str(ROOT / "packages" / "railos_model"),
    str(ROOT / "packages" / "shared"),
    str(ROOT / "packages" / "optimizer"),
    str(ROOT),
]

import unittest
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from railos_api import main
from railos_api.evidence_routes import object_store
from railos_api.storage import MemoryObjectStore
from railos_model import compute_sha256_bytes

# --- Synthetic header credentials for main.py's ticket/plan/possession/work routes ---
ENGG_HEADERS = {"X-RailOS-User": "engg-1", "X-RailOS-Role": "ENGINEERING"}
CONTROL_HEADERS = {"X-RailOS-User": "control-1", "X-RailOS-Role": "CONTROL_OFFICER"}

# --- Seed account used to obtain a real JWT for the evidence_routes.py auth surface ---
FIELD_SUPERVISOR_EMPLOYEE_ID = "EMP901"
FIELD_SUPERVISOR_PASSWORD = "Field@123"


def ticket_payload(**overrides):
    payload = {
        "department": "ENGG",
        "corridorId": "GZB-ALJN",
        "sectionId": "SEC_KRJ_SMQ",
        "track": "UP",
        "kmStart": 60.0,
        "kmEnd": 62.0,
        "taskType": "TAMPING",
        "severity": 5,
        "estimatedDuration": 150,
        "requestedStart": 60,
        "requestedEnd": 300,
        "blockType": "TRAFFIC",
    }
    payload.update(overrides)
    return payload


class TicketToEvidenceE2ETests(unittest.TestCase):
    """One continuous chain, stage by stage, with a stage-labelled assertion
    at each leg so a failure identifies exactly which part of the chain broke."""

    def setUp(self):
        main.state = main.Repository()
        self.client = TestClient(main.app)

    def test_full_ticket_to_evidence_chain(self):
        # ------------------------------------------------------------------
        # Stage 1: Department ticket creation -> linked maintenance task
        # ------------------------------------------------------------------
        ticket_res = self.client.post(
            "/api/v1/block-requests", headers=ENGG_HEADERS, json=ticket_payload()
        )
        self.assertEqual(ticket_res.status_code, 200, f"[stage1] ticket creation failed: {ticket_res.text}")
        ticket_body = ticket_res.json()
        self.assertEqual(ticket_body["status"], "REQUESTED", "[stage1] ticket should start REQUESTED")
        task_id = ticket_body["linkedTaskId"]
        self.assertTrue(task_id.startswith("TKT-"), f"[stage1] linked task id malformed: {task_id}")
        self.assertIsNotNone(ticket_body["linkedTask"], "[stage1] ticket must carry the linked task payload")
        self.assertEqual(ticket_body["linkedTask"]["assetId"], "TRACK_SEC_KRJ_SMQ_UP", "[stage1] asset resolution mismatch")

        tasks_res = self.client.get("/api/v1/maintenance/tasks", headers=ENGG_HEADERS)
        task_ids = [t["taskId"] for t in tasks_res.json()["items"]]
        self.assertIn(task_id, task_ids, "[stage1] linked task must be visible via maintenance/tasks")

        # ------------------------------------------------------------------
        # Stage 2: Optimizer time-block plan generation -- linkage only,
        # never a specific time
        # ------------------------------------------------------------------
        opt_res = self.client.post(
            "/api/v1/optimization/generate",
            headers=CONTROL_HEADERS,
            json={"taskIds": [task_id], "objective": "BALANCED"},
        )
        self.assertEqual(opt_res.status_code, 200, f"[stage2] optimizer generate failed: {opt_res.text}")
        opt_body = opt_res.json()
        candidate_plans = opt_body["candidatePlans"]
        self.assertTrue(candidate_plans, "[stage2] optimizer must return at least one candidate plan")

        chosen_plan = None
        chosen_block_id = None
        for plan in candidate_plans:
            for assignment in plan.get("assignments", []):
                if assignment["taskId"] == task_id:
                    chosen_plan = plan
                    chosen_block_id = assignment["blockId"]
                    break
            if chosen_plan:
                break

        if chosen_plan is None:
            # Task was not scheduled by any candidate -- it must be visible
            # as an explicit unassigned/warning signal instead of silently
            # vanishing from the plan.
            warnings_text = " ".join(opt_body.get("warnings", []))
            self.assertIn(
                task_id,
                warnings_text,
                f"[stage2] task {task_id} missing from every plan's assignments AND from warnings: {warnings_text}",
            )
            self.fail(
                "[stage2] optimizer only surfaced the ticket-derived task as an unassigned "
                "warning; no plan could be carried forward to the sanction stage -- this test "
                "requires at least one candidate to schedule the task so the remaining stages "
                "(3-9) can run against a materialised possession."
            )
        self.assertIsNotNone(chosen_block_id, "[stage2] chosen plan must name the assigned block")

        # The optimizer places maintenance in the night traffic windows, so a
        # plan generated at any real wall-clock time describes a window that
        # has already closed, and grant-clearance rightly refuses it
        # (CLEARANCE_NOT_DAY_OF / CLEARANCE_WINDOW_EXPIRED). Re-anchor the
        # horizon epoch so the chosen block straddles *now* -- possessions
        # take plannedStart/EndUtc from this epoch at approval time, so the
        # day-of and window-expiry guards are still genuinely exercised,
        # against a window that is legitimately open.
        chosen_block = next(b for b in chosen_plan["blocks"] if b["blockId"] == chosen_block_id)
        main.state.horizon_start_iso = (
            datetime.now(timezone.utc) - timedelta(minutes=chosen_block["start"] + 2)
        ).isoformat()

        # ------------------------------------------------------------------
        # Stage 3: Sanction chain -> APPROVED plan -> possession materialised
        # ------------------------------------------------------------------
        plan_id = chosen_plan["planId"]

        sanctions_res = self.client.get(f"/api/v1/block-plans/{plan_id}/sanctions", headers=CONTROL_HEADERS)
        self.assertEqual(sanctions_res.status_code, 200, "[stage3] could not read sanction chain")
        required_authorities = sanctions_res.json()["requiredAuthorities"]
        self.assertIn(
            "SECTION_CONTROL", required_authorities,
            "[stage3] a TRAFFIC/TAMPING block must always require SECTION_CONTROL sanction",
        )

        approve_res = self.client.post(
            f"/api/v1/block-plans/{plan_id}/approve",
            headers=CONTROL_HEADERS,
            json={"reason": "Section Controller clears the tamping block"},
        )
        self.assertEqual(approve_res.status_code, 200, f"[stage3] plan approval failed: {approve_res.text}")
        approved_plan = approve_res.json()
        self.assertEqual(approved_plan["status"], "APPROVED", "[stage3] plan must reach APPROVED once the chain completes")

        self.assertIn(task_id, main.state.assignments, "[stage3] task must be materialised into a runtime assignment")

        possession_id = f"POS-{chosen_block_id}"
        self.assertIn(possession_id, main.state.possessions, "[stage3] approval must materialise a possession")
        possession = main.state.possessions[possession_id]
        self.assertEqual(possession.state.value, "SANCTIONED", "[stage3] a fresh possession starts SANCTIONED")
        self.assertFalse(possession.requiresPTW, "[stage3] TAMPING carries no PTW requirement")
        self.assertFalse(possession.requiresT351, "[stage3] TAMPING carries no Form T/351 requirement")

        # ------------------------------------------------------------------
        # Stage 5 (asserted early, deliberately, before stage 4): field work
        # must be rejected while the possession is not yet LIVE. This is the
        # key safety gate this test exists to prove.
        # ------------------------------------------------------------------
        blocked_start = self.client.post(
            f"/api/v1/work/{task_id}/update",
            headers=ENGG_HEADERS,
            json={"status": "STARTED"},
        )
        self.assertEqual(blocked_start.status_code, 409, "[stage5-pre] work must not start before possession is LIVE")
        self.assertEqual(
            blocked_start.json()["error"]["code"], "POSSESSION_NOT_LIVE",
            "[stage5-pre] rejection must carry the POSSESSION_NOT_LIVE code",
        )

        # ------------------------------------------------------------------
        # Stage 4: Possession lifecycle transitions up to LIVE
        # ------------------------------------------------------------------
        clearance_res = self.client.post(
            f"/api/v1/possessions/{possession_id}/request-clearance", headers=ENGG_HEADERS
        )
        self.assertEqual(clearance_res.status_code, 200, f"[stage4] request-clearance failed: {clearance_res.text}")
        self.assertEqual(clearance_res.json()["state"], "CLEARANCE_REQUESTED", "[stage4] expected CLEARANCE_REQUESTED")

        grant_res = self.client.post(
            f"/api/v1/possessions/{possession_id}/grant-clearance", headers=CONTROL_HEADERS
        )
        self.assertEqual(grant_res.status_code, 200, f"[stage4] grant-clearance failed: {grant_res.text}")
        self.assertEqual(grant_res.json()["state"], "CLEARANCE_GRANTED", "[stage4] expected CLEARANCE_GRANTED")

        protect_res = self.client.post(
            f"/api/v1/possessions/{possession_id}/plant-protection",
            headers=ENGG_HEADERS,
            json={"detonatorCount": 3},
        )
        self.assertEqual(protect_res.status_code, 200, f"[stage4] plant-protection failed: {protect_res.text}")
        self.assertEqual(protect_res.json()["state"], "PROTECTED", "[stage4] expected PROTECTED")

        live_res = self.client.post(
            f"/api/v1/possessions/{possession_id}/start-work", headers=ENGG_HEADERS
        )
        self.assertEqual(live_res.status_code, 200, f"[stage4] start-work failed: {live_res.text}")
        self.assertEqual(live_res.json()["state"], "LIVE", "[stage4] possession must reach LIVE")

        # ------------------------------------------------------------------
        # Stage 5 (post): field work must now succeed
        # ------------------------------------------------------------------
        started_res = self.client.post(
            f"/api/v1/work/{task_id}/update",
            headers=ENGG_HEADERS,
            json={"status": "STARTED"},
        )
        self.assertEqual(started_res.status_code, 200, f"[stage5-post] work start failed once LIVE: {started_res.text}")
        self.assertEqual(started_res.json()["status"], "STARTED", "[stage5-post] assignment must reflect STARTED")

        # ------------------------------------------------------------------
        # Stage 6: Real JWT auth for the field supervisor
        # ------------------------------------------------------------------
        login_res = self.client.post(
            "/api/v1/auth/login",
            json={"employeeId": FIELD_SUPERVISOR_EMPLOYEE_ID, "password": FIELD_SUPERVISOR_PASSWORD},
        )
        self.assertEqual(login_res.status_code, 200, f"[stage6] login failed: {login_res.text}")
        token_data = login_res.json()
        self.assertEqual(token_data["role"], "SUPERVISOR", "[stage6] EMP901 must log in as SUPERVISOR")
        access_token = token_data["accessToken"]
        auth_header = {"Authorization": f"Bearer {access_token}"}

        me_res = self.client.get("/api/v1/me", headers=auth_header)
        self.assertEqual(me_res.status_code, 200, "[stage6] /me must accept the freshly issued JWT")
        self.assertEqual(me_res.json()["employeeId"], FIELD_SUPERVISOR_EMPLOYEE_ID)

        # Pull the ENGG-department "mine" assignments so the ticket-derived
        # task gets its default work steps auto-provisioned (evidence_routes
        # lazily creates them the first time a supervisor's own tasks are
        # listed), giving us a real step_id to attach evidence to.
        mine_res = self.client.get("/api/v1/work/assignments/mine", headers=auth_header)
        self.assertEqual(mine_res.status_code, 200, f"[stage6] work/assignments/mine failed: {mine_res.text}")
        mine_tasks = {t["taskId"]: t for t in mine_res.json()["tasks"]}
        self.assertIn(task_id, mine_tasks, "[stage6] ticket-derived task must appear in the ENGG supervisor's own work list")
        steps = mine_tasks[task_id]["steps"]
        self.assertGreaterEqual(len(steps), 1, "[stage6] task must have at least one work step for evidence capture")
        step_id = steps[0]["stepId"]
        target_lat = steps[0]["targetLatitude"]
        target_lon = steps[0]["targetLongitude"]

        # ------------------------------------------------------------------
        # Stage 7: Evidence upload -- multipart initiate/presign/complete
        # ------------------------------------------------------------------
        evidence_id = "018e9999-1111-7000-8000-999900001111"
        create_evidence_res = self.client.post(
            "/api/v1/evidence",
            headers=auth_header,
            json={
                "evidenceId": evidence_id,
                "taskId": task_id,
                "stepId": step_id,
                "kind": "PHOTO",
                "captureTimeUtc": "2026-09-09T10:00:00Z",
                "startLatitude": target_lat + 0.00003,  # a few metres off target, within radius
                "startLongitude": target_lon + 0.00003,
                "gpsAccuracyMeters": 8.0,
            },
        )
        self.assertEqual(create_evidence_res.status_code, 200, f"[stage7] evidence record creation failed: {create_evidence_res.text}")
        self.assertEqual(create_evidence_res.json()["status"], "UPLOAD_PENDING", "[stage7] new evidence must be UPLOAD_PENDING")

        dummy_jpeg = b"\xff\xd8\xff\xe0" + (b"E2E_TICKET_TO_EVIDENCE_CHAIN" * 80)
        original_sha256 = compute_sha256_bytes(dummy_jpeg)

        initiate_res = self.client.post(
            f"/api/v1/evidence/{evidence_id}/uploads/initiate",
            headers=auth_header,
            json={
                "storageKind": "ORIGINAL",
                "totalBytes": len(dummy_jpeg),
                "contentType": "image/jpeg",
                "partSizeBytes": len(dummy_jpeg),
            },
        )
        self.assertEqual(initiate_res.status_code, 200, f"[stage7] upload initiate failed: {initiate_res.text}")
        session_id = initiate_res.json()["sessionId"]
        upload_id = initiate_res.json()["uploadId"]

        presign_res = self.client.post(
            f"/api/v1/evidence/{evidence_id}/uploads/parts/1/presign?sessionId={session_id}",
            headers=auth_header,
        )
        self.assertEqual(presign_res.status_code, 200, f"[stage7] presign failed: {presign_res.text}")
        self.assertIn("uploadUrl", presign_res.json(), "[stage7] presign response must carry an uploadUrl")

        self.assertIsInstance(object_store, MemoryObjectStore, "[stage7] test relies on the in-memory object store")
        etag = object_store.put_multipart_part(upload_id, 1, dummy_jpeg)

        complete_res = self.client.post(
            f"/api/v1/evidence/{evidence_id}/uploads/complete",
            headers=auth_header,
            json={
                "sessionId": session_id,
                "storageKind": "ORIGINAL",
                "parts": [{"partNumber": 1, "etag": etag}],
                "sha256": original_sha256,
                "sizeBytes": len(dummy_jpeg),
            },
        )
        self.assertEqual(complete_res.status_code, 200, f"[stage7] upload complete failed: {complete_res.text}")

        # ------------------------------------------------------------------
        # Stage 8: Evidence finalize -> VERIFIED (or FLAGGED_REVIEW)
        # ------------------------------------------------------------------
        finalize_res = self.client.post(
            f"/api/v1/evidence/{evidence_id}:finalize",
            headers=auth_header,
            json={
                "locationSamples": [
                    {
                        "timestampUtc": "2026-09-09T10:00:00Z",
                        "latitude": target_lat + 0.00003,
                        "longitude": target_lon + 0.00003,
                        "accuracyMeters": 8.0,
                        "isMocked": False,
                    }
                ],
                "deviceInfo": {"model": "E2E Test Device", "os": "Test OS"},
            },
        )
        self.assertEqual(finalize_res.status_code, 202, f"[stage8] finalize failed: {finalize_res.text}")
        finalized = finalize_res.json()
        self.assertIn(
            finalized["status"], {"VERIFIED", "FLAGGED_REVIEW"},
            f"[stage8] unexpected terminal verification status: {finalized['status']}",
        )

        # ------------------------------------------------------------------
        # Stage 9: Control-officer review if flagged, else assert VERIFIED
        # terminal state directly
        # ------------------------------------------------------------------
        if finalized["status"] == "FLAGGED_REVIEW":
            admin_login = self.client.post(
                "/api/v1/auth/login",
                json={"employeeId": "EMP001", "password": "Admin@123"},
            )
            self.assertEqual(admin_login.status_code, 200, "[stage9] admin login failed for flagged-evidence review")
            admin_token = admin_login.json()["accessToken"]

            review_res = self.client.post(
                f"/api/v1/evidence/{evidence_id}:review",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"decision": "ACCEPT", "reviewNotes": "E2E test: accepting flagged capture"},
            )
            self.assertEqual(review_res.status_code, 200, f"[stage9] review failed: {review_res.text}")
            self.assertEqual(
                review_res.json()["status"], "ACCEPTED_EXCEPTION",
                "[stage9] a reviewed, accepted evidence item must reach ACCEPTED_EXCEPTION",
            )
        else:
            self.assertEqual(finalized["status"], "VERIFIED", "[stage9] evidence must reach VERIFIED terminal state")
            self.assertIsNotNone(finalized.get("ed25519Signature"), "[stage9] VERIFIED evidence must be signed")
            self.assertIsNotNone(finalized.get("canonicalManifest"), "[stage9] VERIFIED evidence must carry a canonical manifest")

            step = main.state.work_steps[step_id]
            self.assertEqual(step.status, "COMPLETED", "[stage9] the work step must be marked COMPLETED once evidence is VERIFIED")


if __name__ == "__main__":
    unittest.main()
