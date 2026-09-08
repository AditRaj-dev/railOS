"""Tests for Possession lifecycle, transitions, handback, safety gates, and block burst."""

import copy
from datetime import datetime, timedelta, timezone
import unittest
from fastapi.testclient import TestClient

from railos_api import main
from railos_model import (
    BlockType,
    CorrespondenceTest,
    Department,
    FormT351,
    MaintenanceTask,
    ObjectiveProfile,
    Plan,
    PlanStatus,
    PermitToWork,
    Possession,
    PossessionState,
    ProtectionRecord,
    ScheduledBlock,
    TaskStatus,
    TaskType,
    Track,
)

AUTH_ADMIN = {"X-RailOS-User": "admin-1", "X-RailOS-Role": "ADMIN"}
AUTH_CONTROL = {"X-RailOS-User": "controller-1", "X-RailOS-Role": "CONTROL_OFFICER"}
AUTH_TPC = {"X-RailOS-User": "tpc-1", "X-RailOS-Role": "TPC"}
AUTH_SM = {"X-RailOS-User": "sm-1", "X-RailOS-Role": "STATION_MASTER"}
AUTH_SNT = {"X-RailOS-User": "snt-1", "X-RailOS-Role": "SIGNAL_TELECOM"}
AUTH_ENGG = {"X-RailOS-User": "engg-sse", "X-RailOS-Role": "ENGINEERING"}
AUTH_SUPERVISOR = {"X-RailOS-User": "supervisor-1", "X-RailOS-Role": "FIELD_SUPERVISOR"}
AUTH_TRACTION = {"X-RailOS-User": "trd-gang-1", "X-RailOS-Role": "TRACTION"}


def create_full_possession(
    possession_id: str = "POS-TEST-01",
    state_val: PossessionState = PossessionState.SANCTIONED,
    requires_ptw: bool = True,
    requires_t351: bool = True,
    requires_corr: bool = True,
    planned_end_offset_min: int = 120,
) -> Possession:
    now = datetime.now(timezone.utc)
    p_start = (now - timedelta(minutes=30)).isoformat()
    p_end = (now + timedelta(minutes=planned_end_offset_min)).isoformat()

    return Possession(
        possessionId=possession_id,
        planId="PLAN-HB-01",
        planVersion=1,
        blockId="BLK-01",
        sectionId="SEC-GZB-ALJN",
        track=Track.DOWN,
        state=state_val,
        plannedStartUtc=p_start,
        plannedEndUtc=p_end,
        requiresPTW=requires_ptw,
        requiresT351=requires_t351,
        requiresCorrespondenceTest=requires_corr,
        assignedTaskIds=["TASK-HB-01"],
        department="TRD",
        createdAtUtc=p_start,
        updatedAtUtc=p_start,
    )


class PossessionHandbackTests(unittest.TestCase):
    def setUp(self):
        main.state = main.Repository()
        self.client = TestClient(main.app)

    def test_full_nine_stage_happy_path(self):
        """Execute 18 transitions from SANCTIONED to CLEARED end to end."""
        possession = create_full_possession("POS-HAPPY-01")
        main.state.possessions[possession.possessionId] = copy.deepcopy(possession)

        # 1. request-clearance (SANCTIONED -> CLEARANCE_REQUESTED)
        r1 = self.client.post(f"/api/v1/possessions/{possession.possessionId}/request-clearance", headers=AUTH_SUPERVISOR)
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()["state"], "CLEARANCE_REQUESTED")

        # 2. defer (CLEARANCE_REQUESTED -> DEFERRED)
        # The section controller has already reached the deferred handoff
        # window by the time this synthetic happy path grants clearance.
        r2 = self.client.post(f"/api/v1/possessions/{possession.possessionId}/defer", headers=AUTH_CONTROL, json={"deferredUntilUtc": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()})
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["state"], "DEFERRED")

        # 3. request-clearance (DEFERRED -> CLEARANCE_REQUESTED)
        r3 = self.client.post(f"/api/v1/possessions/{possession.possessionId}/request-clearance", headers=AUTH_SUPERVISOR)
        self.assertEqual(r3.status_code, 200)
        self.assertEqual(r3.json()["state"], "CLEARANCE_REQUESTED")

        # 4. grant-clearance (CLEARANCE_REQUESTED -> CLEARANCE_GRANTED)
        r4 = self.client.post(f"/api/v1/possessions/{possession.possessionId}/grant-clearance", headers=AUTH_CONTROL)
        self.assertEqual(r4.status_code, 200)
        self.assertEqual(r4.json()["state"], "CLEARANCE_GRANTED")

        # 5. start-isolation (CLEARANCE_GRANTED -> ISOLATION_IN_PROGRESS)
        r5 = self.client.post(f"/api/v1/possessions/{possession.possessionId}/start-isolation", headers=AUTH_SUPERVISOR)
        self.assertEqual(r5.status_code, 200)
        self.assertEqual(r5.json()["state"], "ISOLATION_IN_PROGRESS")

        # 6. issue-t351 (ISOLATION_IN_PROGRESS)
        r6 = self.client.post(f"/api/v1/possessions/{possession.possessionId}/issue-t351", headers=AUTH_SNT, json={"formReference": "T351-001", "note": "Signals disconnected"})
        self.assertEqual(r6.status_code, 200)
        self.assertEqual(r6.json()["formT351"]["status"], "ISSUED")

        # 7. endorse-t351 (ISOLATION_IN_PROGRESS by STATION_MASTER)
        r7 = self.client.post(f"/api/v1/possessions/{possession.possessionId}/endorse-t351", headers=AUTH_SM)
        self.assertEqual(r7.status_code, 200)
        self.assertEqual(r7.json()["formT351"]["status"], "ENDORSED")

        # 8. confirm-earthing (ISOLATION_IN_PROGRESS by TRACTION)
        r8 = self.client.post(f"/api/v1/possessions/{possession.possessionId}/confirm-earthing", headers=AUTH_TRACTION, json={"note": "Discharge rods planted at mast 12/4"})
        self.assertEqual(r8.status_code, 200)
        self.assertTrue(r8.json()["permitToWork"]["earthingConfirmed"])

        # 9. issue-ptw (ISOLATION_IN_PROGRESS by TPC)
        r9 = self.client.post(f"/api/v1/possessions/{possession.possessionId}/issue-ptw", headers=AUTH_TPC, json={"formReference": "ETR3-902"})
        self.assertEqual(r9.status_code, 200)
        self.assertEqual(r9.json()["permitToWork"]["status"], "ISSUED")

        # Simulate the statutory lead-in having elapsed before the field gang
        # enters the block.  The API now enforces this even when the request
        # omits clientEventAtUtc and therefore uses the server clock.
        issued_elapsed = datetime.now(timezone.utc)
        main.state.possessions[possession.possessionId].permitToWork.issuedAtUtc = (issued_elapsed - timedelta(minutes=25)).isoformat()
        main.state.possessions[possession.possessionId].formT351.issuedAtUtc = (issued_elapsed - timedelta(minutes=15)).isoformat()

        # 10. plant-protection (ISOLATION_IN_PROGRESS -> PROTECTED)
        r10 = self.client.post(f"/api/v1/possessions/{possession.possessionId}/plant-protection", headers=AUTH_ENGG, json={"detonatorCount": 3})
        self.assertEqual(r10.status_code, 200)
        self.assertEqual(r10.json()["state"], "PROTECTED")

        # 11. start-work (PROTECTED -> LIVE)
        r11 = self.client.post(f"/api/v1/possessions/{possession.possessionId}/start-work", headers=AUTH_SUPERVISOR)
        self.assertEqual(r11.status_code, 200)
        self.assertEqual(r11.json()["state"], "LIVE")

        # 12. declare-overrun (simulate planned end passed, LIVE -> OVERRUNNING)
        main.state.possessions[possession.possessionId].plannedEndUtc = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        r12 = self.client.post(f"/api/v1/possessions/{possession.possessionId}/declare-overrun", headers=AUTH_CONTROL)
        self.assertEqual(r12.status_code, 200)
        self.assertEqual(r12.json()["state"], "OVERRUNNING")

        # 13. start-testing (OVERRUNNING -> TESTING)
        r13 = self.client.post(f"/api/v1/possessions/{possession.possessionId}/start-testing", headers=AUTH_SNT)
        self.assertEqual(r13.status_code, 200)
        self.assertEqual(r13.json()["state"], "TESTING")

        # 14. record-correspondence-test (TESTING by SNT, >=30 min)
        r14 = self.client.post(f"/api/v1/possessions/{possession.possessionId}/record-correspondence-test", headers=AUTH_SNT, json={"durationMinutes": 35, "note": "Point 102 correspondence OK"})
        self.assertEqual(r14.status_code, 200)
        self.assertTrue(r14.json()["correspondenceTest"]["passed"])

        # 15. request-handback (TESTING -> HANDBACK_REQUESTED)
        r15 = self.client.post(f"/api/v1/possessions/{possession.possessionId}/request-handback", headers=AUTH_SUPERVISOR)
        self.assertEqual(r15.status_code, 200)
        self.assertEqual(r15.json()["state"], "HANDBACK_REQUESTED")

        # 16. remove-discharge-rods (HANDBACK_REQUESTED)
        r16 = self.client.post(f"/api/v1/possessions/{possession.possessionId}/remove-discharge-rods", headers=AUTH_TRACTION)
        self.assertEqual(r16.status_code, 200)
        self.assertTrue(r16.json()["permitToWork"]["dischargeRodsRemoved"])

        # 17. cancel-ptw (HANDBACK_REQUESTED by TPC)
        r17 = self.client.post(f"/api/v1/possessions/{possession.possessionId}/cancel-ptw", headers=AUTH_TPC)
        self.assertEqual(r17.status_code, 200)
        self.assertEqual(r17.json()["permitToWork"]["status"], "CANCELLED")

        # 18. S&T reconnects the endorsed Form T/351 before fitness is
        # certified, and TPC records live OHE re-energisation.
        r18a = self.client.post(f"/api/v1/possessions/{possession.possessionId}/reconnect-t351", headers=AUTH_SNT)
        self.assertEqual(r18a.status_code, 200)
        self.assertEqual(r18a.json()["formT351"]["status"], "RECONNECTED")
        r18b = self.client.post(f"/api/v1/possessions/{possession.possessionId}/re-energise", headers=AUTH_TPC)
        self.assertEqual(r18b.status_code, 200)
        self.assertTrue(r18b.json()["permitToWork"]["reEnergised"])

        # 19. certify-fitness (HANDBACK_REQUESTED -> FIT_CERTIFIED by ENGINEERING SSE)
        r18 = self.client.post(f"/api/v1/possessions/{possession.possessionId}/certify-fitness", headers=AUTH_ENGG, json={"tsrSpeedKmph": 45, "note": "Track packed and fit for 45 km/h"})
        self.assertEqual(r18.status_code, 200)
        self.assertEqual(r18.json()["state"], "FIT_CERTIFIED")

        # 20. station-close (FIT_CERTIFIED by STATION_MASTER)
        r19 = self.client.post(f"/api/v1/possessions/{possession.possessionId}/station-close", headers=AUTH_SM)
        self.assertEqual(r19.status_code, 200)
        self.assertTrue(r19.json()["stationClosed"])

        # 21. close (FIT_CERTIFIED -> CLEARED by CONTROL_OFFICER)
        r20 = self.client.post(f"/api/v1/possessions/{possession.possessionId}/close", headers=AUTH_CONTROL)
        self.assertEqual(r20.status_code, 200)
        self.assertEqual(r20.json()["state"], "CLEARED")

        # Verify block burst was generated because it overran
        burst_id = f"BST-{possession.possessionId}"
        self.assertIn(burst_id, main.state.block_bursts)
        burst = main.state.block_bursts[burst_id]
        self.assertTrue(burst.overrunMinutes > 0)

    def test_ptw_requires_tpc_and_earthing(self):
        possession = create_full_possession("POS-PTW-01", state_val=PossessionState.ISOLATION_IN_PROGRESS)
        main.state.possessions[possession.possessionId] = copy.deepcopy(possession)

        # 403 when ENGINEERING tries to issue PTW
        r_engg = self.client.post(f"/api/v1/possessions/{possession.possessionId}/issue-ptw", headers=AUTH_ENGG)
        self.assertEqual(r_engg.status_code, 403)

        # 409 when TPC tries to issue PTW before earthing confirmed
        r_tpc_no_earth = self.client.post(f"/api/v1/possessions/{possession.possessionId}/issue-ptw", headers=AUTH_TPC)
        self.assertEqual(r_tpc_no_earth.status_code, 409)

        # Confirm earthing
        self.client.post(f"/api/v1/possessions/{possession.possessionId}/confirm-earthing", headers=AUTH_TRACTION)

        # Now TPC can issue PTW
        r_ok = self.client.post(f"/api/v1/possessions/{possession.possessionId}/issue-ptw", headers=AUTH_TPC)
        self.assertEqual(r_ok.status_code, 200)
        self.assertEqual(r_ok.json()["permitToWork"]["status"], "ISSUED")

    def test_work_cannot_start_before_possession_is_live(self):
        possession = create_full_possession("POS-GATE-01", state_val=PossessionState.SANCTIONED)
        main.state.possessions[possession.possessionId] = copy.deepcopy(possession)

        assignment = {
            "id": "TASK-HB-01",
            "planId": "PLAN-HB-01",
            "planVersion": 1,
            "taskId": "TASK-HB-01",
            "blockId": "BLK-01",
            "status": "READY",
            "synthetic": True,
        }
        main.state.assignments["TASK-HB-01"] = assignment
        main.state.tasks["TASK-HB-01"] = MaintenanceTask(
            taskId="TASK-HB-01",
            department=Department.ENGG,
            assetId="A1",
            corridorId="C1",
            sectionId="SEC-GZB-ALJN",
            track=Track.DOWN,
            kmStart=1, kmEnd=2,
            taskType=TaskType.TAMPING,
            severity=5, criticality=5,
            dueMinute=100, estimatedDuration=60,
            status=TaskStatus.PENDING,
            blockType=BlockType.TRAFFIC,
        )

        # Attempt to mark STARTED while possession is still SANCTIONED
        res = self.client.post(
            "/api/v1/work/TASK-HB-01/update",
            headers=AUTH_SUPERVISOR,
            json={"status": "STARTED"},
        )
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["error"]["code"], "POSSESSION_NOT_LIVE")

        # Move possession to LIVE
        main.state.possessions[possession.possessionId].state = PossessionState.LIVE
        res_ok = self.client.post(
            "/api/v1/work/TASK-HB-01/update",
            headers=AUTH_SUPERVISOR,
            json={"status": "STARTED"},
        )
        self.assertEqual(res_ok.status_code, 200)
        self.assertEqual(res_ok.json()["status"], "STARTED")

    def test_offline_replay_allowed_for_field_acts_only(self):
        possession = create_full_possession("POS-OFFLINE-01", state_val=PossessionState.ISOLATION_IN_PROGRESS)
        # Endorse T351 and confirm earthing
        possession.formT351 = None
        possession.requiresT351 = False
        possession.requiresPTW = False
        main.state.possessions[possession.possessionId] = copy.deepcopy(possession)

        # Online-only action (e.g. grant-clearance, issue-ptw, cancel-ptw) sent with replay header -> 409
        r_online = self.client.post(
            f"/api/v1/possessions/{possession.possessionId}/issue-ptw",
            headers=AUTH_TPC | {"X-RailOS-Offline-Replay": "true"},
        )
        self.assertEqual(r_online.status_code, 409)
        self.assertEqual(r_online.json()["error"]["code"], "ONLINE_AUTHORITY_REQUIRED")

        # Replayable field act (plant-protection) -> 200 OK
        r_field = self.client.post(
            f"/api/v1/possessions/{possession.possessionId}/plant-protection",
            headers=AUTH_SUPERVISOR | {"X-RailOS-Offline-Replay": "true"},
            json={"detonatorCount": 3},
        )
        self.assertEqual(r_field.status_code, 200)
        self.assertEqual(r_field.json()["state"], "PROTECTED")

    def test_overrun_declares_block_burst_once(self):
        possession = create_full_possession("POS-BURST-01", state_val=PossessionState.FIT_CERTIFIED, requires_ptw=False)
        possession.stationClosed = True
        possession.plannedEndUtc = (datetime.now(timezone.utc) - timedelta(minutes=25)).isoformat()
        main.state.possessions[possession.possessionId] = copy.deepcopy(possession)

        # 1. Close possession
        r1 = self.client.post(f"/api/v1/possessions/{possession.possessionId}/close", headers=AUTH_CONTROL)
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()["state"], "CLEARED")
        self.assertEqual(len(main.state.block_bursts), 1)

        # 2. Replay close -> natural idempotency returns 200 with replayed=True, exactly 1 burst remains
        r2 = self.client.post(f"/api/v1/possessions/{possession.possessionId}/close", headers=AUTH_CONTROL)
        self.assertEqual(r2.status_code, 200)
        self.assertTrue(r2.json().get("replayed", False))
        self.assertEqual(len(main.state.block_bursts), 1)

    def test_deferral_count_capped_at_three(self):
        possession = create_full_possession("POS-DEF-01", state_val=PossessionState.CLEARANCE_REQUESTED)
        main.state.possessions[possession.possessionId] = copy.deepcopy(possession)

        # Defer 1
        self.client.post(f"/api/v1/possessions/{possession.possessionId}/defer", headers=AUTH_CONTROL)
        self.client.post(f"/api/v1/possessions/{possession.possessionId}/request-clearance", headers=AUTH_SUPERVISOR)

        # Defer 2
        self.client.post(f"/api/v1/possessions/{possession.possessionId}/defer", headers=AUTH_CONTROL)
        self.client.post(f"/api/v1/possessions/{possession.possessionId}/request-clearance", headers=AUTH_SUPERVISOR)

        # Defer 3
        self.client.post(f"/api/v1/possessions/{possession.possessionId}/defer", headers=AUTH_CONTROL)
        self.client.post(f"/api/v1/possessions/{possession.possessionId}/request-clearance", headers=AUTH_SUPERVISOR)

        # 4th deferral should be rejected with 409
        r4 = self.client.post(f"/api/v1/possessions/{possession.possessionId}/defer", headers=AUTH_CONTROL)
        self.assertEqual(r4.status_code, 409)

    def test_correspondence_test_minimum_duration(self):
        possession = create_full_possession("POS-CORR-01", state_val=PossessionState.TESTING)
        main.state.possessions[possession.possessionId] = copy.deepcopy(possession)

        # Test duration 25 min (< 30 min) -> 422 TEST_TOO_SHORT
        r_short = self.client.post(
            f"/api/v1/possessions/{possession.possessionId}/record-correspondence-test",
            headers=AUTH_SNT,
            json={"durationMinutes": 25},
        )
        self.assertEqual(r_short.status_code, 422)
        self.assertEqual(r_short.json()["error"]["code"], "TEST_TOO_SHORT")

        # Test duration 30 min -> 200 OK
        r_ok = self.client.post(
            f"/api/v1/possessions/{possession.possessionId}/record-correspondence-test",
            headers=AUTH_SNT,
            json={"durationMinutes": 30},
        )
        self.assertEqual(r_ok.status_code, 200)

    def test_lazy_sweeper_detects_overrun(self):
        possession = create_full_possession("POS-SWEEP-01", state_val=PossessionState.LIVE)
        possession.plannedEndUtc = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        main.state.possessions[possession.possessionId] = copy.deepcopy(possession)

        # GET /api/v1/possessions triggers lazy sweeper
        res = self.client.get("/api/v1/possessions", headers=AUTH_CONTROL)
        self.assertEqual(res.status_code, 200)

        # Target possession should now be OVERRUNNING
        updated = main.state.possessions[possession.possessionId]
        self.assertEqual(updated.state, PossessionState.OVERRUNNING)

    def test_fitness_requires_t351_reconnect(self):
        """An endorsed disconnection is not evidence that S&T reconnected it."""
        now = datetime.now(timezone.utc)
        possession = create_full_possession("POS-RECONNECT-01", state_val=PossessionState.HANDBACK_REQUESTED)
        possession.formT351 = FormT351(
            formNumber="T351-RECONNECT-01",
            sectionId=possession.sectionId,
            track=possession.track,
            issuedBy="snt-1",
            issuedAtUtc=(now - timedelta(minutes=30)).isoformat(),
            endorsedBy="sm-1",
            endorsedAtUtc=(now - timedelta(minutes=20)).isoformat(),
            status="ENDORSED",
        )
        possession.permitToWork = PermitToWork(
            ptwNumber="ETR3-RECONNECT-01",
            oheSection=possession.sectionId,
            isolatorNumber="ISO-01",
            issuedBy="tpc-1",
            issuedAtUtc=(now - timedelta(minutes=45)).isoformat(),
            earthingConfirmed=True,
            dischargeRodsRemoved=True,
            status="CANCELLED",
            reEnergised=True,
            reEnergisedBy="tpc-1",
            reEnergisedAtUtc=(now - timedelta(minutes=5)).isoformat(),
        )
        possession.protectionRecord = ProtectionRecord(
            bannerFlagsPlaced=True,
            detonatorCount=3,
            handSignalPosted=True,
            plantedBy="engg-sse",
            plantedAtUtc=(now - timedelta(hours=1)).isoformat(),
        )
        possession.correspondenceTest = CorrespondenceTest(
            testId="TEST-RECONNECT-01",
            testedBy="snt-1",
            startAtUtc=(now - timedelta(minutes=40)).isoformat(),
            completedAtUtc=(now - timedelta(minutes=10)).isoformat(),
            durationMinutes=30,
        )
        main.state.possessions[possession.possessionId] = copy.deepcopy(possession)

        before_reconnect = self.client.post(
            f"/api/v1/possessions/{possession.possessionId}/certify-fitness",
            headers=AUTH_ENGG,
            json={"tsrSpeedKmph": 20},
        )
        self.assertEqual(before_reconnect.status_code, 409)
        self.assertIn("reconnected", before_reconnect.json()["error"]["message"])

        reconnect = self.client.post(
            f"/api/v1/possessions/{possession.possessionId}/reconnect-t351",
            headers=AUTH_SNT,
        )
        self.assertEqual(reconnect.status_code, 200)
        self.assertEqual(reconnect.json()["formT351"]["status"], "RECONNECTED")
        self.assertEqual(reconnect.json()["formT351"]["reconnectedBy"], "snt-1")

        certified = self.client.post(
            f"/api/v1/possessions/{possession.possessionId}/certify-fitness",
            headers=AUTH_ENGG,
            json={"tsrSpeedKmph": 20},
        )
        self.assertEqual(certified.status_code, 200)

    def test_start_work_requires_server_lead_in_without_client_timestamp(self):
        """Omitting the field clock must not bypass PTW's 20-minute lead-in."""
        now = datetime.now(timezone.utc)
        possession = create_full_possession(
            "POS-LEAD-IN-01",
            state_val=PossessionState.PROTECTED,
            requires_ptw=True,
            requires_t351=False,
            requires_corr=False,
        )
        possession.permitToWork = PermitToWork(
            ptwNumber="ETR3-LEAD-IN-01",
            oheSection=possession.sectionId,
            isolatorNumber="ISO-01",
            issuedBy="tpc-1",
            issuedAtUtc=now.isoformat(),
            earthingConfirmed=True,
            status="ISSUED",
        )
        possession.protectionRecord = ProtectionRecord(
            bannerFlagsPlaced=True,
            detonatorCount=3,
            handSignalPosted=True,
            plantedBy="engg-sse",
            plantedAtUtc=now.isoformat(),
        )
        main.state.possessions[possession.possessionId] = copy.deepcopy(possession)

        before = self.client.get(
            f"/api/v1/possessions/{possession.possessionId}",
            headers=AUTH_SUPERVISOR,
        )
        self.assertNotIn("start-work", before.json()["allowedActions"])
        blocked = self.client.post(
            f"/api/v1/possessions/{possession.possessionId}/start-work",
            headers=AUTH_SUPERVISOR,
        )
        self.assertEqual(blocked.status_code, 409)
        self.assertIn("lead-in", blocked.json()["error"]["message"])

        main.state.possessions[possession.possessionId].permitToWork.issuedAtUtc = (
            now - timedelta(minutes=21)
        ).isoformat()
        after = self.client.get(
            f"/api/v1/possessions/{possession.possessionId}",
            headers=AUTH_SUPERVISOR,
        )
        self.assertIn("start-work", after.json()["allowedActions"])
        started = self.client.post(
            f"/api/v1/possessions/{possession.possessionId}/start-work",
            headers=AUTH_SUPERVISOR,
        )
        self.assertEqual(started.status_code, 200)

    def test_grant_clearance_honours_day_deferred_window_and_occupied_states(self):
        now = datetime.now(timezone.utc)
        possession = create_full_possession("POS-CLEARANCE-GATES-01", state_val=PossessionState.CLEARANCE_REQUESTED)
        possession.plannedStartUtc = (now + timedelta(days=1)).isoformat()
        possession.plannedEndUtc = (now + timedelta(days=1, minutes=120)).isoformat()
        main.state.possessions[possession.possessionId] = copy.deepcopy(possession)

        not_day_of = self.client.post(
            f"/api/v1/possessions/{possession.possessionId}/grant-clearance",
            headers=AUTH_CONTROL,
        )
        self.assertEqual(not_day_of.status_code, 409)
        self.assertIn("planned operating day", not_day_of.json()["error"]["message"])

        p = main.state.possessions[possession.possessionId]
        p.plannedStartUtc = (now - timedelta(minutes=30)).isoformat()
        p.plannedEndUtc = (now + timedelta(minutes=120)).isoformat()
        p.deferredUntilUtc = (now + timedelta(minutes=15)).isoformat()
        deferred = self.client.post(
            f"/api/v1/possessions/{possession.possessionId}/grant-clearance",
            headers=AUTH_CONTROL,
        )
        self.assertEqual(deferred.status_code, 409)
        self.assertIn("deferred", deferred.json()["error"]["message"])

        p.deferredUntilUtc = (now - timedelta(minutes=1)).isoformat()
        conflicting = create_full_possession("POS-CLEARANCE-GATES-02", state_val=PossessionState.HANDBACK_REQUESTED)
        conflicting.plannedStartUtc = p.plannedStartUtc
        conflicting.plannedEndUtc = p.plannedEndUtc
        main.state.possessions[conflicting.possessionId] = conflicting
        conflict = self.client.post(
            f"/api/v1/possessions/{possession.possessionId}/grant-clearance",
            headers=AUTH_CONTROL,
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertIn("Conflicting possession", conflict.json()["error"]["message"])

    def test_reenergise_is_typed_idempotent_and_required_for_close(self):
        now = datetime.now(timezone.utc)
        possession = create_full_possession("POS-REENERGISE-01", state_val=PossessionState.HANDBACK_REQUESTED)
        possession.permitToWork = PermitToWork(
            ptwNumber="ETR3-REENERGISE-01",
            oheSection=possession.sectionId,
            isolatorNumber="ISO-01",
            issuedBy="tpc-1",
            issuedAtUtc=(now - timedelta(minutes=45)).isoformat(),
            earthingConfirmed=True,
            dischargeRodsRemoved=True,
            status="CANCELLED",
        )
        main.state.possessions[possession.possessionId] = copy.deepcopy(possession)

        p = main.state.possessions[possession.possessionId]
        p.state = PossessionState.FIT_CERTIFIED
        p.stationClosed = True
        blocked_close = self.client.post(
            f"/api/v1/possessions/{possession.possessionId}/close",
            headers=AUTH_CONTROL,
        )
        self.assertEqual(blocked_close.status_code, 409)
        p.state = PossessionState.HANDBACK_REQUESTED
        p.stationClosed = False

        first = self.client.post(
            f"/api/v1/possessions/{possession.possessionId}/re-energise",
            headers=AUTH_TPC,
        )
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.json()["permitToWork"]["reEnergised"])
        transitions_after_first = len(main.state.possessions[possession.possessionId].transitions)

        second = self.client.post(
            f"/api/v1/possessions/{possession.possessionId}/re-energise",
            headers=AUTH_TPC,
        )
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json()["replayed"])
        self.assertEqual(len(main.state.possessions[possession.possessionId].transitions), transitions_after_first)

        p = main.state.possessions[possession.possessionId]
        p.state = PossessionState.FIT_CERTIFIED
        p.stationClosed = True
        closed = self.client.post(
            f"/api/v1/possessions/{possession.possessionId}/close",
            headers=AUTH_CONTROL,
        )
        self.assertEqual(closed.status_code, 200)


if __name__ == "__main__":
    unittest.main()
