"""Tests for the possession authority chain, sanctioning, and role vocabulary."""

import copy
import unittest
from fastapi.testclient import TestClient

from railos_api import main
from railos_api.roles import OPERATIONAL_ROLES, normalize_role
from railos_model import (
    Assignment,
    BlockType,
    Department,
    MaintenanceTask,
    ObjectiveProfile,
    Plan,
    PlanStatus,
    PossessionState,
    SanctionAuthority,
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
AUTH_ENGG = {"X-RailOS-User": "engg-1", "X-RailOS-Role": "ENGINEERING"}
AUTH_MGMT = {"X-RailOS-User": "srdom-1", "X-RailOS-Role": "MANAGEMENT"}
AUTH_SUPERVISOR = {"X-RailOS-User": "sup-1", "X-RailOS-Role": "FIELD_SUPERVISOR"}


def create_test_plan(
    plan_id: str = "PLAN-AUTH-01",
    block_type: BlockType = BlockType.TRAFFIC,
    start: int = 60,
    end: int = 150,
    departments: list[Department] | None = None,
    task_ids: list[str] | None = None,
) -> Plan:
    depts = departments or [Department.ENGG]
    tids = task_ids or ["TASK-A01"]
    return Plan(
        planId=plan_id,
        planVersion=1,
        status=PlanStatus.PROPOSED,
        objectiveProfile=ObjectiveProfile.BALANCED,
        horizonMinutes=4320,
        blocks=[
            ScheduledBlock(
                blockId=f"BLK-{plan_id}",
                sectionId="SEC-GZB-ALJN",
                track=Track.DOWN,
                blockType=block_type,
                start=start,
                end=end,
                taskIds=tids,
                departments=depts,
            )
        ],
        assignments=[
            Assignment(taskId=tids[0], blockId=f"BLK-{plan_id}", start=start, end=end)
        ],
        solverStatus="OPTIMAL",
        provenance="authority test",
    )


class PossessionAuthorityTests(unittest.TestCase):
    def setUp(self):
        main.state = main.Repository()
        self.client = TestClient(main.app)

    def test_role_vocabulary_and_aliases(self):
        self.assertEqual(normalize_role("SUPERVISOR"), "FIELD_SUPERVISOR")
        self.assertEqual(normalize_role("DISPATCHER"), "CONTROL_OFFICER")
        self.assertEqual(normalize_role("INSPECTOR"), "MANAGEMENT")
        self.assertIn("STATION_MASTER", OPERATIONAL_ROLES)
        self.assertIn("TPC", OPERATIONAL_ROLES)

    def test_power_block_requires_four_signatures(self):
        # Create a power block plan requiring:
        # SECTION_CONTROL (always)
        # TRACTION_POWER (POWER blockType)
        # SNT & STATION (requiresT351 task)
        task = MaintenanceTask(
            taskId="TASK-PWR-01",
            department=Department.TRD,
            assetId="ASSET-OHE-1",
            corridorId="GZB-ALJN",
            sectionId="SEC-GZB-ALJN",
            track=Track.DOWN,
            kmStart=10.0,
            kmEnd=10.5,
            taskType=TaskType.OHE_INSPECTION,
            severity=8,
            criticality=8,
            dueMinute=300,
            estimatedDuration=180,
            status=TaskStatus.PENDING,
            blockType=BlockType.POWER,
            requiresPTW=True,
            requiresT351=True,
        )
        main.state.tasks["TASK-PWR-01"] = task

        plan = create_test_plan(
            plan_id="PLAN-PWR-01",
            block_type=BlockType.POWER,
            task_ids=["TASK-PWR-01"],
            departments=[Department.TRD],
        )
        main.state.plans[plan.planId] = copy.deepcopy(plan)
        main.state.plan_versions[f"{plan.planId}:v1"] = copy.deepcopy(plan)

        # Check required authorities
        chain_res = self.client.get(f"/api/v1/block-plans/{plan.planId}/sanctions", headers=AUTH_CONTROL)
        self.assertEqual(chain_res.status_code, 200)
        chain_data = chain_res.json()
        self.assertEqual(len(chain_data["requiredAuthorities"]), 4)
        self.assertIn("SECTION_CONTROL", chain_data["requiredAuthorities"])
        self.assertIn("TRACTION_POWER", chain_data["requiredAuthorities"])
        self.assertIn("STATION", chain_data["requiredAuthorities"])
        self.assertIn("SNT", chain_data["requiredAuthorities"])
        self.assertFalse(chain_data["complete"])

        # 1. CONTROL_OFFICER approves -> 202 Accepted (Partial sanction)
        res1 = self.client.post(f"/api/v1/block-plans/{plan.planId}/approve", headers=AUTH_CONTROL, json={"reason": "controller clears traffic"})
        self.assertEqual(res1.status_code, 202)
        self.assertFalse(res1.json()["complete"])
        self.assertEqual(len(res1.json()["signatures"]), 1)
        # Assignments must NOT be materialised yet
        self.assertNotIn("TASK-PWR-01", main.state.assignments)
        self.assertEqual(main.state.plans[plan.planId].status, PlanStatus.PROPOSED)

        # 2. STATION_MASTER signs Form T/351 sanction -> 202
        res2 = self.client.post(
            f"/api/v1/block-plans/{plan.planId}/sanctions",
            headers=AUTH_SM,
            json={"authority": "STATION", "decision": "GRANTED", "reason": "Station instruments ready", "formReference": "T351-MEMO-01"},
        )
        self.assertEqual(res2.status_code, 202)
        self.assertFalse(res2.json()["complete"])
        self.assertEqual(len(res2.json()["signatures"]), 2)

        # 3. SIGNAL_TELECOM signs -> 202
        res3 = self.client.post(
            f"/api/v1/block-plans/{plan.planId}/sanctions",
            headers=AUTH_SNT,
            json={"authority": "SNT", "decision": "GRANTED", "reason": "S&T disconnection concurred"},
        )
        self.assertEqual(res3.status_code, 202)
        self.assertFalse(res3.json()["complete"])
        self.assertEqual(len(res3.json()["signatures"]), 3)

        # 4. TPC signs -> 200 OK, chain completes, version bumps, assignments materialise!
        res4 = self.client.post(
            f"/api/v1/block-plans/{plan.planId}/sanctions",
            headers=AUTH_TPC,
            json={"authority": "TRACTION_POWER", "decision": "GRANTED", "reason": "OHE elementary section isolation scheduled"},
        )
        self.assertEqual(res4.status_code, 200)
        self.assertEqual(res4.json()["status"], "APPROVED")
        self.assertEqual(res4.json()["planVersion"], 2)

        # Assignments now materialised
        self.assertIn("TASK-PWR-01", main.state.assignments)
        # Runtime possession opened
        poss_id = f"POS-BLK-{plan.planId}"
        self.assertIn(poss_id, main.state.possessions)
        poss = main.state.possessions[poss_id]
        self.assertEqual(poss.state, PossessionState.SANCTIONED)
        self.assertTrue(poss.requiresPTW)
        self.assertTrue(poss.requiresT351)

    def test_unauthorized_role_cannot_sign(self):
        plan = create_test_plan(plan_id="PLAN-UNAUTH")
        main.state.plans[plan.planId] = copy.deepcopy(plan)
        res = self.client.post(
            f"/api/v1/block-plans/{plan.planId}/approve",
            headers=AUTH_SUPERVISOR,
            json={"reason": "unauthorized attempt"},
        )
        self.assertEqual(res.status_code, 403)

    def test_sanction_refusal_marks_chain_refused(self):
        plan = create_test_plan(plan_id="PLAN-REFUSE")
        main.state.plans[plan.planId] = copy.deepcopy(plan)

        res = self.client.post(
            f"/api/v1/block-plans/{plan.planId}/reject",
            headers=AUTH_CONTROL,
            json={"reason": "Heavy mail/express traffic congestion"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "REJECTED")

        chain = main.state.sanctions[plan.planId]
        self.assertTrue(chain.refused)
        self.assertEqual(chain.signatures[0].decision, "REFUSED")
        # Check event emission
        events = [e for e in main.state.events if e["type"] in {"PLAN_SANCTION_REFUSED", "PLAN_REJECTED"}]
        self.assertTrue(len(events) >= 2)

    def test_request_revision_invalidates_signatures(self):
        plan = create_test_plan(plan_id="PLAN-REV", block_type=BlockType.POWER, departments=[Department.TRD])
        main.state.plans[plan.planId] = copy.deepcopy(plan)

        # First sign partial
        main.ensure_chain(plan)
        self.client.post(
            f"/api/v1/block-plans/{plan.planId}/sanctions",
            headers=AUTH_CONTROL,
            json={"authority": "SECTION_CONTROL", "decision": "GRANTED"},
        )

        # Revision requested
        rev = self.client.post(
            f"/api/v1/block-plans/{plan.planId}/request-revision",
            headers=AUTH_CONTROL,
            json={"reason": "Need different time window"},
        )
        self.assertEqual(rev.status_code, 200)
        self.assertEqual(rev.json()["planVersion"], 2)

        # New version chain is empty
        new_chain = self.client.get(f"/api/v1/block-plans/{plan.planId}/sanctions", headers=AUTH_CONTROL).json()
        self.assertEqual(new_chain["planVersion"], 2)
        self.assertEqual(len(new_chain["signatures"]), 0)

    def test_territory_conflict_checked_at_finalisation(self):
        plan1 = create_test_plan(plan_id="PLAN-CONF-1")
        plan1.status = PlanStatus.APPROVED
        main.state.plans[plan1.planId] = plan1

        # Second plan on same section
        plan2 = create_test_plan(plan_id="PLAN-CONF-2")
        main.state.plans[plan2.planId] = plan2

        res = self.client.post(
            f"/api/v1/block-plans/{plan2.planId}/approve",
            headers=AUTH_CONTROL,
            json={"reason": "should conflict"},
        )
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()["error"]["code"], "PLAN_VERSION_CONFLICT")

    def test_notification_routing_and_filtering(self):
        main.state.emit("PTW_REQUESTED", "POS-101", {"info": "PTW memo"}, recipient_role="TPC")
        main.state.emit("T351_ISSUED", "POS-101", {"info": "T351 memo"}, recipient_role="STATION_MASTER")

        all_res = self.client.get("/api/v1/notifications", headers=AUTH_ADMIN)
        self.assertEqual(all_res.status_code, 200)

        tpc_res = self.client.get("/api/v1/notifications?recipientRole=TPC", headers=AUTH_ADMIN)
        self.assertEqual(tpc_res.status_code, 200)
        for n in tpc_res.json()["items"]:
            self.assertEqual(n["recipientRole"], "TPC")

        sm_res = self.client.get("/api/v1/notifications?recipientRole=STATION_MASTER", headers=AUTH_ADMIN)
        self.assertEqual(sm_res.status_code, 200)
        for n in sm_res.json()["items"]:
            self.assertEqual(n["recipientRole"], "STATION_MASTER")

    def test_websocket_accepts_normalized_query_auth_for_browser_clients(self):
        # Native WebSocket browser APIs cannot set X-RailOS-* headers.  The
        # query fallback must still normalize legacy aliases at the boundary.
        with self.client.websocket_connect(
            "/api/v1/events/ws?userId=desk-1&role=DISPATCHER"
        ) as socket:
            initial = socket.receive_json()
            self.assertIn("events", initial)
            self.assertIn("nextSequence", initial)


if __name__ == "__main__":
    unittest.main()
