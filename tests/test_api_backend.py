import copy
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "apps" / "api"), str(ROOT / "packages" / "railos_model"), str(ROOT / "packages" / "shared"), str(ROOT / "packages" / "optimizer"), str(ROOT)]

from fastapi.testclient import TestClient
from railos_model import Assignment, BlockType, Department, ObjectiveProfile, Plan, PlanStatus, ScheduledBlock, Track
from railos_api import main

HEADERS = {"X-RailOS-User":"planner-1","X-RailOS-Role":"PLANNER"}
CONTROL = {"X-RailOS-User":"controller-1","X-RailOS-Role":"CONTROL_OFFICER"}

def sample_plan(profile=ObjectiveProfile.BALANCED, suffix="BAL"):
    return Plan(planId=f"PLAN-{suffix}", planVersion=1, status=PlanStatus.PROPOSED, objectiveProfile=profile, horizonMinutes=4320,
        blocks=[ScheduledBlock(blockId=f"BLK-{suffix}",sectionId="SEC-GZB-ALJN",track=Track.DOWN,blockType=BlockType.TRAFFIC,start=60,end=150,taskIds=["TASK-001"],departments=[Department.ENGG])],
        assignments=[Assignment(taskId="TASK-001",blockId=f"BLK-{suffix}",start=60,end=90)],solverStatus="OPTIMAL",provenance="synthetic test optimizer")

class FakeOptimizer:
    def generate(self, world, objective, **kwargs): return sample_plan(objective, objective.value[:3])

class FakeDiff:
    added=["EMG-TEST"]; removed=[]; moved=[]; unchanged=["TASK-001"]; displaced=[]; metric_deltas={"tasksScheduled":1.0}

class ApiBackendTests(unittest.TestCase):
    def setUp(self):
        main.state=main.Repository(); self.client=TestClient(main.app)

    def test_health_auth_counts_and_strict_camelcase(self):
        self.assertEqual(self.client.get("/api/v1/health").status_code,200)
        self.assertEqual(self.client.get("/api/v1/analytics").status_code,401)
        self.assertEqual(self.client.get("/api/v1/analytics",headers={"X-RailOS-User":"u","X-RailOS-Role":"ROOT"}).status_code,403)
        data=self.client.get("/api/v1/analytics",headers=HEADERS).json()
        self.assertIn("tasks",data); self.assertEqual(data["tasks"],15)
        self.assertIn("defects",data); self.assertEqual(data["defects"],4)
        bad=self.client.post("/api/v1/emergencies",headers=CONTROL,json={"title":"fracture","corridor_id":"GZB-ALJN"})
        self.assertEqual(bad.status_code,422); self.assertEqual(bad.json()["error"]["code"],"VALIDATION_ERROR")

    def test_exact_read_endpoints(self):
        first_task=list(main.state.tasks.keys())[0] if main.state.tasks else "ENG-1001"
        for path in ("/api/v1/corridors/GZB-ALJN","/api/v1/assets","/api/v1/train-movements",f"/api/v1/maintenance/{first_task}","/api/v1/defects","/api/v1/block-windows","/api/v1/work/assignments","/api/v1/integrations/status","/api/v1/events"):
            self.assertEqual(self.client.get(path,headers=HEADERS).status_code,200,path)

    def test_optimizer_unavailable_success_and_idempotency(self):
        with patch.object(main,"optimizer_port",return_value=None):
            response=self.client.post("/api/v1/optimization/generate",headers=HEADERS,json={"objective":"BALANCED"})
            self.assertEqual(response.status_code,503); self.assertEqual(response.json()["error"]["code"],"OPTIMIZER_UNAVAILABLE")
        headers=HEADERS|{"Idempotency-Key":"same"}
        with patch.object(main,"optimizer_port",return_value=FakeOptimizer()):
            first=self.client.post("/api/v1/optimization/generate",headers=headers,json={"objective":"BALANCED"})
            self.assertEqual(first.status_code,200); self.assertEqual(len(first.json()["candidatePlans"]),3)
            self.assertEqual(self.client.post("/api/v1/optimization/generate",headers=headers,json={"objective":"BALANCED"}).json(),first.json())
            self.assertEqual(self.client.post("/api/v1/optimization/generate",headers=headers,json={"objective":"SAFETY_FIRST"}).status_code,409)

    def test_immutable_approval_assignments_and_ack_audit(self):
        plan=sample_plan(); main.state.plans[plan.planId]=copy.deepcopy(plan); main.state.plan_versions[f"{plan.planId}:v1"]=copy.deepcopy(plan)
        approved=self.client.post(f"/api/v1/block-plans/{plan.planId}/approve",headers=CONTROL,json={"reason":"human approval","expectedVersion":1})
        self.assertEqual(approved.status_code,200); self.assertEqual(approved.json()["planVersion"],2)
        self.assertEqual(main.state.plan_versions[f"{plan.planId}:v1"].status,PlanStatus.PROPOSED)
        self.assertEqual(main.state.plan_versions[f"{plan.planId}:v2"].status,PlanStatus.APPROVED)
        self.assertIn("TASK-001",main.state.assignments)
        notice=next(iter(main.state.notifications)); ack=self.client.post(f"/api/v1/notifications/{notice}/acknowledge",headers=CONTROL)
        self.assertEqual(ack.status_code,200); self.assertTrue(ack.json()["acknowledged"]); self.assertEqual(main.state.audit[-1]["type"],"NOTIFICATION_ACKNOWLEDGED")

    def test_emergency_replan_preserves_parent_and_lock(self):
        from railos_model import MaintenanceTask, Department, Track, TaskType, TaskStatus, BlockType
        parent=sample_plan(); main.state.plans[parent.planId]=copy.deepcopy(parent)
        fake_task=MaintenanceTask(taskId="TASK-001",department=Department.ENGG,assetId="ASSET-1",corridorId="GZB-ALJN",sectionId="SEC-GZB-DER",track=Track.DOWN,kmStart=0.0,kmEnd=0.5,taskType=TaskType.TAMPING,severity=5,criticality=5,dueMinute=100,estimatedDuration=60,status=TaskStatus.PENDING,blockType=BlockType.TRAFFIC)
        main.state.tasks["TASK-001"]=fake_task
        emergency=self.client.post("/api/v1/emergencies",headers=CONTROL,json={
            "title":"IMR fracture","corridorId":"GZB-ALJN","sectionId":"SEC_GZB_DER",
            "assetId":"TRACK_SEC_GZB_DER_UP","department":"ENGG","track":"UP",
            "kmStart":12.0,"kmEnd":12.05,"taskType":"RAIL_REPLACEMENT","durationMinutes":60,
        })
        self.assertEqual(emergency.status_code,200); eid=emergency.json()["id"]
        def insert(world, task): clone=world.model_copy(deep=True); clone.tasks.append(task); return clone
        def replan(world, previous, now=0, reason=""):
            child=previous.model_copy(deep=True); child.planId="PLAN-REPLAN"; child.parentPlanId=previous.planId; child.planVersion+=1; child.status=PlanStatus.PROPOSED
            return child,FakeDiff()
        with patch.object(main,"replanner_functions",return_value=(insert,replan)):
            response=self.client.post("/api/v1/replanning/generate",headers=HEADERS,json={"parentPlanId":parent.planId,"emergencyId":eid,"nowMinute":30,"reason":"rail fracture"})
        self.assertEqual(response.status_code,200); self.assertTrue(response.json()["parentPreserved"])
        self.assertEqual(main.state.plans[parent.planId].model_dump(),parent.model_dump()); self.assertEqual(response.json()["diff"]["added"],["EMG-TEST"])
        self.assertEqual(self.client.post(f"/api/v1/block-plans/{parent.planId}/lock",headers=CONTROL).status_code,200)
        self.assertTrue(main.state.tasks["TASK-001"].locked)

    def test_reset_deterministic_and_postgres_misconfiguration(self):
        before=copy.deepcopy(main.state.serializable()); main.state.reset(); after=main.state.serializable(); self.assertEqual(before,after)
        old=os.environ.get("RAILOS_STORAGE_BACKEND"); os.environ["RAILOS_STORAGE_BACKEND"]="postgres"
        try:
            with self.assertRaises(RuntimeError): main.repository_factory()
        finally:
            if old is None: os.environ.pop("RAILOS_STORAGE_BACKEND",None)
            else: os.environ["RAILOS_STORAGE_BACKEND"]=old

if __name__=="__main__": unittest.main()
