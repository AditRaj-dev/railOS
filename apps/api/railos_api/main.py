"""RailOS API: human-governed orchestration over canonical RailOS contracts."""
from __future__ import annotations

import asyncio, copy, hashlib, json, math, os, threading, uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from railos_data import geometry_intersects_bbox
from railos_model import (Asset, BlockType, BlockWindow, Corridor, Department,
    Defect, Dependency, GoodsForecast, MaintenanceTask, NetworkCatalog,
    ObjectiveProfile, Plan, PlanStatus, Resource, ScenarioWorld, Severity,
    TaskStatus, TaskType, Track, TrainMovement)

DEMO_EPOCH = "2026-09-09T00:00:00+05:30"
DEMO_NOW = "2026-09-08T06:00:00+00:00"
VALID_ROLES = {"ADMIN", "CONTROL_OFFICER", "PLANNER", "ENGINEERING", "SIGNAL_TELECOM", "TRACTION", "FIELD_SUPERVISOR", "MANAGEMENT"}

def camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.title() for part in tail)

class DTO(BaseModel):
    model_config = ConfigDict(alias_generator=camel, populate_by_name=False, extra="forbid")

class PlanRequest(DTO):
    corridor_ids: list[str] = Field(default_factory=lambda: ["GZB-ALJN"])
    objective: ObjectiveProfile = ObjectiveProfile.BALANCED
    planning_horizon: str = "WEEKLY"
    task_ids: list[str] | None = None

class Decision(DTO):
    reason: str = ""
    expected_version: int | None = None

class EmergencyRequest(DTO):
    title: str
    corridor_id: str
    section_id: str = "SEC_KRJ_SMQ"
    asset_id: str = "TRACK_SEC_KRJ_SMQ_DOWN"
    severity: Severity = Severity.IMR
    duration_minutes: int = Field(default=60, gt=0)

class ReplanRequest(DTO):
    parent_plan_id: str
    emergency_id: str
    now_minute: int = Field(default=0, ge=0)
    reason: str = Field(min_length=1)

class WorkUpdate(DTO):
    status: TaskStatus
    note: str = ""

class DefectCreate(DTO):
    defect_id: str
    asset_id: str
    section_id: str
    severity_code: Severity
    detected_at_minute: int = Field(ge=0)
    task_id: str | None = None
    repeat_count: int = Field(default=0, ge=0)

class User(DTO):
    user_id: str
    role: str

class Repository:
    """Atomic deterministic repository used by demo and tests."""
    def __init__(self):
        self.lock = threading.RLock()
        self.subscribers: list[asyncio.Queue] = []
        self.reset()

    def reset(self):
        with self.lock:
            for name in ("corridors", "assets", "tasks", "defects", "trains", "goods", "windows", "resources", "dependencies", "plans", "plan_versions", "runs", "notifications", "idempotency", "emergencies", "assignments", "ingestion_records"):
                setattr(self, name, {})
            self.network = NetworkCatalog()
            self.events, self.audit = [], []
            self._seed()
            self.commit()

    def _seed(self):
        from railos_data import load_network, load_world
        from integrations.adapters import ADAPTERS

        self.adapters = ADAPTERS
        for name, adapter in ADAPTERS.items():
            self.ingestion_records[name] = adapter.normalize(adapter.fetch("seed")[0])

        world = load_world(os.getenv("RAILOS_DATASET_DIR", "datasets"))
        self.network = load_network(os.getenv("RAILOS_NETWORK_DATA", "datasets/network.json"))
        for name, values, key in (
            ("corridors", world.corridors, "corridorId"),
            ("assets", world.assets, "assetId"),
            ("tasks", world.tasks, "taskId"),
            ("defects", world.defects, "defectId"),
            ("trains", world.trains, "trainId"),
            ("goods", world.goods, "rakeId"),
            ("windows", world.windows, "windowId"),
            ("resources", world.resources, "resourceId"),
        ):
            setattr(self, name, {getattr(value, key): value for value in values})
        self.dependencies = {
            f"{value.predecessorTaskId}:{value.successorTaskId}": value
            for value in world.dependencies
        }
        self.horizon_minutes = world.horizonMinutes
        self.horizon_start_iso = world.horizonStartIso
        self.emit("DEMO_RESET", "demo", {
            "tasks": len(self.tasks), "defects": len(self.defects),
            "movements": len(self.trains), "windows": len(self.windows),
            "networkZones": len(self.network.zones),
        }, occurred_at=DEMO_NOW, notify=False)

    @contextmanager
    def transaction(self):
        with self.lock:
            yield
            self.commit()

    def commit(self):
        pass

    def emit(self, event_type, entity_id, payload, actor="system", reason="", before=None, version=None, occurred_at=None, notify=True):
        event = {"sequence":len(self.events)+1, "id":f"EVT-{len(self.events)+1:06d}", "type":event_type, "actor":actor, "action":event_type, "entityId":entity_id, "before":copy.deepcopy(before), "after":copy.deepcopy(payload), "planVersion":version, "reason":reason, "occurredAt":occurred_at or datetime.now(timezone.utc).isoformat(), "synthetic":True}
        self.events.append(event); self.audit.append(copy.deepcopy(event))
        if notify:
            nid = f"NTF-{event['sequence']:06d}"
            self.notifications[nid] = {"id":nid,"eventId":event["id"],"category":"CRITICAL" if event_type=="EMERGENCY_CREATED" else "ACTION_REQUIRED","recipientRole":"CONTROL_OFFICER" if event_type.startswith(("PLAN_","EMERGENCY")) else "FIELD_SUPERVISOR","groupingKey":f"{event_type}:{entity_id}","acknowledged":False,"createdAt":event["occurredAt"],"synthetic":True}
        for queue in list(self.subscribers):
            try: queue.put_nowait(copy.deepcopy(event))
            except asyncio.QueueFull: pass
        return event

    def world(self):
        return ScenarioWorld(
            horizonMinutes=getattr(self, "horizon_minutes", 4320),
            horizonStartIso=getattr(self, "horizon_start_iso", DEMO_EPOCH),
            corridors=list(self.corridors.values()), assets=list(self.assets.values()),
            tasks=list(self.tasks.values()), defects=list(self.defects.values()),
            trains=list(self.trains.values()), goods=list(self.goods.values()),
            windows=list(self.windows.values()), resources=list(self.resources.values()),
            dependencies=list(self.dependencies.values()),
        )

    def serializable(self):
        def dump(values): return {k:(v.model_dump(mode="json") if hasattr(v,"model_dump") else v) for k,v in values.items()}
        result = {name:dump(getattr(self,name)) for name in ("corridors","assets","tasks","defects","trains","goods","windows","resources","dependencies","plans","plan_versions","runs","notifications","idempotency","emergencies","assignments","ingestion_records")}
        return result | {"network": self.network.model_dump(mode="json"), "events":self.events,"audit":self.audit}

class PostgresRepository(Repository):
    """Persists each atomic application snapshot to PostgreSQL JSONB."""
    def __init__(self):
        url = os.getenv("DATABASE_URL") or os.getenv("RAILOS_DATABASE_URL")
        if not url: raise RuntimeError("DATABASE_URL is required for postgres backend")
        try: import psycopg
        except ImportError as exc: raise RuntimeError("psycopg is required for postgres backend") from exc
        try:
            self.connection = psycopg.connect(url, connect_timeout=3)
            self.connection.execute("CREATE TABLE IF NOT EXISTS railos_state(namespace text NOT NULL,key text NOT NULL,payload jsonb NOT NULL,version bigint NOT NULL DEFAULT 1,updated_at timestamptz NOT NULL DEFAULT now(),PRIMARY KEY(namespace,key))")
            self.connection.commit()
            row = self.connection.execute("SELECT payload FROM railos_state WHERE namespace=%s AND key=%s",("application","snapshot")).fetchone()
        except Exception as exc: raise RuntimeError("postgres connectivity validation failed") from exc
        if row:
            self.lock=threading.RLock(); self.subscribers=[]
            payload=row[0] if isinstance(row[0],dict) else json.loads(row[0])
            model_types={"corridors":Corridor,"assets":Asset,"tasks":MaintenanceTask,"defects":Defect,"trains":TrainMovement,"windows":BlockWindow,"plans":Plan,"plan_versions":Plan}
            for name,values in payload.items():
                if name in {"events","audit"}: setattr(self,name,values); continue
                model=model_types.get(name)
                setattr(self,name,{k:(model.model_validate(v) if model else v) for k,v in values.items()})
            from integrations.adapters import ADAPTERS
            self.adapters=ADAPTERS
        else:
            self._initializing=True; super().__init__(); self._initializing=False; self.commit()

    def commit(self):
        if getattr(self,"_initializing",False): return
        payload = json.dumps(self.serializable(), default=str)
        with self.connection.transaction():
            self.connection.execute("INSERT INTO railos_state(namespace,key,payload,version) VALUES(%s,%s,%s,1) ON CONFLICT(namespace,key) DO UPDATE SET payload=EXCLUDED.payload,version=railos_state.version+1,updated_at=now()",("application","snapshot",payload))

def repository_factory():
    backend = os.getenv("RAILOS_STORAGE_BACKEND","memory").lower()
    if backend=="memory": return Repository()
    if backend=="postgres": return PostgresRepository()
    raise RuntimeError(f"unsupported RAILOS_STORAGE_BACKEND: {backend}")

def optimizer_port():
    try:
        from .optimizer_port import optimizer_port as load
        return load()
    except (ImportError,AttributeError,TypeError): return None

def replanner_functions():
    try:
        from optimizer.replan import insert_emergency, replan
        return insert_emergency, replan
    except (ImportError,AttributeError,TypeError): return None

state = repository_factory()
app = FastAPI(title="RailOS API",version="1.0.0",description="Synthetic Hackathon Simulation — decision support; human approval required")

# Local synthetic mode only: the control-center dev server is a separate origin.
app.add_middleware(CORSMiddleware, allow_origins=[o for o in os.getenv("RAILOS_CORS_ORIGINS","http://localhost:3000,http://127.0.0.1:3000").split(",") if o], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

from .evidence_routes import router as evidence_router
app.include_router(evidence_router)


def auth(user:str|None=Header(None,alias="X-RailOS-User"), role:str|None=Header(None,alias="X-RailOS-Role")):
    if not user: raise HTTPException(401,{"code":"UNAUTHENTICATED","message":"X-RailOS-User is required"})
    if role not in VALID_ROLES: raise HTTPException(403,{"code":"FORBIDDEN","message":"X-RailOS-Role is missing or invalid"})
    return User(userId=user,role=role)

def allow(*roles):
    def dependency(user:User=Depends(auth)):
        if user.role not in roles and user.role!="ADMIN": raise HTTPException(403,{"code":"FORBIDDEN","message":"role is not allowed"})
        return user
    return dependency

def error_body(code,message,details=None): return {"error":{"code":code,"message":message,"details":details or {},"requestId":uuid.uuid4().hex}}

NETWORK_LAYER_ORDER = ("sections", "segments", "stations")
NETWORK_WORLD_BBOX = (-180.0, -90.0, 180.0, 90.0)
DEFAULT_NETWORK_LIMIT = 5_000
MAX_NETWORK_LIMIT = 10_000

def _invalid_network_query(code:str,message:str,parameter:str,value:Any,**details:Any):
    raise HTTPException(422,{"code":code,"message":message,"details":{"parameter":parameter,"value":value,**details}})

def _parse_network_bbox(value:str|None):
    if value is None: return NETWORK_WORLD_BBOX,None
    try: parts=[float(part.strip()) for part in value.split(",")]
    except ValueError:
        _invalid_network_query("INVALID_BBOX","bbox must contain four finite numbers","bbox",value,expected="minLon,minLat,maxLon,maxLat")
    if len(parts)!=4 or not all(math.isfinite(part) for part in parts):
        _invalid_network_query("INVALID_BBOX","bbox must contain four finite numbers","bbox",value,expected="minLon,minLat,maxLon,maxLat")
    min_lon,min_lat,max_lon,max_lat=parts
    if not (-180<=min_lon<max_lon<=180 and -90<=min_lat<max_lat<=90):
        _invalid_network_query("INVALID_BBOX","bbox coordinates are outside valid bounds or not ordered","bbox",value,longitudeRange=[-180,180],latitudeRange=[-90,90])
    return (min_lon,min_lat,max_lon,max_lat),parts

def _parse_network_zoom(value:str|None):
    if value is None: return None
    try: zoom=float(value)
    except ValueError:
        _invalid_network_query("INVALID_ZOOM","zoom must be a finite number between 0 and 24","zoom",value,minimum=0,maximum=24)
    if not math.isfinite(zoom) or not 0<=zoom<=24:
        _invalid_network_query("INVALID_ZOOM","zoom must be a finite number between 0 and 24","zoom",value,minimum=0,maximum=24)
    return zoom

def _parse_network_layers(layer:str|None,layers:list[str]|None):
    requested=[]
    for raw in ([layer] if layer is not None else [])+(layers or []):
        requested.extend(value.strip().lower() for value in raw.split(","))
    if not requested: return ["sections"]
    invalid=sorted({value for value in requested if value not in {*NETWORK_LAYER_ORDER,"all"}})
    if invalid:
        _invalid_network_query("INVALID_LAYER","one or more network layers are not supported","layers",invalid,allowed=[*NETWORK_LAYER_ORDER,"all"])
    if "all" in requested: return list(NETWORK_LAYER_ORDER)
    return [value for value in NETWORK_LAYER_ORDER if value in requested]

def _parse_network_limit(value:str|None):
    if value is None: return DEFAULT_NETWORK_LIMIT
    try: limit=int(value)
    except ValueError:
        _invalid_network_query("INVALID_LIMIT",f"limit must be an integer between 1 and {MAX_NETWORK_LIMIT}","limit",value,minimum=1,maximum=MAX_NETWORK_LIMIT)
    if not 1<=limit<=MAX_NETWORK_LIMIT:
        _invalid_network_query("INVALID_LIMIT",f"limit must be an integer between 1 and {MAX_NETWORK_LIMIT}","limit",value,minimum=1,maximum=MAX_NETWORK_LIMIT)
    return limit

def _network_properties(*,entity_type:str,entity_id:str,layer:str,code:str|None,name:str|None,section_id:str|None,division_id:str|None,zone_id:str|None,planning_enabled:bool,metrics:dict[str,Any],provenance:Any):
    provenance_data=provenance.model_dump(by_alias=True,mode="json") if hasattr(provenance,"model_dump") else provenance
    return {"entityType":entity_type,"entityId":entity_id,"layer":layer,"code":code,"name":name,"sectionId":section_id,"divisionId":division_id,"zoneId":zone_id,"planningEnabled":planning_enabled,"metrics":metrics,"synthetic":bool(provenance_data.get("synthetic",True)),"provenance":provenance_data}

@app.exception_handler(HTTPException)
async def http_error(_,exc):
    detail = exc.detail if isinstance(exc.detail,dict) else {"code":"HTTP_ERROR","message":str(exc.detail)}
    return JSONResponse(error_body(detail.get("code","HTTP_ERROR"),detail.get("message","request failed"),detail.get("details")),status_code=exc.status_code)

@app.exception_handler(RequestValidationError)
async def validation_error(_,exc): return JSONResponse(error_body("VALIDATION_ERROR","request validation failed",exc.errors()),status_code=422)

def listed(values): return {"items":[v.model_dump(by_alias=True,mode="json") if hasattr(v,"model_dump") else v for v in values.values()],"count":len(values),"synthetic":True,"scenario":"GZB_ALJN_DEMO"}

@app.get("/health")
@app.get("/api/v1/health")
def health(): return {"status":"ok","synthetic":True,"storageBackend":os.getenv("RAILOS_STORAGE_BACKEND","memory")}

@app.post("/api/v1/demo/reset")
def reset(_:User=Depends(allow("ADMIN"))):
    state.reset()
    counts={"tasks":len(state.tasks),"defects":len(state.defects),"movements":len(state.trains),"windows":len(state.windows),
        "critical":sum(t.severity>=9 for t in state.tasks.values()),"overdue":sum(t.overdueDays>0 for t in state.tasks.values())}
    return {"status":"reset","counts":counts,"synthetic":True}

@app.get("/api/v1/corridors")
def corridors(_:User=Depends(auth)): return listed(state.corridors)
@app.get("/api/v1/corridors/{corridor_id}")
def corridor(corridor_id:str,_:User=Depends(auth)):
    if corridor_id not in state.corridors: raise HTTPException(404,{"code":"UNKNOWN_CORRIDOR","message":"corridor not found"})
    return state.corridors[corridor_id]
@app.get("/api/v1/assets")
def assets(_:User=Depends(auth)): return listed(state.assets)
@app.get("/api/v1/trains")
@app.get("/api/v1/trains/movements")
@app.get("/api/v1/train-movements")
def trains(_:User=Depends(auth)): return listed(state.trains)
@app.get("/api/v1/maintenance/priority")
def priority(_:User=Depends(auth)):
    try:
        from risk_engine import score_all
        results=score_all(state.world())
        return {"items":[r.model_dump(by_alias=True,mode="json") if hasattr(r,"model_dump") else r for r in results.values()],"count":len(results),"synthetic":True}
    except (ImportError,AttributeError,TypeError):
        raise HTTPException(503,{"code":"ENGINE_UNAVAILABLE","message":"risk engine is unavailable"})
@app.get("/api/v1/maintenance/risk")
def risk(_:User=Depends(auth)):
    try:
        from risk_engine import assess_all
        results=assess_all(state.world())
        return {"items":[r.model_dump(by_alias=True,mode="json") if hasattr(r,"model_dump") else r for r in results.values()],"count":len(results),"synthetic":True}
    except (ImportError,AttributeError,TypeError):
        raise HTTPException(503,{"code":"ENGINE_UNAVAILABLE","message":"risk engine is unavailable"})
@app.get("/api/v1/maintenance")
@app.get("/api/v1/maintenance/tasks")
def tasks(status:TaskStatus|None=None,_:User=Depends(auth)): return listed({k:v for k,v in state.tasks.items() if status is None or v.status==status})
@app.get("/api/v1/maintenance/{task_id}")
@app.get("/api/v1/maintenance/tasks/{task_id}")
def task(task_id:str,_:User=Depends(auth)):
    if task_id not in state.tasks: raise HTTPException(404,{"code":"NOT_FOUND","message":"task not found"})
    return state.tasks[task_id]
@app.get("/api/v1/defects")
def defects(_:User=Depends(auth)): return listed(state.defects)
@app.post("/api/v1/defects")
def create_defect(body:DefectCreate,user:User=Depends(allow("ENGINEERING","SIGNAL_TELECOM","TRACTION"))):
    defect=Defect(defectId=body.defect_id,assetId=body.asset_id,sectionId=body.section_id,severityCode=body.severity_code,detectedAtMinute=body.detected_at_minute,taskId=body.task_id,repeatCount=body.repeat_count)
    with state.transaction(): state.defects[defect.defectId]=defect; state.emit("DEFECT_CREATED",defect.defectId,defect.model_dump(mode="json"),user.user_id)
    return defect
@app.get("/api/v1/block-windows")
def windows(_:User=Depends(auth)): return listed(state.windows)
@app.get("/api/v1/block-plans")
def plans(_:User=Depends(auth)): return listed(state.plans)
@app.get("/api/v1/block-plans/{plan_id}")
def plan_detail(plan_id:str,version:int|None=None,_:User=Depends(auth)):
    value = state.plan_versions.get(f"{plan_id}:v{version}") if version is not None else state.plans.get(plan_id)
    if value is None: raise HTTPException(404,{"code":"NOT_FOUND","message":"plan not found"})
    return value

@app.post("/api/v1/optimization/generate")
def generate(request:PlanRequest,idempotency_key:str|None=Header(None,alias="Idempotency-Key"),user:User=Depends(allow("PLANNER","CONTROL_OFFICER"))):
    key = f"{user.user_id}:optimization:{idempotency_key}" if idempotency_key else None
    fingerprint = hashlib.sha256(request.model_dump_json(by_alias=True).encode()).hexdigest()
    if key and key in state.idempotency:
        saved=state.idempotency[key];
        if saved["fingerprint"]!=fingerprint: raise HTTPException(409,{"code":"IDEMPOTENCY_CONFLICT","message":"key reused with a different request"})
        return saved["response"]
    for cid in request.corridor_ids:
        sections=[s for s in state.network.sections if s.corridorId==cid]
        if not any(s.planningEnabled for s in sections): raise HTTPException(403,{"code":"PLANNING_NOT_ENABLED","message":f"planning is not enabled for corridor {cid}","details":{"corridorId":cid}})
    port=optimizer_port()
    if port is None: raise HTTPException(503,{"code":"OPTIMIZER_UNAVAILABLE","message":"architecture-owned optimizer is unavailable"})
    candidates=[port.generate(state.world(),profile) for profile in (ObjectiveProfile.SAFETY_FIRST,ObjectiveProfile.BALANCED,ObjectiveProfile.OPERATIONS_FIRST)]
    if candidates and all("INFEASIBLE" in p.solverStatus.upper() for p in candidates):
        raise HTTPException(422,{"code":"SOLVER_INFEASIBLE","message":"optimizer found no feasible plan","details":{"warnings":[w for p in candidates for w in p.warnings]}})
    try:
        from optimizer.audit import audit
        world=state.world()
        for plan in candidates:
            try:
                violations=audit(world,plan)
                if violations: plan.warnings.extend([f"{v.code}: {v.detail}" for v in violations])
            except (KeyError,ValueError): pass
    except (ImportError,AttributeError,TypeError): pass
    blocking_violations=[w for p in candidates for w in p.warnings if any(x in w for x in ["HC-","PLAN","RECOMPUTE"])]
    if candidates and all(p.warnings for p in candidates) and blocking_violations:
        raise HTTPException(422,{"code":"PLAN_FAILED_AUDIT","message":"all candidate plans failed safety audit","details":{"violations":blocking_violations[:10]}})
    with state.transaction():
        for plan in candidates: state.plans[plan.planId]=copy.deepcopy(plan); state.plan_versions[f"{plan.planId}:v{plan.planVersion}"]=copy.deepcopy(plan)
        run_id=f"RUN-{len(state.runs)+1:06d}"; run={"id":run_id,"status":"COMPLETED","solverStatus":[p.solverStatus for p in candidates],"candidatePlanIds":[p.planId for p in candidates],"createdAt":datetime.now(timezone.utc).isoformat(),"synthetic":True}; state.runs[run_id]=run; state.emit("PLAN_GENERATED",run_id,run,user.user_id)
        response={"optimizationRun":run,"candidatePlans":[p.model_dump(by_alias=True,mode="json") for p in candidates],"warnings":[w for p in candidates for w in p.warnings]}
        if key: state.idempotency[key]={"fingerprint":fingerprint,"response":response}
    return response

@app.get("/api/v1/network/catalog")
def network_catalog(_:User=Depends(auth)): return state.network.model_dump(by_alias=True,mode="json")|{"synthetic":True}
@app.get("/api/v1/network/zones")
def zones(_:User=Depends(auth)): return {"items":[z.model_dump(by_alias=True,mode="json") for z in state.network.zones],"count":len(state.network.zones),"synthetic":True}
@app.get("/api/v1/network/zones/{zone_id}/divisions")
def divisions(zone_id:str,_:User=Depends(auth)):
    divs=[d for d in state.network.divisions if d.zoneId==zone_id]
    return {"items":[d.model_dump(by_alias=True,mode="json") for d in divs],"count":len(divs),"synthetic":True}
@app.get("/api/v1/network/divisions/{division_id}/sections")
def sections_by_div(division_id:str,_:User=Depends(auth)):
    secs=[s for s in state.network.sections if s.divisionId==division_id]
    return {"items":[s.model_dump(by_alias=True,mode="json") for s in secs],"count":len(secs),"synthetic":True}
@app.get("/api/v1/network/sections/{section_id}")
def section(section_id:str,_:User=Depends(auth)):
    sec=next((s for s in state.network.sections if s.sectionId==section_id),None)
    if sec is None: raise HTTPException(404,{"code":"NOT_FOUND","message":"section not found"})
    data=sec.model_dump(by_alias=True,mode="json")
    div=next((d for d in state.network.divisions if d.divisionId==sec.divisionId),None)
    if div:
        data["division"]={"divisionId":div.divisionId,"zoneId":div.zoneId,"name":div.name,"code":div.code}
        zone=next((z for z in state.network.zones if z.zoneId==div.zoneId),None)
        if zone: data["zone"]={"zoneId":zone.zoneId,"name":zone.name,"code":zone.code}
    return data
@app.get("/api/v1/network/geojson")
def network_geojson(
    bbox:str|None=Query(None,description="minLon,minLat,maxLon,maxLat"),
    zoom:str|None=Query(None,description="Map zoom level from 0 through 24"),
    layer:str|None=Query(None,description="Backward-compatible singular layer selector"),
    layers:list[str]|None=Query(None,description="Comma-separated or repeated layer selectors"),
    limit:str|None=Query(None,description=f"Maximum features, up to {MAX_NETWORK_LIMIT}"),
    _:User=Depends(auth),
):
    viewport,requested_bbox=_parse_network_bbox(bbox)
    requested_zoom=_parse_network_zoom(zoom)
    requested_layers=_parse_network_layers(layer,layers)
    requested_limit=_parse_network_limit(limit)
    features=[]
    sections_by_id={section.sectionId:section for section in state.network.sections}

    if "sections" in requested_layers:
        for section_value in state.network.sections:
            if not geometry_intersects_bbox(section_value.geometry,viewport): continue
            properties=_network_properties(entity_type="SECTION",entity_id=section_value.sectionId,layer="sections",code=section_value.code,name=section_value.name,section_id=section_value.sectionId,division_id=section_value.divisionId,zone_id=section_value.zoneId,planning_enabled=section_value.planningEnabled,metrics=section_value.metrics.model_dump(mode="json"),provenance=section_value.provenance)
            properties.update({"corridorId":section_value.corridorId,"fromStation":section_value.fromStation,"toStation":section_value.toStation,"tracks":[track.value for track in section_value.tracks]})
            features.append({"type":"Feature","id":section_value.sectionId,"geometry":section_value.geometry.model_dump(mode="json"),"properties":properties})

    if "segments" in requested_layers:
        for segment in state.network.segments:
            if not geometry_intersects_bbox(segment.geometry,viewport): continue
            parent=sections_by_id.get(segment.sectionId)
            properties=_network_properties(entity_type="SEGMENT",entity_id=segment.segmentId,layer="segments",code=parent.code if parent else segment.segmentId,name=parent.name if parent else segment.segmentId,section_id=segment.sectionId,division_id=segment.divisionId,zone_id=segment.zoneId,planning_enabled=segment.planningEnabled,metrics={"riskScore":segment.riskScore,"maintenancePressure":segment.maintenancePressure,"trafficPressure":segment.trafficPressure,"activeBlock":segment.activeBlock},provenance=segment.provenance)
            properties["segmentId"]=segment.segmentId
            features.append({"type":"Feature","id":segment.segmentId,"geometry":segment.geometry.model_dump(mode="json"),"properties":properties})

    if "stations" in requested_layers:
        for station in state.network.stations:
            if not geometry_intersects_bbox(station.geometry,viewport): continue
            station_sections=[sections_by_id[section_id] for section_id in station.sectionIds if section_id in sections_by_id]
            division_ids=list(dict.fromkeys(section_value.divisionId for section_value in station_sections))
            zone_ids=list(dict.fromkeys(section_value.zoneId for section_value in station_sections))
            properties=_network_properties(entity_type="STATION",entity_id=station.stationId,layer="stations",code=station.code,name=station.name,section_id=None,division_id=division_ids[0] if len(division_ids)==1 else None,zone_id=zone_ids[0] if len(zone_ids)==1 else None,planning_enabled=station.planningEnabled,metrics={},provenance=station.provenance)
            properties.update({"stationId":station.stationId,"sectionIds":station.sectionIds,"divisionIds":division_ids,"zoneIds":zone_ids})
            features.append({"type":"Feature","id":station.stationId,"geometry":station.geometry.model_dump(mode="json"),"properties":properties})

    total_count=len(features)
    features=features[:requested_limit]
    catalogue_provenance=state.network.provenance.model_dump(by_alias=True,mode="json")
    return {"type":"FeatureCollection","features":features,"count":len(features),"totalCount":total_count,"truncated":total_count>requested_limit,"synthetic":catalogue_provenance["synthetic"],"provenance":catalogue_provenance,"query":{"bbox":requested_bbox,"zoom":requested_zoom,"layers":requested_layers,"limit":requested_limit}}
@app.get("/api/v1/network/search")
def search(q:str=Query(""),_:User=Depends(auth)):
    q_lower=q.lower()
    items=[]
    for z in state.network.zones:
        if q_lower in z.code.lower() or q_lower in z.name.lower(): items.append({"entityType":"ZONE","entityId":z.zoneId,"code":z.code,"name":z.name,"zoneId":z.zoneId,"planningEnabled":z.planningEnabled})
    for d in state.network.divisions:
        if q_lower in d.code.lower() or q_lower in d.name.lower(): items.append({"entityType":"DIVISION","entityId":d.divisionId,"code":d.code,"name":d.name,"zoneId":d.zoneId,"divisionId":d.divisionId,"planningEnabled":d.planningEnabled})
    for s in state.network.sections:
        if q_lower in s.code.lower() or q_lower in s.name.lower(): items.append({"entityType":"SECTION","entityId":s.sectionId,"code":s.code,"name":s.name,"zoneId":s.zoneId,"divisionId":s.divisionId,"sectionId":s.sectionId,"planningEnabled":s.planningEnabled})
    for st in state.network.stations:
        if q_lower in st.code.lower() or q_lower in st.name.lower(): items.append({"entityType":"STATION","entityId":st.stationId,"code":st.code,"name":st.name,"stationId":st.stationId,"planningEnabled":st.planningEnabled})
    return {"items":items,"count":len(items),"synthetic":True}
@app.get("/api/v1/opportunities")
def opportunities(_:User=Depends(auth)):
    try:
        from opportunity_engine import detect
        results=detect(state.world())
        return {"items":[o.model_dump(by_alias=True,mode="json") if hasattr(o,"model_dump") else o for o in results],"count":len(results),"synthetic":True}
    except (ImportError,AttributeError,TypeError):
        raise HTTPException(503,{"code":"ENGINE_UNAVAILABLE","message":"opportunity engine is unavailable"})
@app.get("/api/v1/bundles")
def bundles(_:User=Depends(auth)):
    try:
        from opportunity_engine import detect
        from bundling_engine import build
        from risk_engine import score_all
        world=state.world()
        priority={task_id:result.score for task_id,result in score_all(world).items()}
        results=build(world,detect(world),priority)
        return {"items":[b.model_dump(by_alias=True,mode="json") if hasattr(b,"model_dump") else b for b in results],"count":len(results),"synthetic":True}
    except (ImportError,AttributeError,TypeError):
        raise HTTPException(503,{"code":"ENGINE_UNAVAILABLE","message":"bundling engine is unavailable"})
@app.post("/api/v1/simulator/scenarios/{scenario}")
def simulate_scenario(scenario:str,body:dict[str,Any]=Body(default_factory=dict),user:User=Depends(allow("PLANNER","CONTROL_OFFICER"))):
    try:
        from simulator import SCENARIOS
    except ImportError:
        raise HTTPException(503,{"code":"ENGINE_UNAVAILABLE","message":"simulator is unavailable"})
    fn=SCENARIOS.get(scenario)
    if fn is None:
        raise HTTPException(404,{"code":"UNKNOWN_SCENARIO","message":f"unknown simulator scenario '{scenario}'"})
    try:
        world=fn(state.world(),**body) if body else fn(state.world())
    except TypeError as exc:
        raise HTTPException(422,{"code":"VALIDATION_ERROR","message":str(exc)})
    return {"scenario":scenario,"world":world.model_dump(by_alias=True,mode="json"),"synthetic":True}
@app.get("/api/v1/optimization/{run_id}")
@app.get("/api/v1/optimization/status/{run_id}")
def optimization_status(run_id:str,_:User=Depends(auth)):
    if run_id not in state.runs: raise HTTPException(404,{"code":"NOT_FOUND","message":"optimization run not found"})
    return state.runs[run_id]

def decide(plan_id,body,target,user):
    with state.transaction():
        source=state.plans.get(plan_id)
        if source is None: raise HTTPException(404,{"code":"NOT_FOUND","message":"plan not found"})
        if body.expected_version is not None and body.expected_version!=source.planVersion: raise HTTPException(409,{"code":"STALE_PLAN_VERSION","message":"plan version is stale"})
        if source.status==PlanStatus.APPROVED: raise HTTPException(409,{"code":"PLAN_ALREADY_APPROVED","message":"approved plan is immutable"})
        if target==PlanStatus.APPROVED:
            sections={b.sectionId for b in source.blocks}
            for other_id,other in state.plans.items():
                if other_id!=plan_id and other.status==PlanStatus.APPROVED and sections.intersection({b.sectionId for b in other.blocks}):
                    raise HTTPException(409,{"code":"PLAN_VERSION_CONFLICT","message":"an approved plan already covers this territory"})
        state.plan_versions.setdefault(f"{plan_id}:v{source.planVersion}",copy.deepcopy(source)); decided=source.model_copy(deep=True)
        decided.planVersion+=1; decided.parentPlanId=source.planId
        decided.status=target
        stamp=f"{target.value} by {user.user_id} at {datetime.now(timezone.utc).isoformat()}" + (f" ({body.reason})" if body.reason else "")
        decided.provenance=f"{decided.provenance}\n{stamp}" if decided.provenance else stamp
        state.plan_versions[f"{plan_id}:v{decided.planVersion}"]=copy.deepcopy(decided); state.plans[plan_id]=copy.deepcopy(decided)
        if target==PlanStatus.APPROVED:
            for a in decided.assignments: state.assignments[a.taskId]={"id":a.taskId,"planId":plan_id,"planVersion":decided.planVersion,"taskId":a.taskId,"blockId":a.blockId,"status":"READY","start":a.start,"end":a.end,"synthetic":True}
        state.emit(f"PLAN_{target.value}",plan_id,decided.model_dump(mode="json"),user.user_id,body.reason,source.model_dump(mode="json"),decided.planVersion)
        return decided

@app.post("/api/v1/block-plans/{plan_id}/approve")
def approve(plan_id:str,body:Decision=Decision(),user:User=Depends(allow("CONTROL_OFFICER"))): return decide(plan_id,body,PlanStatus.APPROVED,user)
@app.post("/api/v1/block-plans/{plan_id}/reject")
def reject(plan_id:str,body:Decision=Decision(),user:User=Depends(allow("CONTROL_OFFICER"))): return decide(plan_id,body,PlanStatus.REJECTED,user)
@app.post("/api/v1/block-plans/{plan_id}/request-revision")
def request_revision(plan_id:str,body:Decision=Decision(),user:User=Depends(allow("CONTROL_OFFICER","PLANNER"))): return decide(plan_id,body,PlanStatus.PROPOSED,user)
@app.post("/api/v1/block-plans/{plan_id}/lock")
def lock(plan_id:str,user:User=Depends(allow("CONTROL_OFFICER"))):
    with state.transaction():
        plan=state.plans.get(plan_id)
        if plan is None: raise HTTPException(404,{"code":"NOT_FOUND","message":"plan not found"})
        for a in plan.assignments:
            if a.taskId in state.tasks: state.tasks[a.taskId]=state.tasks[a.taskId].model_copy(update={"locked":True})
        ids=[a.taskId for a in plan.assignments]; state.emit("PLAN_LOCKED",plan_id,{"taskIds":ids},user.user_id,version=plan.planVersion); return {"planId":plan_id,"lockedTaskIds":ids}

@app.get("/api/v1/work/assignments")
def work_assignments(_:User=Depends(auth)): return listed(state.assignments)
@app.post("/api/v1/work/assignments/{assignment_id}/updates")
@app.post("/api/v1/work/{assignment_id}/update")
def work_update(assignment_id:str,body:WorkUpdate,user:User=Depends(allow("FIELD_SUPERVISOR","ENGINEERING","SIGNAL_TELECOM","TRACTION","CONTROL_OFFICER"))):
    with state.transaction():
        assignment=state.assignments.get(assignment_id)
        if assignment is None: raise HTTPException(404,{"code":"NOT_FOUND","message":"assignment not found"})
        before=copy.deepcopy(assignment); assignment["status"]=body.status.value; assignment["note"]=body.note
        if assignment["taskId"] in state.tasks: state.tasks[assignment["taskId"]]=state.tasks[assignment["taskId"]].model_copy(update={"status":body.status,"locked":body.status in {TaskStatus.STARTED,TaskStatus.COMPLETED}})
        state.emit(f"TASK_{body.status.value}",assignment["taskId"],assignment,user.user_id,body.note,before); return assignment

@app.post("/api/v1/emergencies")
def create_emergency(body:EmergencyRequest,user:User=Depends(allow("CONTROL_OFFICER","ENGINEERING","SIGNAL_TELECOM","TRACTION","FIELD_SUPERVISOR"))):
    eid="EMG-"+hashlib.sha1(body.model_dump_json(by_alias=True).encode()).hexdigest()[:8].upper(); task=MaintenanceTask(taskId=eid,department=Department.ENGG,assetId=body.asset_id,corridorId=body.corridor_id,sectionId=body.section_id,track=Track.DOWN,kmStart=72.4,kmEnd=72.41,taskType=TaskType.RAIL_REPLACEMENT,severity=10,criticality=10,dueMinute=body.duration_minutes,estimatedDuration=body.duration_minutes,status=TaskStatus.PENDING,blockType=BlockType.EMERGENCY,isEmergency=True,detectedAtMinute=0)
    with state.transaction(): state.emergencies[eid]={"id":eid,"request":body.model_dump(mode="json"),"task":task.model_dump(mode="json"),"synthetic":True}; state.emit("EMERGENCY_CREATED",eid,state.emergencies[eid],user.user_id)
    return {"id":eid,"replanRequired":True,"synthetic":True}

@app.post("/api/v1/replanning/generate")
def replan_generate(body:ReplanRequest,user:User=Depends(allow("CONTROL_OFFICER","PLANNER"))):
    functions=replanner_functions()
    if functions is None: raise HTTPException(503,{"code":"OPTIMIZER_UNAVAILABLE","message":"canonical replanner is unavailable"})
    parent=state.plans.get(body.parent_plan_id); emergency=state.emergencies.get(body.emergency_id)
    if parent is None: raise HTTPException(404,{"code":"NOT_FOUND","message":"parent plan not found"})
    if emergency is None: raise HTTPException(400,{"code":"EMERGENCY_CONTEXT_REQUIRED","message":"persisted emergency is required"})
    insert_emergency,canonical_replan=functions; world=insert_emergency(state.world(),MaintenanceTask.model_validate(emergency["task"])); new,diff=canonical_replan(world,copy.deepcopy(parent),now=body.now_minute,reason=body.reason)
    payload={"added":diff.added,"removed":diff.removed,"moved":diff.moved,"unchanged":diff.unchanged,"displaced":diff.displaced,"metricDeltas":diff.metric_deltas}
    with state.transaction(): state.plans[new.planId]=copy.deepcopy(new); state.plan_versions[f"{new.planId}:v{new.planVersion}"]=copy.deepcopy(new); state.emit("PLAN_REOPTIMIZED",new.planId,payload,user.user_id,body.reason,parent.model_dump(mode="json"),new.planVersion)
    return {"plan":new.model_dump(by_alias=True,mode="json"),"diff":payload,"parentPreserved":True}

@app.get("/api/v1/notifications")
def notifications(_:User=Depends(auth)): return listed(state.notifications)
@app.post("/api/v1/notifications/{notification_id}/acknowledge")
@app.post("/api/v1/notifications/{notification_id}/ack")
def acknowledge(notification_id:str,user:User=Depends(auth)):
    with state.transaction():
        note=state.notifications.get(notification_id)
        if note is None: raise HTTPException(404,{"code":"NOT_FOUND","message":"notification not found"})
        before=copy.deepcopy(note); note["acknowledged"]=True; note["acknowledgedBy"]=user.user_id; state.emit("NOTIFICATION_ACKNOWLEDGED",notification_id,note,user.user_id,before=before,notify=False); return note
@app.get("/api/v1/analytics")
@app.get("/api/v1/analytics/summary")
def analytics(_:User=Depends(auth)): return {"label":"Synthetic Hackathon Simulation","tasks":len(state.tasks),"defects":len(state.defects),"criticalTasks":sum(t.severity>=9 for t in state.tasks.values()),"overdueTasks":sum(t.overdueDays>0 for t in state.tasks.values()),"completedTasks":sum(t.status==TaskStatus.COMPLETED for t in state.tasks.values()),"maintenanceDebt":sum(t.overdueDays*t.criticality for t in state.tasks.values()),"synthetic":True}
@app.get("/api/v1/integrations/status")
def integration_status(_:User=Depends(auth)): return {"synthetic":True,"scenario":"GZB_ALJN_DEMO","sources":{n:a.health() for n,a in state.adapters.items()},"ingestion":state.ingestion_records}
@app.get("/api/v1/events")
def events(after:int=0,_:User=Depends(auth)): return {"events":[e for e in state.events if e["sequence"]>after],"nextSequence":len(state.events)}
@app.post("/api/v1/events/replay")
def replay(after:int=0,user:User=Depends(auth)): return events(after,user)

async def websocket_events(socket:WebSocket):
    user,role=socket.headers.get("x-railos-user"),socket.headers.get("x-railos-role")
    if not user: await socket.close(code=4401); return
    if role not in VALID_ROLES: await socket.close(code=4403); return
    await socket.accept(); queue=asyncio.Queue(maxsize=100); state.subscribers.append(queue)
    try:
        await socket.send_json({"events":state.events,"nextSequence":len(state.events)})
        while True: await socket.send_json(await queue.get())
    except WebSocketDisconnect: pass
    finally:
        if queue in state.subscribers: state.subscribers.remove(queue)
@app.websocket("/api/v1/events/ws")
async def events_ws(socket:WebSocket): await websocket_events(socket)
@app.websocket("/api/v1/ws")
async def legacy_ws(socket:WebSocket): await websocket_events(socket)
