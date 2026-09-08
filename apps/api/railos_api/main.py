"""RailOS API: human-governed orchestration over canonical RailOS contracts."""
from __future__ import annotations

import asyncio, copy, hashlib, json, os, threading, uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from railos_model import (Asset, BlockSection, BlockType, BlockWindow, Corridor,
    Department, Defect, LineConfig, MaintenanceTask, ObjectiveProfile, Plan,
    PlanStatus, ScenarioWorld, Severity, TaskStatus, TaskType, Track, TrainClass,
    TrainMovement)

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
    section_id: str = "SEC-GZB-ALJN"
    asset_id: str = "ASSET-001"
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
            for name in ("corridors", "assets", "tasks", "defects", "trains", "windows", "plans", "plan_versions", "runs", "notifications", "idempotency", "emergencies", "assignments", "ingestion_records"):
                setattr(self, name, {})
            self.events, self.audit = [], []
            self._seed()
            self.commit()

    def _seed(self):
        from integrations.adapters import ADAPTERS
        self.adapters = ADAPTERS
        for name, adapter in ADAPTERS.items():
            self.ingestion_records[name] = adapter.normalize(adapter.fetch("seed")[0])
        section = BlockSection(sectionId="SEC-GZB-ALJN", fromStation="GZB", toStation="ALJN", startM=0, endM=100000, tracks=[Track.UP, Track.DOWN])
        self.corridors["GZB-ALJN"] = Corridor(corridorId="GZB-ALJN", name="Ghaziabad–Aligarh", lineConfig=LineConfig.DOUBLE, tracks=[Track.UP, Track.DOWN], sections=[section])
        for i in range(12):
            key = f"ASSET-{i+1:03d}"
            self.assets[key] = Asset(assetId=key, assetType="TRACK", sectionId=section.sectionId, track=Track.UP if i%2 else Track.DOWN, locationM=72000+i*100, criticality=7+i%4)
        for i in range(267):
            key = f"TASK-{i+1:03d}"
            self.tasks[key] = MaintenanceTask(taskId=key, department=[Department.ENGG, Department.SNT, Department.TRD][i%3], assetId=f"ASSET-{i%12+1:03d}", corridorId="GZB-ALJN", sectionId=section.sectionId, track=Track.UP if i%2 else Track.DOWN, kmStart=72+i/1000, kmEnd=72.01+i/1000, taskType=TaskType.TAMPING, severity=10 if i<17 else 4, criticality=9 if i<17 else 5, dueMinute=100+i, estimatedDuration=30+i%4*15, status=TaskStatus.PENDING, overdueDays=5 if i<29 else 0)
        for i in range(34):
            key = f"DEFECT-{i+1:03d}"
            self.defects[key] = Defect(defectId=key, assetId=f"ASSET-{i%12+1:03d}", sectionId=section.sectionId, severityCode=Severity.IMR if i<17 else Severity.OBS, detectedAtMinute=i)
        for i in range(41):
            key = f"MOV-{i+1:03d}"
            self.trains[key] = TrainMovement(trainId=key, sectionId=section.sectionId, track=Track.UP if i%2 else Track.DOWN, entry=i*30, exit=i*30+20, trainClass=TrainClass.RAJDHANI if i==0 else TrainClass.GOODS if i%4==0 else TrainClass.MAIL_EXPRESS, priority=10 if i==0 else 5)
        for i in range(12):
            key = f"WIN-{i+1:03d}"
            self.windows[key] = BlockWindow(windowId=key, sectionId=section.sectionId, track=Track.UP if i%2 else Track.DOWN, start=60+i*120, end=150+i*120)
        self.emit("DEMO_RESET", "demo", {"tasks":267,"defects":34,"movements":41,"windows":12}, occurred_at=DEMO_NOW, notify=False)

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
        return ScenarioWorld(horizonStartIso=DEMO_EPOCH, corridors=list(self.corridors.values()), assets=list(self.assets.values()), tasks=list(self.tasks.values()), defects=list(self.defects.values()), trains=list(self.trains.values()), windows=list(self.windows.values()))

    def serializable(self):
        def dump(values): return {k:(v.model_dump(mode="json") if hasattr(v,"model_dump") else v) for k,v in values.items()}
        result = {name:dump(getattr(self,name)) for name in ("corridors","assets","tasks","defects","trains","windows","plans","plan_versions","runs","notifications","idempotency","emergencies","assignments","ingestion_records")}
        return result | {"events":self.events,"audit":self.audit}

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
def reset(_:User=Depends(allow("ADMIN"))): state.reset(); return {"status":"reset","counts":{"tasks":267,"defects":34,"movements":41,"windows":12,"critical":17,"overdue":29},"synthetic":True}

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
    with state.transaction():
        if key and key in state.idempotency:
            saved=state.idempotency[key]
            if saved["fingerprint"]!=fingerprint: raise HTTPException(409,{"code":"IDEMPOTENCY_CONFLICT","message":"key reused with a different request"})
            return saved["response"]
        port=optimizer_port()
        if port is None: raise HTTPException(503,{"code":"OPTIMIZER_UNAVAILABLE","message":"architecture-owned optimizer is unavailable"})
        candidates=[port.generate(state.world(),profile) for profile in (ObjectiveProfile.SAFETY_FIRST,ObjectiveProfile.BALANCED,ObjectiveProfile.OPERATIONS_FIRST)]
        if candidates and all("INFEASIBLE" in p.solverStatus.upper() for p in candidates):
            raise HTTPException(422,{"code":"SOLVER_INFEASIBLE","message":"optimizer found no feasible plan","details":{"warnings":[w for p in candidates for w in p.warnings]}})
        for plan in candidates: state.plans[plan.planId]=copy.deepcopy(plan); state.plan_versions[f"{plan.planId}:v{plan.planVersion}"]=copy.deepcopy(plan)
        run_id=f"RUN-{len(state.runs)+1:06d}"; run={"id":run_id,"status":"COMPLETED","solverStatus":[p.solverStatus for p in candidates],"candidatePlanIds":[p.planId for p in candidates],"createdAt":datetime.now(timezone.utc).isoformat(),"synthetic":True}; state.runs[run_id]=run; state.emit("PLAN_GENERATED",run_id,run,user.user_id)
        response={"optimizationRun":run,"candidatePlans":[p.model_dump(by_alias=True,mode="json") for p in candidates],"warnings":[w for p in candidates for w in p.warnings]}
        if key: state.idempotency[key]={"fingerprint":fingerprint,"response":response}
        return response

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
        decided.status=target; state.plan_versions[f"{plan_id}:v{decided.planVersion}"]=copy.deepcopy(decided); state.plans[plan_id]=copy.deepcopy(decided)
        if target==PlanStatus.APPROVED:
            for a in decided.assignments: state.assignments[a.taskId]={"id":a.taskId,"planId":plan_id,"planVersion":decided.planVersion,"taskId":a.taskId,"blockId":a.blockId,"status":"READY","start":a.start,"end":a.end,"synthetic":True}
        state.emit(f"PLAN_{target.value}",plan_id,decided.model_dump(mode="json"),user.user_id,body.reason,source.model_dump(mode="json"),decided.planVersion)
        return decided

@app.post("/api/v1/block-plans/{plan_id}/approve")
def approve(plan_id:str,body:Decision=Decision(),user:User=Depends(allow("CONTROL_OFFICER"))): return decide(plan_id,body,PlanStatus.APPROVED,user)
@app.post("/api/v1/block-plans/{plan_id}/reject")
def reject(plan_id:str,body:Decision=Decision(),user:User=Depends(allow("CONTROL_OFFICER"))): return decide(plan_id,body,PlanStatus.SUPERSEDED,user)
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
