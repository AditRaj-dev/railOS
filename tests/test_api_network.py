import copy
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "apps" / "api"), str(ROOT / "packages" / "railos_model"), str(ROOT / "packages" / "shared"), str(ROOT / "packages" / "optimizer"), str(ROOT)]

from fastapi.testclient import TestClient
from railos_data import geometry_intersects_bbox
from railos_model import Assignment, BlockType, DataProvenance, Department, GeoJSONGeometry, ObjectiveProfile, Plan, PlanStatus, RailwaySection, ScheduledBlock, SourceSnapshot, Track
from railos_api import main

HEADERS = {"X-RailOS-User":"planner-1","X-RailOS-Role":"PLANNER"}
CONTROL = {"X-RailOS-User":"controller-1","X-RailOS-Role":"CONTROL_OFFICER"}

def sample_plan(profile=ObjectiveProfile.BALANCED, suffix="BAL"):
    return Plan(planId=f"PLAN-{suffix}", planVersion=1, status=PlanStatus.PROPOSED, objectiveProfile=profile, horizonMinutes=4320,
        blocks=[ScheduledBlock(blockId=f"BLK-{suffix}",sectionId="SEC_GZB_DER",track=Track.DOWN,blockType=BlockType.TRAFFIC,start=60,end=150,taskIds=["TASK-001"],departments=[Department.ENGG])],
        assignments=[Assignment(taskId="TASK-001",blockId=f"BLK-{suffix}",start=60,end=90)],solverStatus="OPTIMAL",provenance="synthetic test optimizer")

class NetworkApiTests(unittest.TestCase):
    def setUp(self):
        main.state=main.Repository()
        self.client=TestClient(main.app)

    def test_zones_list(self):
        resp=self.client.get("/api/v1/network/zones",headers=HEADERS)
        self.assertEqual(resp.status_code,200)
        data=resp.json()
        self.assertIn("items",data)
        self.assertIn("count",data)
        self.assertTrue(data["synthetic"])
        zones=[z for z in data["items"] if z.get("zoneId")=="ZONE_NR"]
        self.assertTrue(len(zones)>0)
        self.assertTrue(zones[0]["planningEnabled"])

    def test_divisions_by_zone(self):
        resp=self.client.get("/api/v1/network/zones/ZONE_NR/divisions",headers=HEADERS)
        self.assertEqual(resp.status_code,200)
        data=resp.json()
        self.assertGreater(len(data["items"]),0)
        divs=[d for d in data["items"] if d.get("divisionId")=="DIV_DLI"]
        self.assertTrue(len(divs)>0)
        self.assertTrue(divs[0]["planningEnabled"])

    def test_sections_by_division(self):
        resp=self.client.get("/api/v1/network/divisions/DIV_DLI/sections",headers=HEADERS)
        self.assertEqual(resp.status_code,200)
        data=resp.json()
        self.assertGreater(len(data["items"]),0)
        secs=[s for s in data["items"] if s.get("sectionId")=="SEC_GZB_DER"]
        self.assertTrue(len(secs)>0)
        self.assertTrue(secs[0]["planningEnabled"])

    def test_section_detail(self):
        resp=self.client.get("/api/v1/network/sections/SEC_GZB_DER",headers=HEADERS)
        self.assertEqual(resp.status_code,200)
        data=resp.json()
        self.assertEqual(data["sectionId"],"SEC_GZB_DER")
        self.assertTrue(data["planningEnabled"])
        self.assertIn("metrics",data)
        self.assertIn("division",data)
        self.assertIn("zone",data)
        self.assertEqual(data["division"]["divisionId"],"DIV_DLI")
        self.assertEqual(data["zone"]["zoneId"],"ZONE_NR")

    def test_section_not_found(self):
        resp=self.client.get("/api/v1/network/sections/NONEXISTENT",headers=HEADERS)
        self.assertEqual(resp.status_code,404)
        self.assertEqual(resp.json()["error"]["code"],"NOT_FOUND")

    def test_geojson_bbox_validation(self):
        resp=self.client.get("/api/v1/network/geojson?bbox=invalid",headers=HEADERS)
        self.assertEqual(resp.status_code,422)
        self.assertEqual(resp.json()["error"]["code"],"INVALID_BBOX")
        resp=self.client.get("/api/v1/network/geojson?bbox=77,28,76,29",headers=HEADERS)
        self.assertEqual(resp.status_code,422)
        self.assertEqual(resp.json()["error"]["code"],"INVALID_BBOX")
        for bbox in ("nan,28,77,29","-181,28,77,29","77,-91,78,29"):
            resp=self.client.get(f"/api/v1/network/geojson?bbox={bbox}",headers=HEADERS)
            self.assertEqual(resp.status_code,422)
            self.assertEqual(resp.json()["error"]["code"],"INVALID_BBOX")

    def test_geojson_query_validation_is_actionable(self):
        for query,code in (
            ("zoom=twenty","INVALID_ZOOM"),
            ("zoom=25","INVALID_ZOOM"),
            ("layer=signals","INVALID_LAYER"),
            ("layers=sections,signals","INVALID_LAYER"),
            ("limit=0","INVALID_LIMIT"),
            ("limit=1.5","INVALID_LIMIT"),
            ("limit=10001","INVALID_LIMIT"),
        ):
            resp=self.client.get(f"/api/v1/network/geojson?{query}",headers=HEADERS)
            self.assertEqual(resp.status_code,422,query)
            error=resp.json()["error"]
            self.assertEqual(error["code"],code)
            self.assertIn("parameter",error["details"])

    def test_geojson_includes_crossing_line_with_endpoints_outside_bbox(self):
        main.state.network.sections.append(RailwaySection(
            sectionId="SEC_CROSSING",
            divisionId="DIV_DLI",
            zoneId="ZONE_NR",
            code="CROSSING",
            name="Viewport crossing test section",
            fromStation="WEST",
            toStation="EAST",
            tracks=[Track.UP],
            geometry=GeoJSONGeometry(type="LineString",coordinates=[[76.0,28.5],[79.0,28.5]]),
        ))
        resp=self.client.get("/api/v1/network/geojson?bbox=77,28,78,29&layer=sections",headers=HEADERS)
        self.assertEqual(resp.status_code,200)
        self.assertIn("SEC_CROSSING",[feature["properties"]["entityId"] for feature in resp.json()["features"]])

    def test_supported_geojson_geometry_intersection_semantics(self):
        bbox=(1.0,1.0,2.0,2.0)
        self.assertTrue(geometry_intersects_bbox({"type":"Point","coordinates":[1.5,1.5]},bbox))
        self.assertTrue(geometry_intersects_bbox({"type":"LineString","coordinates":[[0,1.5],[3,1.5]]},bbox))
        self.assertTrue(geometry_intersects_bbox({"type":"MultiLineString","coordinates":[[[4,4],[5,5]],[[0,1.5],[3,1.5]]]},bbox))
        self.assertTrue(geometry_intersects_bbox({"type":"Polygon","coordinates":[[[0,0],[3,0],[3,3],[0,3],[0,0]]]},bbox))
        self.assertTrue(geometry_intersects_bbox({"type":"MultiPolygon","coordinates":[[[[4,4],[5,4],[5,5],[4,5],[4,4]]],[[[0,0],[3,0],[3,3],[0,3],[0,0]]]]},bbox))
        polygon_with_hole={"type":"Polygon","coordinates":[[[0,0],[10,0],[10,10],[0,10],[0,0]],[[4,4],[6,4],[6,6],[4,6],[4,4]]]}
        self.assertFalse(geometry_intersects_bbox(polygon_with_hole,(4.5,4.5,5.5,5.5)))

    def test_geojson_sections(self):
        resp=self.client.get("/api/v1/network/geojson?layer=sections",headers=HEADERS)
        self.assertEqual(resp.status_code,200)
        data=resp.json()
        self.assertEqual(data["type"],"FeatureCollection")
        self.assertIn("features",data)
        self.assertTrue(data["synthetic"])
        if data["features"]:
            feat=data["features"][0]
            self.assertEqual(feat["type"],"Feature")
            self.assertIn("entityType",feat["properties"])
            self.assertIn("entityId",feat["properties"])
            self.assertIn("sectionId",feat["properties"])
            self.assertIn("divisionId",feat["properties"])
            self.assertIn("zoneId",feat["properties"])
            self.assertIn("planningEnabled",feat["properties"])
            self.assertIn("metrics",feat["properties"])
            self.assertIn("provenance",feat["properties"])

    def test_geojson_segments(self):
        resp=self.client.get("/api/v1/network/geojson?layer=segments",headers=HEADERS)
        self.assertEqual(resp.status_code,200)
        data=resp.json()
        self.assertEqual(data["type"],"FeatureCollection")
        if data["features"]:
            feat=data["features"][0]
            self.assertEqual(feat["properties"]["entityType"],"SEGMENT")
            self.assertIn("riskScore",feat["properties"]["metrics"])

    def test_geojson_stations(self):
        resp=self.client.get("/api/v1/network/geojson?layer=stations",headers=HEADERS)
        self.assertEqual(resp.status_code,200)
        data=resp.json()
        self.assertEqual(data["type"],"FeatureCollection")
        if data["features"]:
            feat=data["features"][0]
            self.assertEqual(feat["properties"]["entityType"],"STATION")

    def test_geojson_multi_layer_contract_limit_and_canonical_properties(self):
        resp=self.client.get("/api/v1/network/geojson?bbox=77.4,28.5,77.6,28.7&layers=sections,segments,stations&zoom=8.5",headers=HEADERS)
        self.assertEqual(resp.status_code,200)
        data=resp.json()
        self.assertEqual(data["query"]["layers"],["sections","segments","stations"])
        self.assertEqual(data["query"]["zoom"],8.5)
        self.assertIn("provenance",data)
        self.assertGreater(len({feature["properties"]["entityType"] for feature in data["features"]}),1)
        common={"entityType","entityId","layer","code","name","sectionId","divisionId","zoneId","planningEnabled","metrics","synthetic","provenance"}
        for feature in data["features"]:
            self.assertTrue(common.issubset(feature["properties"]),feature["properties"])
            self.assertEqual(feature["id"],feature["properties"]["entityId"])

        limited=self.client.get("/api/v1/network/geojson?layer=all&limit=1",headers=HEADERS).json()
        self.assertEqual(limited["count"],1)
        self.assertGreater(limited["totalCount"],1)
        self.assertTrue(limited["truncated"])

    def test_provenance_supports_immutable_source_snapshot_without_claiming_authority(self):
        provenance=DataProvenance(
            synthetic=False,
            label="OpenStreetMap railway geometry",
            source="Geofabrik India extract",
            sourceType="community-geometry",
            sourceSnapshot=SourceSnapshot(snapshotId="india-2026-09-08",licence="ODbL-1.0",checksumSha256="a"*64),
        )
        payload=provenance.model_dump(mode="json")
        self.assertEqual(payload["sourceSnapshot"]["snapshotId"],"india-2026-09-08")
        self.assertTrue(payload["sourceSnapshot"]["immutable"])
        self.assertFalse(payload["isOperationallyAuthoritative"])

    def test_search_zones(self):
        resp=self.client.get("/api/v1/network/search?q=NR",headers=HEADERS)
        self.assertEqual(resp.status_code,200)
        data=resp.json()
        zones=[i for i in data["items"] if i.get("entityType")=="ZONE"]
        self.assertGreater(len(zones),0)
        self.assertTrue(any("NR" in z.get("code","") for z in zones))

    def test_search_sections(self):
        resp=self.client.get("/api/v1/network/search?q=GZB",headers=HEADERS)
        self.assertEqual(resp.status_code,200)
        data=resp.json()
        secs=[i for i in data["items"] if i.get("entityType")=="SECTION"]
        self.assertGreater(len(secs),0)

    def test_search_case_insensitive(self):
        resp=self.client.get("/api/v1/network/search?q=gzb",headers=HEADERS)
        self.assertEqual(resp.status_code,200)
        data=resp.json()
        self.assertGreater(len(data["items"]),0)

    def test_opportunities_endpoint(self):
        resp=self.client.get("/api/v1/opportunities",headers=HEADERS)
        self.assertEqual(resp.status_code,200)
        body=resp.json()
        self.assertIn("items",body)
        self.assertEqual(body["count"],len(body["items"]))

    def test_bundles_endpoint(self):
        resp=self.client.get("/api/v1/bundles",headers=HEADERS)
        self.assertEqual(resp.status_code,200)
        body=resp.json()
        self.assertIn("items",body)
        self.assertEqual(body["count"],len(body["items"]))

    def test_priority_endpoint(self):
        resp=self.client.get("/api/v1/maintenance/priority",headers=HEADERS)
        self.assertEqual(resp.status_code,200)
        body=resp.json()
        self.assertIn("items",body)
        self.assertEqual(body["count"],len(body["items"]))

    def test_risk_endpoint(self):
        resp=self.client.get("/api/v1/maintenance/risk",headers=HEADERS)
        self.assertEqual(resp.status_code,200)
        body=resp.json()
        self.assertIn("items",body)
        self.assertEqual(body["count"],len(body["items"]))

    def test_planning_gated_not_enabled(self):
        with patch.object(main,"optimizer_port",return_value=type("O",(object,),{"generate":lambda s,w,p:sample_plan(p)})()) as opt:
            resp=self.client.post("/api/v1/optimization/generate",headers=HEADERS,json={"corridorIds":["DEMO_FZR_LDH"],"objective":"BALANCED"})
            self.assertEqual(resp.status_code,403)
            self.assertEqual(resp.json()["error"]["code"],"PLANNING_NOT_ENABLED")

    def test_planning_enabled_gzb_aljn(self):
        with patch.object(main,"optimizer_port",return_value=type("O",(object,),{"generate":lambda s,w,p:sample_plan(p)})()) as opt:
            resp=self.client.post("/api/v1/optimization/generate",headers=HEADERS,json={"corridorIds":["GZB-ALJN"],"objective":"BALANCED"})
            self.assertEqual(resp.status_code,200)

    def test_reject_sets_status_rejected(self):
        plan=sample_plan()
        main.state.plans[plan.planId]=copy.deepcopy(plan)
        main.state.plan_versions[f"{plan.planId}:v1"]=copy.deepcopy(plan)
        resp=self.client.post(f"/api/v1/block-plans/{plan.planId}/reject",headers=CONTROL,json={"reason":"not feasible"})
        self.assertEqual(resp.status_code,200)
        self.assertEqual(resp.json()["status"],"REJECTED")
        self.assertEqual(main.state.plan_versions[f"{plan.planId}:v2"].status,PlanStatus.REJECTED)

    def test_approver_identity_recorded(self):
        plan=sample_plan()
        main.state.plans[plan.planId]=copy.deepcopy(plan)
        main.state.plan_versions[f"{plan.planId}:v1"]=copy.deepcopy(plan)
        resp=self.client.post(f"/api/v1/block-plans/{plan.planId}/approve",headers=CONTROL,json={"reason":"approved"})
        self.assertEqual(resp.status_code,200)
        events=[e for e in main.state.events if e["type"]=="PLAN_APPROVED"]
        self.assertGreater(len(events),0)
        self.assertEqual(events[-1]["actor"],"controller-1")
        self.assertEqual(events[-1]["reason"],"approved")
        self.assertIn("controller-1",main.state.plans[plan.planId].provenance)

    def test_auth_required_on_network_endpoints(self):
        resp=self.client.get("/api/v1/network/zones")
        self.assertEqual(resp.status_code,401)
        resp=self.client.get("/api/v1/network/geojson")
        self.assertEqual(resp.status_code,401)

    def test_simulator_scenario_endpoint(self):
        resp=self.client.post("/api/v1/simulator/scenarios/train_delayed",headers=HEADERS,json={})
        self.assertEqual(resp.status_code,200)
        body=resp.json()
        self.assertEqual(body["scenario"],"train_delayed")
        self.assertIn("world",body)

    def test_simulator_unknown_scenario_404(self):
        resp=self.client.post("/api/v1/simulator/scenarios/not_a_scenario",headers=HEADERS,json={})
        self.assertEqual(resp.status_code,404)

if __name__=="__main__": unittest.main()
