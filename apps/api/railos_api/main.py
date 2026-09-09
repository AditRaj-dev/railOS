"""RailOS API: human-governed orchestration over canonical RailOS contracts."""
from __future__ import annotations

import asyncio, copy, hashlib, json, math, os, re, threading, uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from railos_data import geometry_intersects_bbox
from railos_model import (
    Asset, AuthoritySignature, BlockBurst, BlockRequest, BlockRequestStatus,
    BlockType, BlockWindow,
    CorrespondenceTest, Corridor, DataProvenance, Defect, Dependency, Department,
    EvidenceItem, FitnessCertificate, FormT351, GoodsForecast, MaintenanceTask,
    MachineType,
    NetworkCatalog, ObjectiveProfile, PermitToWork, Plan, PlanStatus,
    Possession, PossessionState, PossessionTransition, ProtectionRecord,
    Resource, SanctionAuthority, SanctionChain, ScenarioWorld, Severity,
    SignatureDecision, TaskStatus, TaskType, Track, TrainMovement,
    WorkExecutionStatus, WorkStep,
)
from railos_model.enums import MIN_MACHINE_BLOCK_MINUTES
from .auth import decode_access_token
from .roles import OPERATIONAL_ROLES as VALID_ROLES, normalize_role
from .possession import (
    AUTHORITY_ROLES,
    CORRESPONDENCE_TEST,
    ONLINE_AUTHORITY_ACTIONS,
    PTW_LEAD_IN,
    ROLE_AUTHORITIES,
    SR_DAY_SPEEDS_KMPH,
    T351_LEAD_IN,
    TRANSITIONS,
    TRANSITION_TABLE,
    build_possession_view,
    action_already_applied,
    check_precondition,
    compute_handback_checklist,
    compute_overrun_minutes,
    derive_required_authorities,
    get_allowed_actions_for_role,
    parse_datetime,
)

DEMO_EPOCH = "2026-09-09T00:00:00+05:30"
DEMO_NOW = "2026-09-08T06:00:00+00:00"

NOTIFICATION_ROUTING: dict[str, str] = {
    "BLOCK_REQUEST_CREATED": "CONTROL_OFFICER",
    "BLOCK_REQUEST_STATUS_UPDATED": "CONTROL_OFFICER",
    "T351_REQUESTED": "STATION_MASTER",
    "T351_ISSUED": "STATION_MASTER",
    "T351_ENDORSED": "FIELD_SUPERVISOR",
    "PTW_REQUESTED": "TPC",
    "PTW_EARTHED": "TPC",
    "PTW_ISSUED": "FIELD_SUPERVISOR",
    "PTW_RODS_REMOVED": "TPC",
    "PTW_CANCELLED": "FIELD_SUPERVISOR",
    "POSSESSION_CLEARANCE_REQUESTED": "CONTROL_OFFICER",
    "POSSESSION_DEFERRED": "FIELD_SUPERVISOR",
    "POSSESSION_CLEARANCE_GRANTED": "FIELD_SUPERVISOR",
    "POSSESSION_OVERRUN": "CONTROL_OFFICER",
    "POSSESSION_HANDBACK_REQUESTED": "TPC",
    "CORRESPONDENCE_TEST_REQUIRED": "SIGNAL_TELECOM",
    "FITNESS_CERTIFICATE_REQUIRED": "ENGINEERING",
    "STATION_CLOSE_REQUIRED": "STATION_MASTER",
    "POSSESSION_CLOSED": "CONTROL_OFFICER",
    "BLOCK_BURST_RECORDED": "CONTROL_OFFICER",
    "PLAN_SANCTION_REQUIRED": "MANAGEMENT",
    "PLAN_SANCTION_PARTIAL": "CONTROL_OFFICER",
    "PLAN_SANCTION_REFUSED": "CONTROL_OFFICER",
    # Possession endpoints emit namespaced events.  Keep the short legacy
    # names above for connector/event-bus callers, but route both forms so a
    # T/351/PTW request cannot silently fall through to the supervisor.
    "POSSESSION_ISSUE_T351": "STATION_MASTER",
    "POSSESSION_ENDORSE_T351": "FIELD_SUPERVISOR",
    "POSSESSION_CONFIRM_EARTHING": "TPC",
    "POSSESSION_ISSUE_PTW": "FIELD_SUPERVISOR",
    "POSSESSION_REMOVE_DISCHARGE_RODS": "TPC",
    "POSSESSION_CANCEL_PTW": "FIELD_SUPERVISOR",
    "POSSESSION_RECONNECT_T351": "FIELD_SUPERVISOR",
    "POSSESSION_RE_ENERGISE": "FIELD_SUPERVISOR",
    "POSSESSION_REQUEST_CLEARANCE": "CONTROL_OFFICER",
    "POSSESSION_DEFER": "FIELD_SUPERVISOR",
    "POSSESSION_GRANT_CLEARANCE": "FIELD_SUPERVISOR",
    "POSSESSION_REQUEST_HANDBACK": "TPC",
    "POSSESSION_START_TESTING": "SIGNAL_TELECOM",
    "POSSESSION_RECORD_CORRESPONDENCE_TEST": "ENGINEERING",
    "POSSESSION_CERTIFY_FITNESS": "STATION_MASTER",
    "POSSESSION_STATION_CLOSE": "CONTROL_OFFICER",
    "POSSESSION_CLOSE": "CONTROL_OFFICER",
    "POSSESSION_SANCTIONED": "FIELD_SUPERVISOR",
    "POSSESSION_START_WORK": "FIELD_SUPERVISOR",
    "POSSESSION_DECLARE_OVERRUN": "CONTROL_OFFICER",
}

COLLECTIONS = (
    "corridors", "assets", "tasks", "defects", "trains", "goods",
    "windows", "resources", "dependencies", "plans", "plan_versions",
    "runs", "notifications", "idempotency", "emergencies", "assignments",
    "ingestion_records", "sanctions", "sanction_versions", "possessions",
    "block_bursts", "block_requests", "evidence_items", "work_steps", "upload_sessions",
)

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


class BlockRequestCreate(DTO):
    """Client input for the guided ticket composer.

    The server owns optimizer flags (machine, PTW/T351, escorts, and task
    defaults); clients submit only the operational facts they know.
    """

    request_id: str | None = Field(default=None, min_length=1)
    department: Department
    corridor_id: str = "GZB-ALJN"
    section_id: str
    asset_id: str | None = None
    track: Track
    km_start: float = Field(ge=0)
    km_end: float = Field(gt=0)
    task_type: TaskType
    severity: int = Field(ge=1, le=10)
    criticality: int | None = Field(default=None, ge=1, le=10)
    estimated_duration: int = Field(gt=0)
    requested_start: int = Field(ge=0)
    requested_end: int = Field(gt=0)
    due_minute: int | None = Field(default=None, ge=0)
    block_required: bool = True
    block_type: BlockType = BlockType.TRAFFIC
    reason: str = ""


class BlockRequestStatusUpdate(DTO):
    status: BlockRequestStatus
    reason: str = ""

class Decision(DTO):
    reason: str = ""
    expected_version: int | None = None
    authority: SanctionAuthority | None = None
    form_reference: str = ""

class SanctionSignRequest(DTO):
    authority: SanctionAuthority | None = None
    decision: SignatureDecision = SignatureDecision.GRANTED
    reason: str = ""
    form_reference: str = ""
    expected_version: int | None = None

class PossessionTransitionRequest(DTO):
    action: str = ""
    client_event_at_utc: str | None = None
    note: str = ""
    form_reference: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
    duration_minutes: int | None = None
    tsr_speed_kmph: int | None = None
    detonator_count: int | None = None
    deferred_until_utc: str | None = None
    cause_category: str | None = None

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
    execution_status: WorkExecutionStatus | None = None
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
    department: Department | None = None


DEPARTMENT_TASK_TYPES: dict[Department, frozenset[TaskType]] = {
    Department.ENGG: frozenset({
        TaskType.TAMPING, TaskType.DEEP_SCREENING, TaskType.RAIL_REPLACEMENT,
        TaskType.SLEEPER_RENEWAL, TaskType.TURNOUT_RENEWAL,
        TaskType.DESTRESSING, TaskType.USFD_INSPECTION,
    }),
    Department.SNT: frozenset({
        TaskType.POINT_MACHINE_MAINT, TaskType.TRACK_CIRCUIT_BOND,
        TaskType.AXLE_COUNTER_CALIB, TaskType.GJ_REPLACEMENT,
        TaskType.INTERLOCKING_WORK, TaskType.SNT_DISCONNECTION,
        TaskType.SNT_RECONNECTION,
    }),
    Department.TRD: frozenset({
        TaskType.OHE_INSPECTION, TaskType.CATENARY_REPLACEMENT,
        TaskType.OHE_BRACKET_ADJUST, TaskType.OHE_SLEWING,
        TaskType.TRD_ISOLATION,
    }),
}

TASK_ASSET_TYPES: dict[TaskType, str] = {
    TaskType.POINT_MACHINE_MAINT: "POINT",
    TaskType.TURNOUT_RENEWAL: "POINT",
    TaskType.AXLE_COUNTER_CALIB: "AXLE_COUNTER",
    TaskType.OHE_INSPECTION: "OHE_ELEMENTARY_SECTION",
    TaskType.CATENARY_REPLACEMENT: "OHE_ELEMENTARY_SECTION",
    TaskType.OHE_BRACKET_ADJUST: "OHE_ELEMENTARY_SECTION",
    TaskType.OHE_SLEWING: "OHE_ELEMENTARY_SECTION",
    TaskType.TRD_ISOLATION: "OHE_ELEMENTARY_SECTION",
}

# These are deliberately server-owned.  A client may request a task type but
# may not smuggle optimizer safety flags through the ticket payload.
TASK_REQUIREMENTS: dict[TaskType, dict[str, Any]] = {
    TaskType.TAMPING: {"machineType": MachineType.CSM, "requiresSntEscort": True, "imposesSpeedRestriction": True},
    TaskType.DEEP_SCREENING: {"machineType": MachineType.BCM, "requiresPTW": True, "infringesAdjacent": True, "imposesSpeedRestriction": True},
    TaskType.RAIL_REPLACEMENT: {"imposesSpeedRestriction": True},
    TaskType.TURNOUT_RENEWAL: {"requiresPTW": True, "requiresT351": True, "imposesSpeedRestriction": True},
    TaskType.POINT_MACHINE_MAINT: {"requiresT351": True},
    TaskType.SNT_DISCONNECTION: {"requiresT351": True},
    TaskType.SNT_RECONNECTION: {"requiresT351": True},
    TaskType.OHE_INSPECTION: {"machineType": MachineType.TOWER_WAGON},
    TaskType.CATENARY_REPLACEMENT: {"machineType": MachineType.TOWER_WAGON, "requiresPTW": True},
    TaskType.TRD_ISOLATION: {"requiresPTW": True},
    TaskType.OHE_BRACKET_ADJUST: {"requiresPTW": True},
    TaskType.OHE_SLEWING: {"requiresPTW": True},
}

ROLE_DEPARTMENT: dict[str, Department] = {
    "ENGINEERING": Department.ENGG,
    "SIGNAL_TELECOM": Department.SNT,
    "TRACTION": Department.TRD,
}

BROAD_TICKET_ROLES = frozenset({"ADMIN", "CONTROL_OFFICER", "PLANNER", "MANAGEMENT"})
SUBMITTER_TICKET_ROLES = frozenset({
    "ENGINEERING", "SIGNAL_TELECOM", "TRACTION", "FIELD_SUPERVISOR",
    "ADMIN", "CONTROL_OFFICER", "PLANNER",
})


def _department_scope(user: User) -> Department | None:
    """Return the server-owned department scope for a ticket actor."""
    role_department = ROLE_DEPARTMENT.get(normalize_role(user.role))
    if role_department is not None:
        return role_department
    return user.department


def _authorize_ticket_department(user: User, department: Department) -> None:
    role = normalize_role(user.role)
    if role in BROAD_TICKET_ROLES:
        return
    scope = _department_scope(user)
    if role not in SUBMITTER_TICKET_ROLES or scope is None:
        raise HTTPException(403, {
            "code": "DEPARTMENT_SCOPE_REQUIRED",
            "message": "the authenticated department supervisor has no department scope",
        })
    if scope != department:
        raise HTTPException(403, {
            "code": "DEPARTMENT_FORBIDDEN",
            "message": f"role '{role}' may only submit or view {scope.value} requests",
            "details": {"department": department.value, "allowedDepartment": scope.value},
        })


def _request_provenance() -> DataProvenance:
    return DataProvenance(
        synthetic=True,
        label="Synthetic Hackathon Simulation",
        source="RailOS guided ticket intake",
        sourceType="synthetic",
        isOperationallyAuthoritative=False,
        generatedAt=datetime.now(timezone.utc).isoformat(),
    )

class Repository:
    """Atomic deterministic repository used by demo and tests."""
    def __init__(self):
        self.lock = threading.RLock()
        self.subscribers: list[asyncio.Queue] = []
        self.reset()

    def reset(self):
        with self.lock:
            for name in COLLECTIONS:
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

        # Demo field-evidence work steps for TSK-0001 (survives restarts via
        # this repository, unlike the rest of FieldEvidenceState in
        # evidence_routes.py which is session-scoped in-memory auth state).
        self.work_steps = {
            step.stepId: step for step in (
                WorkStep(
                    stepId="stp-101", taskId="TSK-0001", stepIndex=1,
                    title="Pre-work Site Inspection & Ballast Profile",
                    description="Photograph the initial ballast shoulder and check fishplate clearances.",
                    requiresPhoto=True, requiresVideo=False,
                    targetLatitude=28.6139, targetLongitude=77.2090, targetRadiusMeters=100.0,
                    status=WorkExecutionStatus.READY,
                ),
                WorkStep(
                    stepId="stp-102", taskId="TSK-0001", stepIndex=2,
                    title="Tamping Machine Alignment & Depth Verification",
                    description="Photograph tamper tines penetrating sleeper crib to prescribed depth.",
                    requiresPhoto=True, requiresVideo=False,
                    targetLatitude=28.6141, targetLongitude=77.2093, targetRadiusMeters=100.0,
                    status=WorkExecutionStatus.READY,
                ),
                WorkStep(
                    stepId="stp-103", taskId="TSK-0001", stepIndex=3,
                    title="Post-Tamping Final Track Geometry Walkthrough",
                    description="Continuous walkthrough video verifying cross-level, alignment, and track clear of equipment.",
                    requiresPhoto=False, requiresVideo=True,
                    targetLatitude=28.6140, targetLongitude=77.2091, targetRadiusMeters=100.0,
                    status=WorkExecutionStatus.READY,
                ),
            )
        }

        # Seed realistic demo tickets, work steps, and field evidence
        try:
            from .demo_seed import seed_all_demo_data
            from .evidence_routes import object_store, verification_service
            seed_all_demo_data(self, object_store, verification_service)
        except Exception:
            pass

        self.emit("DEMO_RESET", "demo", {
            "tasks": len(self.tasks), "defects": len(self.defects),
            "movements": len(self.trains), "windows": len(self.windows),
            "networkZones": len(self.network.zones),
        }, occurred_at=DEMO_NOW, notify=False)

    @contextmanager
    def transaction(self):
        with self.lock:
            # The memory repository is also the reference implementation for
            # tests and local demos.  Preserve its atomicity promise when a
            # validation/authority guard raises after mutating a nested model.
            # Without this snapshot, a failed final signature or transition
            # could leave a half-written chain visible to the next request.
            snapshot = {
                name: copy.deepcopy(getattr(self, name))
                for name in COLLECTIONS
            }
            events = copy.deepcopy(self.events)
            audit = copy.deepcopy(self.audit)
            try:
                yield
            except Exception as exc:
                # Partial sanction is a deliberate 202 outcome: its
                # collected signature must survive the exception handler.
                if getattr(exc, "commit_transaction", False):
                    self.commit()
                    raise
                for name, value in snapshot.items():
                    setattr(self, name, value)
                self.events = events
                self.audit = audit
                raise
            else:
                self.commit()

    def commit(self):
        pass

    def emit(self, event_type, entity_id, payload, actor="system", reason="", before=None, version=None, occurred_at=None, notify=True, *, recipient_role=None):
        event = {"sequence":len(self.events)+1, "id":f"EVT-{len(self.events)+1:06d}", "type":event_type, "actor":actor, "action":event_type, "entityId":entity_id, "before":copy.deepcopy(before), "after":copy.deepcopy(payload), "planVersion":version, "reason":reason, "occurredAt":occurred_at or datetime.now(timezone.utc).isoformat(), "synthetic":True}
        self.events.append(event); self.audit.append(copy.deepcopy(event))
        if notify:
            nid = f"NTF-{event['sequence']:06d}"
            if recipient_role:
                recip = normalize_role(recipient_role)
            elif event_type in NOTIFICATION_ROUTING:
                recip = NOTIFICATION_ROUTING[event_type]
            else:
                recip = "CONTROL_OFFICER" if event_type.startswith(("PLAN_","EMERGENCY")) else "FIELD_SUPERVISOR"
            self.notifications[nid] = {
                "id": nid,
                "eventId": event["id"],
                "category": "CRITICAL" if event_type in {"EMERGENCY_CREATED", "POSSESSION_OVERRUN"} else "ACTION_REQUIRED",
                "recipientRole": recip,
                "groupingKey": f"{event_type}:{entity_id}",
                "acknowledged": False,
                "createdAt": event["occurredAt"],
                "synthetic": True,
            }
        for queue in list(self.subscribers):
            try: queue.put_nowait(copy.deepcopy(event))
            except asyncio.QueueFull: pass
        return event

    def world(self, task_ids: list[str] | None = None):
        request_by_task = {
            request.linkedTaskId: request
            for request in self.block_requests.values()
            if isinstance(request, BlockRequest)
        }
        excluded_request_tasks = {
            task_id
            for task_id, request in request_by_task.items()
            if request.status in {BlockRequestStatus.REJECTED, BlockRequestStatus.CANCELLED}
        }
        available_tasks = [
            task for task_id, task in self.tasks.items()
            if task_id not in excluded_request_tasks
            and (task_ids is None or task_id in set(task_ids))
        ]
        available_task_ids = {task.taskId for task in available_tasks}
        return ScenarioWorld(
            horizonMinutes=getattr(self, "horizon_minutes", 4320),
            horizonStartIso=getattr(self, "horizon_start_iso", DEMO_EPOCH),
            corridors=list(self.corridors.values()), assets=list(self.assets.values()),
            tasks=available_tasks, defects=list(self.defects.values()),
            trains=list(self.trains.values()), goods=list(self.goods.values()),
            windows=list(self.windows.values()), resources=list(self.resources.values()),
            dependencies=[
                dependency for dependency in self.dependencies.values()
                if dependency.predecessorTaskId in available_task_ids
                and dependency.successorTaskId in available_task_ids
            ],
        )

    def serializable(self):
        def dump(values): return {k:(v.model_dump(mode="json") if hasattr(v,"model_dump") else v) for k,v in values.items()}
        result = {name:dump(getattr(self,name)) for name in COLLECTIONS}
        return result | {
            "network": self.network.model_dump(mode="json"),
            "horizonMinutes": getattr(self, "horizon_minutes", 4320),
            "horizonStartIso": getattr(self, "horizon_start_iso", DEMO_EPOCH),
            "events": self.events,
            "audit": self.audit,
        }

class PostgresRepository(Repository):
    """Persists each atomic application snapshot to PostgreSQL JSONB."""

    # Model registration is intentionally explicit.  A restart must restore
    # the authority-layer collections as typed contracts rather than raw dicts
    # (the memory backend would never expose that failure).
    model_types = {
        "corridors": Corridor, "assets": Asset, "tasks": MaintenanceTask,
        "block_requests": BlockRequest,
        "defects": Defect, "trains": TrainMovement, "windows": BlockWindow,
        "goods": GoodsForecast, "resources": Resource, "dependencies": Dependency,
        "plans": Plan, "plan_versions": Plan,
        "sanctions": SanctionChain, "sanction_versions": SanctionChain,
        "possessions": Possession, "block_bursts": BlockBurst,
        "evidence_items": EvidenceItem, "work_steps": WorkStep,
    }

    def __init__(self):
        url = os.getenv("DATABASE_URL") or os.getenv("RAILOS_DATABASE_URL")
        if not url: raise RuntimeError("DATABASE_URL is required for postgres backend")
        try: import psycopg
        except ImportError as exc: raise RuntimeError("psycopg is required for postgres backend") from exc
        try:
            self.connection = psycopg.connect(url, connect_timeout=3, autocommit=True)
            self.connection.execute("CREATE TABLE IF NOT EXISTS railos_state(namespace text NOT NULL,key text NOT NULL,payload jsonb NOT NULL,version bigint NOT NULL DEFAULT 1,updated_at timestamptz NOT NULL DEFAULT now(),PRIMARY KEY(namespace,key))")
            row = self.connection.execute("SELECT payload FROM railos_state WHERE namespace=%s AND key=%s",("application","snapshot")).fetchone()
        except Exception as exc: raise RuntimeError("postgres connectivity validation failed") from exc
        if row:
            self.lock=threading.RLock(); self.subscribers=[]
            payload=row[0] if isinstance(row[0],dict) else json.loads(row[0])
            # Initialise every collection before loading so snapshots written
            # by an older process (before the possession layer existed) still
            # rehydrate cleanly.
            for name in COLLECTIONS:
                setattr(self, name, {})
            self.events = []
            self.audit = []
            self.network = NetworkCatalog()
            self.horizon_minutes = 4320
            self.horizon_start_iso = DEMO_EPOCH
            for name,values in payload.items():
                if name in {"events","audit"}: setattr(self,name,values); continue
                if name == "network":
                    self.network = NetworkCatalog.model_validate(values)
                    continue
                if name in {"horizon_minutes", "horizon_start_iso", "horizonMinutes", "horizonStartIso"}:
                    setattr(self, "horizon_minutes" if name in {"horizon_minutes", "horizonMinutes"} else "horizon_start_iso", values)
                    continue
                if name not in COLLECTIONS or not isinstance(values, dict):
                    continue
                model=self.model_types.get(name)
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

class PartialSanction(Exception):
    def __init__(self, chain: SanctionChain):
        self.chain = chain
        self.commit_transaction = True

app = FastAPI(title="RailOS API",version="1.0.0",description="Synthetic Hackathon Simulation — decision support; human approval required")

@app.exception_handler(PartialSanction)
def partial_sanction_handler(request, exc: PartialSanction):
    return JSONResponse(status_code=202, content=exc.chain.model_dump(by_alias=True, mode="json"))

cors_origins = [o.strip() for o in os.getenv("RAILOS_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if o.strip()]
cors_regex = os.getenv("RAILOS_CORS_REGEX", r"^https://.*\.vercel\.app$")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=cors_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from .evidence_routes import router as evidence_router
app.include_router(evidence_router)

def auth(
    user: str | None = Header(None, alias="X-RailOS-User"),
    role: str | None = Header(None, alias="X-RailOS-Role"),
    department: str | None = Header(None, alias="X-RailOS-Department"),
    authorization: str | None = Header(None, alias="Authorization"),
):
    """Authenticate both real JWT sessions and the local demo headers.

    The control-center historically used synthetic headers for the planning
    API while the login flow uses Bearer JWTs.  Keeping this compatibility
    boundary in one dependency prevents ticket intake from silently working
    only when logged out.
    """
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(401, {"code": "TOKEN_INVALID", "message": "Bearer token is required"})
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        normalized = normalize_role(payload.get("role"))
        if not user_id:
            raise HTTPException(401, {"code": "TOKEN_INVALID", "message": "Missing token subject"})
        if normalized not in VALID_ROLES:
            raise HTTPException(403, {"code": "FORBIDDEN", "message": "token role is invalid"})
        token_department = payload.get("department")
        try:
            parsed_department = Department(token_department) if token_department else None
        except ValueError as exc:
            raise HTTPException(403, {"code": "FORBIDDEN", "message": "token department is invalid"}) from exc
        return User(userId=user_id, role=normalized, department=parsed_department)

    if not user:
        raise HTTPException(401,{"code":"UNAUTHENTICATED","message":"X-RailOS-User is required"})
    normalized = normalize_role(role)
    if normalized not in VALID_ROLES:
        raise HTTPException(403,{"code":"FORBIDDEN","message":"X-RailOS-Role is missing or invalid"})
    try:
        parsed_department = Department(department) if department else None
    except ValueError as exc:
        raise HTTPException(403, {"code": "FORBIDDEN", "message": "X-RailOS-Department is invalid"}) from exc
    return User(userId=user,role=normalized,department=parsed_department)

def allow(*roles):
    norm_roles = {normalize_role(r) for r in roles}
    def dependency(user:User=Depends(auth)):
        user_role_norm = normalize_role(user.role)
        if user_role_norm not in norm_roles and user_role_norm!="ADMIN": raise HTTPException(403,{"code":"FORBIDDEN","message":"role is not allowed"})
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


def _ticket_actions(request: BlockRequest, user: User) -> list[str]:
    if request.status not in {BlockRequestStatus.REQUESTED, BlockRequestStatus.READY}:
        return []
    if any(request.linkedTaskId in block.taskIds for plan in state.plans.values() for block in plan.blocks):
        return []
    manager = normalize_role(user.role) in {"ADMIN", "CONTROL_OFFICER", "PLANNER"}
    actions = ["ACCEPT", "REJECT"] if manager and request.status == BlockRequestStatus.REQUESTED else []
    if manager or request.requestedBy == user.user_id:
        actions.append("CANCEL")
    return actions


def _ticket_view(request: BlockRequest, user: User | None = None) -> dict[str, Any]:
    payload = request.model_dump(by_alias=True, mode="json")
    task = state.tasks.get(request.linkedTaskId)
    payload["linkedTask"] = task.model_dump(by_alias=True, mode="json") if task else None
    payload["allowedActions"] = _ticket_actions(request, user) if user else []
    return payload


def _resolve_request_asset(body: BlockRequestCreate) -> Asset:
    if body.asset_id:
        asset = state.assets.get(body.asset_id)
        if asset is None:
            raise HTTPException(422, {
                "code": "UNKNOWN_ASSET",
                "message": "the selected asset does not exist",
                "details": {"field": "assetId", "assetId": body.asset_id},
            })
        if asset.sectionId != body.section_id:
            raise HTTPException(422, {
                "code": "ASSET_SECTION_MISMATCH",
                "message": "the selected asset is not in the requested section",
                "details": {"field": "assetId", "sectionId": body.section_id},
            })
        if asset.track is not None and asset.track != body.track:
            raise HTTPException(422, {
                "code": "ASSET_TRACK_MISMATCH",
                "message": "the selected asset is not on the requested track",
                "details": {"field": "assetId", "track": body.track.value},
            })
        return asset

    expected_type = TASK_ASSET_TYPES.get(body.task_type, "TRACK_SECTION")
    candidates = [
        asset for asset in state.assets.values()
        if asset.sectionId == body.section_id
        and asset.assetType == expected_type
        and (asset.track is None or asset.track == body.track)
    ]
    if len(candidates) != 1:
        raise HTTPException(422, {
            "code": "ASSET_REQUIRED",
            "message": "select the asset that identifies the work location",
            "details": {
                "field": "assetId",
                "candidateAssetIds": [asset.assetId for asset in candidates],
                "assetType": expected_type,
            },
        })
    return candidates[0]


def _resolve_request_section(body: BlockRequestCreate):
    """The corridor's own section record, or a 422 naming what is wrong.

    Runs before asset resolution: the demo catalogue carries overview-only
    sections that no corridor plans, and answering those with ASSET_REQUIRED
    sent operators hunting for an asset that was never the problem.
    """
    corridor = state.corridors.get(body.corridor_id)
    if corridor is None:
        raise HTTPException(422, {
            "code": "UNKNOWN_CORRIDOR",
            "message": "the selected corridor does not exist",
            "details": {"field": "corridorId", "corridorId": body.corridor_id},
        })
    section = next((candidate for candidate in corridor.sections if candidate.sectionId == body.section_id), None)
    if section is None:
        raise HTTPException(422, {
            "code": "SECTION_CORRIDOR_MISMATCH",
            "message": f"section {body.section_id} is not planable on corridor {body.corridor_id}",
            "details": {
                "field": "sectionId",
                "sectionId": body.section_id,
                "corridorId": body.corridor_id,
                "sectionIds": [candidate.sectionId for candidate in corridor.sections],
            },
        })
    if body.track not in section.tracks:
        raise HTTPException(422, {
            "code": "TRACK_NOT_ON_SECTION",
            "message": f"section {body.section_id} has no {body.track.value} track",
            "details": {
                "field": "track",
                "sectionId": body.section_id,
                "tracks": [track.value for track in section.tracks],
            },
        })
    return section


def _validate_request_location(body: BlockRequestCreate, asset: Asset, section) -> None:
    if body.km_end * 1000 > section.endM or body.km_start * 1000 < section.startM:
        raise HTTPException(422, {
            "code": "KM_OUT_OF_SECTION",
            "message": "the kilometre range must remain inside the selected section",
            "details": {
                "field": "kmStart/kmEnd",
                "sectionId": section.sectionId,
                "minKm": section.startM / 1000,
                "maxKm": section.endM / 1000,
            },
        })
    if asset.locationM < section.startM or asset.locationM > section.endM:
        raise HTTPException(422, {
            "code": "ASSET_OUTSIDE_SECTION",
            "message": "the selected asset is outside the selected section",
            "details": {"field": "assetId", "sectionId": section.sectionId},
        })


def _build_linked_task(body: BlockRequestCreate, request_id: str, asset: Asset) -> MaintenanceTask:
    requirements = TASK_REQUIREMENTS.get(body.task_type, {})
    due_minute = body.due_minute if body.due_minute is not None else body.requested_end
    try:
        return MaintenanceTask(
            taskId=f"TKT-{request_id}",
            department=body.department,
            assetId=asset.assetId,
            corridorId=body.corridor_id,
            sectionId=body.section_id,
            track=body.track,
            kmStart=body.km_start,
            kmEnd=body.km_end,
            taskType=body.task_type,
            severity=body.severity,
            criticality=body.criticality if body.criticality is not None else body.severity,
            dueMinute=due_minute,
            estimatedDuration=body.estimated_duration,
            blockRequired=body.block_required,
            blockType=body.block_type,
            status=TaskStatus.PENDING,
            **requirements,
        )
    except ValueError as exc:
        # The pydantic ValueError names an internal task id and machine enum;
        # an SSE filling in a ticket needs the number and the rule, not that.
        floor = _task_type_min_duration(body.task_type)
        message = (
            f"{body.task_type.value.replace('_', ' ').title()} needs at least {floor} minutes "
            f"under HC-002; you entered {body.estimated_duration}."
        ) if body.estimated_duration < floor else str(exc)
        raise HTTPException(422, {
            "code": "TASK_CONSTRAINT_INVALID",
            "message": message,
            "details": {"field": "estimatedDuration", "taskType": body.task_type.value, "minDurationMinutes": floor},
        }) from exc


def _task_type_min_duration(task_type: TaskType) -> int:
    """Statutory block floor (HC-002) implied by the task type's machine."""
    machine = TASK_REQUIREMENTS.get(task_type, {}).get("machineType", MachineType.NONE)
    return MIN_MACHINE_BLOCK_MINUTES[machine]


def _task_type_view(department: Department, task_type: TaskType) -> dict[str, Any]:
    requirements = TASK_REQUIREMENTS.get(task_type, {})
    return {
        "taskType": task_type.value,
        "department": department.value,
        "minDurationMinutes": _task_type_min_duration(task_type),
        # Which asset identifies the work location for this task type, so the
        # composer can offer the right ones instead of hitting ASSET_REQUIRED.
        "assetType": TASK_ASSET_TYPES.get(task_type, "TRACK_SECTION"),
        "requiresPTW": bool(requirements.get("requiresPTW", False)),
        "requiresT351": bool(requirements.get("requiresT351", False)),
        "requiresCorrespondenceTest": bool(requirements.get("requiresCorrespondenceTest", False)),
    }


def _ticket_fingerprint(body: BlockRequestCreate) -> str:
    return hashlib.sha256(body.model_dump_json(by_alias=True, exclude_none=True).encode("utf-8")).hexdigest()


def _find_request(request_id: str) -> BlockRequest:
    request = state.block_requests.get(request_id)
    if request is None:
        raise HTTPException(404, {"code": "NOT_FOUND", "message": "block request not found"})
    return request

@app.get("/api/v1/block-requests/task-types")
def list_ticket_task_types(user: User = Depends(auth)):
    """Per-department task types with their statutory duration floors.

    The composer used to hard-code this list, so a new task type or a changed
    HC-002 floor silently drifted out of sync and only surfaced as a 422.
    """
    items = [
        _task_type_view(department, task_type)
        for department, task_types in DEPARTMENT_TASK_TYPES.items()
        for task_type in sorted(task_types, key=lambda t: t.value)
    ]
    return {"items": items, "count": len(items), "synthetic": True}


@app.get("/api/v1/block-requests")
def list_block_requests(department:Department|None=None,status:BlockRequestStatus|None=None,sectionId:str|None=None,user:User=Depends(auth)):
    role = normalize_role(user.role)
    if role not in BROAD_TICKET_ROLES:
        scope = _department_scope(user)
        if department is not None:
            _authorize_ticket_department(user, department)
        elif scope is None:
            raise HTTPException(403, {"code": "DEPARTMENT_SCOPE_REQUIRED", "message": "the authenticated department supervisor has no department scope"})
        department = scope
    items = [
        r for r in state.block_requests.values()
        if (department is None or r.department == department)
        and (status is None or r.status == status)
        and (sectionId is None or r.sectionId == sectionId)
    ]
    return {"items": [_ticket_view(r, user) for r in items], "count": len(items), "synthetic": True, "scenario": "GZB_ALJN_DEMO"}

@app.get("/api/v1/block-requests/{request_id}")
def get_block_request(request_id:str,user:User=Depends(auth)):
    request = _find_request(request_id)
    _authorize_ticket_department(user, request.department)
    return _ticket_view(request, user)

@app.post("/api/v1/block-requests")
def create_block_request(body:BlockRequestCreate,idempotency_key:str|None=Header(None,alias="Idempotency-Key"),user:User=Depends(allow(*SUBMITTER_TICKET_ROLES))):
    _authorize_ticket_department(user, body.department)
    key = f"{user.user_id}:block-requests:{idempotency_key}" if idempotency_key else None
    fingerprint = _ticket_fingerprint(body)
    if key and key in state.idempotency:
        saved = state.idempotency[key]
        if saved["fingerprint"] != fingerprint:
            raise HTTPException(409, {"code": "IDEMPOTENCY_CONFLICT", "message": "key reused with a different request"})
        return saved["response"]
    allowed_task_types = DEPARTMENT_TASK_TYPES.get(body.department, frozenset())
    if body.task_type not in allowed_task_types:
        raise HTTPException(422, {
            "code": "TASK_TYPE_DEPARTMENT_MISMATCH",
            "message": f"task type '{body.task_type.value}' is not valid for department {body.department.value}",
            "details": {"field": "taskType", "department": body.department.value, "allowed": [t.value for t in allowed_task_types]},
        })
    section = _resolve_request_section(body)
    asset = _resolve_request_asset(body)
    _validate_request_location(body, asset, section)
    request_id = body.request_id or f"REQ-{uuid.uuid4().hex[:10].upper()}"
    if request_id in state.block_requests:
        raise HTTPException(409, {"code": "REQUEST_ALREADY_EXISTS", "message": "Ticket ID already exists"})
    task = _build_linked_task(body, request_id, asset)
    now = datetime.now(timezone.utc).isoformat()
    request = BlockRequest(
        requestId=request_id, department=body.department, corridorId=body.corridor_id,
        sectionId=body.section_id, assetId=asset.assetId, track=body.track,
        kmStart=body.km_start, kmEnd=body.km_end, taskType=body.task_type,
        severity=body.severity, criticality=body.criticality if body.criticality is not None else body.severity,
        dueMinute=body.due_minute if body.due_minute is not None else body.requested_end,
        estimatedDuration=body.estimated_duration, blockRequired=body.block_required,
        blockType=body.block_type, requestedStart=body.requested_start, requestedEnd=body.requested_end,
        status=BlockRequestStatus.REQUESTED, linkedTaskId=task.taskId,
        requestedBy=user.user_id, requestedByRole=normalize_role(user.role),
        createdAtUtc=now, updatedAtUtc=now, reason=body.reason,
        provenance=_request_provenance(),
    )
    with state.transaction():
        state.block_requests[request.requestId] = request
        state.tasks[task.taskId] = task
        state.emit("BLOCK_REQUEST_CREATED", request.requestId, request.model_dump(by_alias=True, mode="json"), user.user_id, reason=body.reason)
        response = _ticket_view(request, user)
        if key: state.idempotency[key] = {"fingerprint": fingerprint, "response": response}
    return response

@app.patch("/api/v1/block-requests/{request_id}/status")
def update_block_request_status(request_id: str, body: BlockRequestStatusUpdate, user: User = Depends(auth)):
    with state.transaction():
        request = _find_request(request_id)
        _authorize_ticket_department(user, request.department)
        action = {BlockRequestStatus.READY: "ACCEPT", BlockRequestStatus.REJECTED: "REJECT",
                  BlockRequestStatus.CANCELLED: "CANCEL"}.get(body.status)
        if not action or action not in _ticket_actions(request, user):
            raise HTTPException(409, {"code": "TICKET_ACTION_UNAVAILABLE", "message": "This ticket action is not available for your role or its current planning state"})
        if not body.reason.strip():
            raise HTTPException(422, {"code": "REASON_REQUIRED", "message": "Enter a reason for the ticket decision", "details": {"field": "reason"}})
        before = request.model_dump(by_alias=True, mode="json")
        request.status = body.status
        request.updatedAtUtc = datetime.now(timezone.utc).isoformat()
        request.reason = body.reason.strip()
        state.emit("BLOCK_REQUEST_STATUS_UPDATED", request_id, request.model_dump(by_alias=True, mode="json"),
                   user.user_id, reason=request.reason, before=before)
        return _ticket_view(request, user)

@app.get("/health")
@app.get("/api/v1/health")
def health(): return {"status":"ok","synthetic":True,"storageBackend":os.getenv("RAILOS_STORAGE_BACKEND","memory")}

@app.post("/api/v1/demo/reset")
def reset(_:User=Depends(allow("ADMIN"))):
    state.reset()
    counts={"tasks":len(state.tasks),"defects":len(state.defects),"movements":len(state.trains),"windows":len(state.windows),
        "critical":sum(t.severity>=9 for t in state.tasks.values()),"overdue":sum(t.overdueDays>0 for t in state.tasks.values())}
    return {"status":"reset","counts":counts,"synthetic":True}

@app.post("/api/v1/demo/seed")
def seed_demo(_:User=Depends(allow("ADMIN", "CONTROL_OFFICER", "PLANNER"))):
    from .demo_seed import seed_all_demo_data
    from .evidence_routes import object_store, verification_service
    summary = seed_all_demo_data(state, object_store, verification_service)
    state.commit()
    return {"status":"seeded","summary":summary,"synthetic":True}

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
    if request.task_ids is not None:
        unknown_task_ids = sorted(set(request.task_ids) - set(state.tasks))
        if unknown_task_ids:
            raise HTTPException(400, {
                "code": "UNKNOWN_TASK",
                "message": "one or more selected task IDs do not exist",
                "details": {"taskIds": unknown_task_ids},
            })
        request_task_ids = set(request.task_ids)
        blocked_task_ids = sorted(
            task_id for task_id in request_task_ids
            if any(
                block_request.linkedTaskId == task_id
                and block_request.status in {BlockRequestStatus.REJECTED, BlockRequestStatus.CANCELLED}
                for block_request in state.block_requests.values()
            )
        )
        if blocked_task_ids:
            raise HTTPException(409, {
                "code": "TASK_NOT_PLANNABLE",
                "message": "rejected or cancelled requests cannot be sent to Block Finder",
                "details": {"taskIds": blocked_task_ids},
            })

    for cid in request.corridor_ids:
        sections=[s for s in state.network.sections if s.corridorId==cid]
        if not any(s.planningEnabled for s in sections): raise HTTPException(403,{"code":"PLANNING_NOT_ENABLED","message":f"planning is not enabled for corridor {cid}","details":{"corridorId":cid}})
    port=optimizer_port()
    if port is None: raise HTTPException(503,{"code":"OPTIMIZER_UNAVAILABLE","message":"architecture-owned optimizer is unavailable"})
    planning_world = state.world(task_ids=request.task_ids)
    if request.task_ids is not None and not planning_world.tasks:
        raise HTTPException(400, {"code": "EMPTY_TASK_SELECTION", "message": "at least one existing task must be selected"})
    candidates=[port.generate(planning_world,profile) for profile in (ObjectiveProfile.SAFETY_FIRST,ObjectiveProfile.BALANCED,ObjectiveProfile.OPERATIONS_FIRST)]
    if candidates and all("INFEASIBLE" in p.solverStatus.upper() for p in candidates):
        raise HTTPException(422,{"code":"SOLVER_INFEASIBLE","message":"optimizer found no feasible plan","details":{"warnings":[w for p in candidates for w in p.warnings]}})
    # audit() violations are genuine hard-constraint breaches and must block.
    # plan.warnings already carries the model's own advisory obligations
    # (e.g. "HC-003: TASK needs a Permit To Work under the power block") for
    # every power/T351 block — that is expected paperwork, not a violation,
    # and the CLI renders it separately for exactly this reason. Track audit
    # violations in their own dict instead of re-matching "HC-" substrings
    # inside the merged warnings list, or every realistic plan gets rejected.
    audit_violations_by_plan: dict[str, list[str]] = {}
    try:
        from optimizer.audit import audit
        world=planning_world
        for plan in candidates:
            try:
                violations=audit(world,plan)
                if violations:
                    formatted=[f"{v.code}: {v.detail}" for v in violations]
                    plan.warnings.extend(formatted)
                    audit_violations_by_plan[plan.planId]=formatted
            except (KeyError,ValueError): pass
    except (ImportError,AttributeError,TypeError): pass
    if candidates and len(audit_violations_by_plan)==len(candidates):
        all_violations=[w for vs in audit_violations_by_plan.values() for w in vs]
        raise HTTPException(422,{"code":"PLAN_FAILED_AUDIT","message":"all candidate plans failed safety audit","details":{"violations":all_violations[:10]}})
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

def _backfill_approval_signature(plan: Plan, required: list[SanctionAuthority]) -> AuthoritySignature | None:
    """Recover the one legacy approver without inventing statutory signatures.

    Before SanctionChain existed, an approved plan carried a provenance stamp
    such as ``APPROVED by controller-1 (CONTROL_OFFICER) at ...``.  A legacy
    read may preserve that single approval, but must not claim that TPC,
    Station Master, or any other authority signed it too.
    """
    provenance = plan.provenance or ""
    match = re.search(
        r"approved\s+by\s+(?P<user>[^;\n(]+?)(?:\s*\((?P<role>[^)]+)\))?\s+at\s+(?P<at>[^;\n]+)",
        provenance,
        flags=re.IGNORECASE,
    )
    if not match:
        # A few old solver/library records used ``approved by <actor>;`` with
        # no timestamp.  Keep the actor if it is unambiguous.
        match = re.search(r"approved\s+by\s+(?P<user>[^;\n(]+)", provenance, flags=re.IGNORECASE)
    if not match:
        return None

    actor = match.group("user").strip()
    role = normalize_role((match.groupdict().get("role") or "CONTROL_OFFICER").strip())
    authority = ROLE_AUTHORITIES.get(role)
    if authority is None or authority not in required:
        # Legacy single-signature approval was the Section Controller path;
        # keep it attached to that authority when the plan still requires it.
        authority = SanctionAuthority.SECTION_CONTROL if SanctionAuthority.SECTION_CONTROL in required else None
    if authority is None:
        return None
    signed_at = match.groupdict().get("at") if match.groupdict().get("at") else datetime.now(timezone.utc).isoformat()
    return AuthoritySignature(
        signatureId=f"SIG-BF-{plan.planId}-{authority.value}",
        authority=authority,
        decision=SignatureDecision.GRANTED,
        role=role,
        userId=actor,
        reason="Backfilled from existing approved plan provenance",
        signedAtUtc=signed_at.strip(),
        planVersion=plan.planVersion,
    )


def ensure_chain(plan: Plan) -> SanctionChain:
    chain = state.sanctions.get(plan.planId)
    if chain is None or chain.planVersion != plan.planVersion:
        reqs, derived_from = derive_required_authorities(plan, state.tasks)
        signatures: list[AuthoritySignature] = []
        backfilled = False
        if plan.status == PlanStatus.APPROVED:
            legacy = _backfill_approval_signature(plan, reqs)
            if legacy is not None:
                signatures.append(legacy)
            backfilled = True

        granted = {s.authority for s in signatures if s.decision == SignatureDecision.GRANTED}
        chain = SanctionChain(
            planId=plan.planId,
            planVersion=plan.planVersion,
            requiredAuthorities=reqs,
            signatures=signatures,
            # A legacy plan is complete only when its recovered single
            # authority is the complete requirement.  Multi-authority plans
            # remain visibly incomplete until an explicit backfill/approval
            # workflow supplies the missing signatures.
            complete=set(reqs).issubset(granted),
            refused=False,
            derivedFrom=derived_from,
            backfilled=backfilled,
        )
        state.sanctions[plan.planId] = chain
        state.sanction_versions[f"{plan.planId}:v{plan.planVersion}"] = copy.deepcopy(chain)
    return chain

def open_possessions_for_plan(
    plan: Plan,
    actor: str = "system",
    actor_role: str = "CONTROL_OFFICER",
) -> list[str]:
    created: list[str] = []
    from datetime import timedelta
    for b in plan.blocks:
        possession_id = f"POS-{b.blockId}"
        if possession_id in state.possessions:
            continue

        needs_ptw = b.blockType in {BlockType.POWER, BlockType.INTEGRATED}
        needs_t351 = b.blockType == BlockType.DISCONNECTION
        needs_corr = False
        block_tasks = [state.tasks.get(tid) for tid in b.taskIds if tid in state.tasks]
        for t in block_tasks:
            if t:
                if getattr(t, "requiresPTW", False): needs_ptw = True
                if getattr(t, "requiresT351", False): needs_t351 = True
                if getattr(t, "requiresCorrespondenceTest", False): needs_corr = True

        lead_in = (PTW_LEAD_IN if needs_ptw else 0) + (T351_LEAD_IN if needs_t351 else 0)
        epoch_dt = parse_datetime(getattr(state, "horizon_start_iso", DEMO_EPOCH))
        p_start_dt = epoch_dt + timedelta(minutes=b.start)
        p_end_dt = epoch_dt + timedelta(minutes=b.end)

        possession = Possession(
            possessionId=possession_id,
            planId=plan.planId,
            planVersion=plan.planVersion,
            blockId=b.blockId,
            sectionId=b.sectionId,
            track=b.track,
            state=PossessionState.SANCTIONED,
            plannedStartUtc=p_start_dt.isoformat(),
            plannedEndUtc=p_end_dt.isoformat(),
            requiresPTW=needs_ptw,
            requiresT351=needs_t351,
            requiresCorrespondenceTest=needs_corr,
            assignedTaskIds=list(b.taskIds),
            department=(b.departments[0].value if b.departments else "ENGG"),
            leadInMinutes=lead_in,
            createdAtUtc=datetime.now(timezone.utc).isoformat(),
            updatedAtUtc=datetime.now(timezone.utc).isoformat(),
            transitions=[
                PossessionTransition(
                    transitionId=f"TRN-{uuid.uuid4().hex[:8]}",
                    fromState=PossessionState.SANCTIONED,
                    toState=PossessionState.SANCTIONED,
                    action="sanction",
                    actor=actor,
                    role=normalize_role(actor_role),
                    occurredAtUtc=datetime.now(timezone.utc).isoformat(),
                    ruleCitation="G&SR 4.09",
                )
            ]
        )
        state.possessions[possession_id] = possession
        created.append(possession_id)
        state.emit("POSSESSION_SANCTIONED", possession_id, possession.model_dump(mode="json"), actor)
    return created

def decide(plan_id, body, target, user):
    with state.transaction():
        source = state.plans.get(plan_id)
        if source is None:
            raise HTTPException(404, {"code": "NOT_FOUND", "message": "plan not found"})
        if body.expected_version is not None and body.expected_version != source.planVersion:
            raise HTTPException(409, {"code": "STALE_PLAN_VERSION", "message": "plan version is stale"})
        if source.status == PlanStatus.APPROVED:
            raise HTTPException(409, {"code": "PLAN_ALREADY_APPROVED", "message": "approved plan is immutable"})

        if target == PlanStatus.PROPOSED:
            state.sanctions.pop(plan_id, None)
            state.plan_versions.setdefault(f"{plan_id}:v{source.planVersion}", copy.deepcopy(source))
            decided = source.model_copy(deep=True)
            decided.planVersion += 1
            decided.parentPlanId = source.planId
            decided.status = target
            stamp = f"{target.value} by {user.user_id} at {datetime.now(timezone.utc).isoformat()}" + (f" ({body.reason})" if body.reason else "")
            decided.provenance = f"{decided.provenance}\n{stamp}" if decided.provenance else stamp
            state.plan_versions[f"{plan_id}:v{decided.planVersion}"] = copy.deepcopy(decided)
            state.plans[plan_id] = copy.deepcopy(decided)
            state.emit(f"PLAN_{target.value}", plan_id, decided.model_dump(mode="json"), user.user_id, body.reason, source.model_dump(mode="json"), decided.planVersion)
            return decided

        if target == PlanStatus.REJECTED:
            chain = ensure_chain(source)
            norm_role = normalize_role(user.role)
            auth_to_sign = getattr(body, "authority", None) or ROLE_AUTHORITIES.get(norm_role, SanctionAuthority.SECTION_CONTROL)
            if norm_role != "ADMIN" and (
                auth_to_sign not in chain.requiredAuthorities
                or norm_role not in AUTHORITY_ROLES.get(auth_to_sign, frozenset())
            ):
                raise HTTPException(
                    403,
                    {
                        "code": "FORBIDDEN",
                        "message": f"Role '{user.role}' cannot refuse authority '{getattr(auth_to_sign, 'value', auth_to_sign)}' for this plan",
                    },
                )
            refusal_sig = AuthoritySignature(
                signatureId=f"SIG-{uuid.uuid4().hex[:8]}",
                authority=auth_to_sign,
                decision=SignatureDecision.REFUSED,
                role=norm_role,
                userId=user.user_id,
                reason=body.reason,
                formReference=getattr(body, "form_reference", ""),
                signedAtUtc=datetime.now(timezone.utc).isoformat(),
                planVersion=source.planVersion,
            )
            chain.signatures.append(refusal_sig)
            chain.refused = True
            state.sanctions[plan_id] = chain
            state.sanction_versions[f"{plan_id}:v{source.planVersion}"] = copy.deepcopy(chain)
            state.emit("PLAN_SANCTION_REFUSED", plan_id, chain.model_dump(mode="json"), user.user_id, body.reason, version=source.planVersion)

            state.plan_versions.setdefault(f"{plan_id}:v{source.planVersion}", copy.deepcopy(source))
            decided = source.model_copy(deep=True)
            decided.planVersion += 1
            decided.parentPlanId = source.planId
            decided.status = target
            stamp = f"{target.value} by {user.user_id} at {datetime.now(timezone.utc).isoformat()}" + (f" ({body.reason})" if body.reason else "")
            decided.provenance = f"{decided.provenance}\n{stamp}" if decided.provenance else stamp
            state.plan_versions[f"{plan_id}:v{decided.planVersion}"] = copy.deepcopy(decided)
            state.plans[plan_id] = copy.deepcopy(decided)
            state.emit(f"PLAN_{target.value}", plan_id, decided.model_dump(mode="json"), user.user_id, body.reason, source.model_dump(mode="json"), decided.planVersion)
            return decided

        # Target is APPROVED
        chain = ensure_chain(source)
        norm_role = normalize_role(user.role)

        auth_to_sign = getattr(body, "authority", None)
        if auth_to_sign is None:
            if norm_role == "ADMIN":
                already_signed = {s.authority for s in chain.signatures if s.decision == SignatureDecision.GRANTED and s.planVersion == source.planVersion}
                pending = [a for a in chain.requiredAuthorities if a not in already_signed]
                auth_to_sign = pending[0] if pending else chain.requiredAuthorities[0]
            else:
                auth_to_sign = ROLE_AUTHORITIES.get(norm_role)

        if auth_to_sign is None or (auth_to_sign not in chain.requiredAuthorities and norm_role != "ADMIN"):
            raise HTTPException(403, {"code": "FORBIDDEN", "message": f"Role '{user.role}' cannot sign required authorities for this plan ({[a.value for a in chain.requiredAuthorities]})"})
        if norm_role != "ADMIN" and norm_role not in AUTHORITY_ROLES.get(auth_to_sign, frozenset()):
            raise HTTPException(
                403,
                {
                    "code": "FORBIDDEN",
                    "message": f"Role '{user.role}' cannot sign authority '{auth_to_sign.value}'",
                },
            )

        already = any(s.authority == auth_to_sign and s.decision == SignatureDecision.GRANTED and s.planVersion == source.planVersion for s in chain.signatures)
        if not already:
            sig = AuthoritySignature(
                signatureId=f"SIG-{uuid.uuid4().hex[:8]}",
                authority=auth_to_sign,
                decision=SignatureDecision.GRANTED,
                role=norm_role,
                userId=user.user_id,
                reason=body.reason,
                formReference=getattr(body, "form_reference", ""),
                signedAtUtc=datetime.now(timezone.utc).isoformat(),
                planVersion=source.planVersion,
            )
            chain.signatures.append(sig)

        granted_set = {s.authority for s in chain.signatures if s.decision == SignatureDecision.GRANTED and s.planVersion == source.planVersion}
        chain.complete = set(chain.requiredAuthorities).issubset(granted_set)

        state.sanctions[plan_id] = chain
        state.sanction_versions[f"{plan_id}:v{source.planVersion}"] = copy.deepcopy(chain)

        if not chain.complete:
            state.emit("PLAN_SANCTION_PARTIAL", plan_id, chain.model_dump(mode="json"), user.user_id, body.reason, version=source.planVersion)
            raise PartialSanction(chain)

        # Finalisation
        sections = {b.sectionId for b in source.blocks}
        for other_id, other in state.plans.items():
            if other_id != plan_id and other.status == PlanStatus.APPROVED and sections.intersection({b.sectionId for b in other.blocks}):
                raise HTTPException(409, {"code": "PLAN_VERSION_CONFLICT", "message": "an approved plan already covers this territory"})

        state.plan_versions.setdefault(f"{plan_id}:v{source.planVersion}", copy.deepcopy(source))
        decided = source.model_copy(deep=True)
        decided.planVersion += 1
        decided.parentPlanId = source.planId
        decided.status = PlanStatus.APPROVED
        stamp = f"APPROVED by {user.user_id} ({norm_role}) at {datetime.now(timezone.utc).isoformat()}" + (f" ({body.reason})" if body.reason else "")
        decided.provenance = f"{decided.provenance}\n{stamp}" if decided.provenance else stamp
        state.plan_versions[f"{plan_id}:v{decided.planVersion}"] = copy.deepcopy(decided)
        state.plans[plan_id] = copy.deepcopy(decided)

        for a in decided.assignments:
            state.assignments[a.taskId] = {
                "id": a.taskId, "planId": plan_id, "planVersion": decided.planVersion,
                "taskId": a.taskId, "blockId": a.blockId, "status": "READY",
                "start": a.start, "end": a.end, "synthetic": True,
            }

        # Keep the collected signatures attached to the immutable approved
        # version.  The signatures were collected against source vN; the
        # resulting sanctioned plan is vN+1, so a versioned copy is recorded
        # for reads while the source-version chain remains in history.
        final_chain = copy.deepcopy(chain)
        final_chain.planVersion = decided.planVersion
        final_chain.signatures = [
            signature.model_copy(update={"planVersion": decided.planVersion})
            for signature in final_chain.signatures
        ]
        final_chain.complete = True
        final_chain.backfilled = False
        state.sanctions[plan_id] = final_chain
        state.sanction_versions[f"{plan_id}:v{decided.planVersion}"] = copy.deepcopy(final_chain)

        open_possessions_for_plan(decided, user.user_id, norm_role)
        state.emit("PLAN_APPROVED", plan_id, decided.model_dump(mode="json"), user.user_id, body.reason, source.model_dump(mode="json"), decided.planVersion)
        return decided

@app.post("/api/v1/block-plans/{plan_id}/approve")
def approve(plan_id:str,body:Decision=Decision(),user:User=Depends(allow("CONTROL_OFFICER"))):
    return decide(plan_id,body,PlanStatus.APPROVED,user)

@app.post("/api/v1/block-plans/{plan_id}/reject")
def reject(plan_id:str,body:Decision=Decision(),user:User=Depends(allow("CONTROL_OFFICER"))):
    return decide(plan_id,body,PlanStatus.REJECTED,user)

@app.post("/api/v1/block-plans/{plan_id}/request-revision")
def request_revision(plan_id:str,body:Decision=Decision(),user:User=Depends(allow("CONTROL_OFFICER","PLANNER"))):
    return decide(plan_id,body,PlanStatus.PROPOSED,user)

@app.post("/api/v1/block-plans/{plan_id}/lock")
def lock(plan_id:str,user:User=Depends(allow("CONTROL_OFFICER"))):
    with state.transaction():
        plan=state.plans.get(plan_id)
        if plan is None: raise HTTPException(404,{"code":"NOT_FOUND","message":"plan not found"})
        for a in plan.assignments:
            if a.taskId in state.tasks: state.tasks[a.taskId]=state.tasks[a.taskId].model_copy(update={"locked":True})
        ids=[a.taskId for a in plan.assignments]; state.emit("PLAN_LOCKED",plan_id,{"taskIds":ids},user.user_id,version=plan.planVersion); return {"planId":plan_id,"lockedTaskIds":ids}

@app.get("/api/v1/block-plans/{plan_id}/sanctions")
def get_plan_sanctions(plan_id: str, _: User = Depends(auth)):
    # ensure_chain() may backfill a legacy approval on first read.  Keep that
    # write inside the repository transaction so a Postgres-backed process
    # cannot return the chain and then lose it on restart.
    with state.transaction():
        plan = state.plans.get(plan_id)
        if plan is None:
            raise HTTPException(404, {"code": "NOT_FOUND", "message": "plan not found"})
        chain = ensure_chain(plan)
        return chain.model_dump(by_alias=True, mode="json")

@app.post("/api/v1/block-plans/{plan_id}/sanctions")
def sign_plan_sanction(
    plan_id: str,
    body: SanctionSignRequest = SanctionSignRequest(),
    user: User = Depends(auth),
):
    # GRANTED is the normal multi-party path and REFUSED follows the normal
    # rejected-plan path.  DEFERRED/WITHDRAWN are non-terminal chain events:
    # they remain visible in the audit trail but must not mutate PlanStatus.
    if body.decision in {SignatureDecision.DEFERRED, SignatureDecision.WITHDRAWN}:
        with state.transaction():
            plan = state.plans.get(plan_id)
            if plan is None:
                raise HTTPException(404, {"code": "NOT_FOUND", "message": "plan not found"})
            if body.expected_version is not None and body.expected_version != plan.planVersion:
                raise HTTPException(409, {"code": "STALE_PLAN_VERSION", "message": "plan version is stale"})
            if plan.status == PlanStatus.APPROVED:
                raise HTTPException(409, {"code": "PLAN_ALREADY_APPROVED", "message": "approved plan is immutable"})
            chain = ensure_chain(plan)
            role = normalize_role(user.role)
            authority = body.authority or ROLE_AUTHORITIES.get(role)
            if authority is None or authority not in chain.requiredAuthorities:
                raise HTTPException(403, {"code": "FORBIDDEN", "message": "role cannot update a required sanction authority"})
            if role != "ADMIN" and role not in AUTHORITY_ROLES.get(authority, frozenset()):
                raise HTTPException(403, {"code": "FORBIDDEN", "message": f"Role '{user.role}' cannot update authority '{authority.value}'"})
            if body.decision == SignatureDecision.WITHDRAWN:
                chain.signatures = [
                    signature for signature in chain.signatures
                    if not (
                        signature.authority == authority
                        and signature.decision == SignatureDecision.GRANTED
                        and signature.planVersion == plan.planVersion
                    )
                ]
            chain.signatures.append(
                AuthoritySignature(
                    signatureId=f"SIG-{uuid.uuid4().hex[:8]}",
                    authority=authority,
                    decision=body.decision,
                    role=role,
                    userId=user.user_id,
                    reason=body.reason,
                    formReference=body.form_reference,
                    signedAtUtc=datetime.now(timezone.utc).isoformat(),
                    planVersion=plan.planVersion,
                )
            )
            granted = {s.authority for s in chain.signatures if s.decision == SignatureDecision.GRANTED and s.planVersion == plan.planVersion}
            chain.complete = set(chain.requiredAuthorities).issubset(granted)
            chain.refused = False
            state.sanctions[plan_id] = chain
            state.sanction_versions[f"{plan_id}:v{plan.planVersion}"] = copy.deepcopy(chain)
            state.emit(f"PLAN_SANCTION_{body.decision.value}", plan_id, chain.model_dump(mode="json"), user.user_id, body.reason, version=plan.planVersion)
            view = chain.model_dump(by_alias=True, mode="json")
            view["replayed"] = False
            return JSONResponse(status_code=202, content=view)

    target = PlanStatus.APPROVED if body.decision == SignatureDecision.GRANTED else PlanStatus.REJECTED
    dec = Decision(
        reason=body.reason,
        expectedVersion=body.expected_version,
        authority=body.authority,
        formReference=body.form_reference,
    )
    return decide(plan_id, dec, target, user)

@app.get("/api/v1/work/assignments")
def work_assignments(_:User=Depends(auth)): return listed(state.assignments)

@app.post("/api/v1/work/assignments/{assignment_id}/updates")
@app.post("/api/v1/work/{assignment_id}/update")
def work_update(assignment_id:str,body:WorkUpdate,user:User=Depends(allow("FIELD_SUPERVISOR","ENGINEERING","SIGNAL_TELECOM","TRACTION","CONTROL_OFFICER"))):
    with state.transaction():
        assignment=state.assignments.get(assignment_id)
        if assignment is None: raise HTTPException(404,{"code":"NOT_FOUND","message":"assignment not found"})

        def assignment_value(name: str, default: Any = None):
            if isinstance(assignment, dict):
                return assignment.get(name, default)
            return getattr(assignment, name, default)

        # New guard: TaskStatus.STARTED when a possession exists for the block and is not LIVE/OVERRUNNING
        if body.status == TaskStatus.STARTED:
            block_id = assignment_value("blockId")
            matching_poss = None
            explicit_possession_id = assignment_value("possessionId")
            if explicit_possession_id:
                matching_poss = state.possessions.get(explicit_possession_id)
            if block_id:
                matching_poss = matching_poss or state.possessions.get(f"POS-{block_id}")
                if matching_poss is None:
                    for p in state.possessions.values():
                        if p.blockId == block_id:
                            matching_poss = p
                            break
            if matching_poss and matching_poss.state not in {PossessionState.LIVE, PossessionState.OVERRUNNING}:
                raise HTTPException(409, {
                    "code": "POSSESSION_NOT_LIVE",
                    "message": f"Cannot start task '{assignment_value('taskId', assignment_id)}': possession '{matching_poss.possessionId}' is in state '{matching_poss.state}', not LIVE or OVERRUNNING"
                })

        before=copy.deepcopy(assignment)
        task_id = assignment_value("taskId", assignment_id)
        if isinstance(assignment, dict):
            assignment["status"] = body.status.value
            assignment["note"] = body.note
            if body.execution_status:
                assignment["executionStatus"] = body.execution_status.value
            response = assignment
        else:
            updates: dict[str, Any] = {"status": body.status, "note": body.note}
            if body.execution_status:
                updates["executionStatus"] = body.execution_status
            assignment = assignment.model_copy(update=updates)
            state.assignments[assignment_id] = assignment
            response = assignment
        if task_id in state.tasks:
            state.tasks[task_id]=state.tasks[task_id].model_copy(update={"status":body.status,"locked":body.status in {TaskStatus.STARTED,TaskStatus.COMPLETED}})
        state.emit(f"TASK_{body.status.value}",task_id,response,user.user_id,body.note,before); return response

@app.post("/api/v1/emergencies")
def create_emergency(body:EmergencyRequest,user:User=Depends(allow("CONTROL_OFFICER","ENGINEERING","SIGNAL_TELECOM","TRACTION","FIELD_SUPERVISOR"))):
    eid="EMG-"+hashlib.sha1(body.model_dump_json(by_alias=True).encode()).hexdigest()[:8].upper()
    task=MaintenanceTask(taskId=eid,department=Department.ENGG,assetId=body.asset_id,corridorId=body.corridor_id,sectionId=body.section_id,track=Track.DOWN,kmStart=72.4,kmEnd=72.41,taskType=TaskType.RAIL_REPLACEMENT,severity=10,criticality=10,dueMinute=body.duration_minutes,estimatedDuration=body.duration_minutes,status=TaskStatus.PENDING,blockType=BlockType.EMERGENCY,isEmergency=True,detectedAtMinute=0)
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

# --- Possession Endpoints & Lifecycle -----------------------------------------

def handle_possession_action(
    possession_id: str,
    action: str,
    body: PossessionTransitionRequest,
    user: User,
    idempotency_key: str | None = None,
    offline_replay: str | None = None,
):
    norm_role = normalize_role(user.role)
    is_replay = bool(offline_replay and offline_replay.lower() in {"true", "1", "yes"})

    key = f"possession:{possession_id}:{action}:{idempotency_key}" if idempotency_key else None
    fingerprint = hashlib.sha256(
        body.model_dump_json(by_alias=True, exclude_none=True).encode("utf-8")
    ).hexdigest()
    if key and key in state.idempotency:
        saved = state.idempotency[key]
        if saved.get("fingerprint") and saved["fingerprint"] != fingerprint:
            raise HTTPException(
                409,
                {
                    "code": "IDEMPOTENCY_CONFLICT",
                    "message": "Idempotency-Key was already used with a different transition body",
                },
            )
        replay_response = copy.deepcopy(saved["response"])
        if isinstance(replay_response, dict):
            replay_response["replayed"] = True
        return replay_response

    possession = state.possessions.get(possession_id)
    if possession is None:
        raise HTTPException(404, {"code": "NOT_FOUND", "message": f"Possession '{possession_id}' not found"})

    if is_replay and action in ONLINE_AUTHORITY_ACTIONS:
        raise HTTPException(409, {
            "code": "ONLINE_AUTHORITY_REQUIRED",
            "message": f"Action '{action}' requires real-time online authority and cannot be replayed from offline queue",
        })

    # A client timestamp is part of the transition's optimistic concurrency
    # contract, not merely a hint for offline requests.  Reject it whenever it
    # predates the latest server transition, regardless of whether the caller
    # remembered to include the replay marker.
    if body.client_event_at_utc:
        try:
            client_dt = datetime.fromisoformat(body.client_event_at_utc)
            if client_dt.tzinfo is None:
                client_dt = client_dt.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            raise HTTPException(
                422,
                {
                    "code": "VALIDATION_ERROR",
                    "message": "clientEventAtUtc must be an ISO-8601 timestamp",
                },
            )
        if possession.transitions:
            last_transition = max(
                possession.transitions,
                key=lambda transition: parse_datetime(transition.occurredAtUtc),
            )
            last_dt = parse_datetime(last_transition.occurredAtUtc)
            if client_dt < last_dt:
                raise HTTPException(409, {
                    "code": "STALE_TRANSITION",
                    "message": f"Event timestamp {body.client_event_at_utc} predates last transition at {last_transition.occurredAtUtc}",
                })

    # Find transition definition
    rule = TRANSITION_TABLE.get((possession.state, action))

    if rule is None:
        # Check natural target-state idempotency.  The original action may
        # have been a state-changing transition whose target is now current.
        matching = [t for t in TRANSITIONS if t.action == action and t.to_state == possession.state]
        if matching:
            if norm_role != "ADMIN" and not any(norm_role in t.allowed_roles for t in matching):
                raise HTTPException(403, {"code": "FORBIDDEN", "message": f"Role '{user.role}' is not authorized to replay action '{action}'"})
            view = build_possession_view(possession, user.role, state)
            view["replayed"] = True
            return view

        allowed = get_allowed_actions_for_role(possession, user.role, state)
        raise HTTPException(409, {
            "code": "ILLEGAL_TRANSITION",
            "message": f"Cannot perform action '{action}' on possession in state '{possession.state}'",
            "details": {"currentState": possession.state, "action": action, "allowedActions": allowed},
        })

    if norm_role != "ADMIN" and norm_role not in rule.allowed_roles:
        raise HTTPException(403, {"code": "FORBIDDEN", "message": f"Role '{user.role}' is not authorized to perform action '{action}'"})

    # Same-state physical acts use their persisted artefact as a second
    # idempotency layer, even when the client did not send an Idempotency-Key.
    if rule.to_state == possession.state and action_already_applied(possession, action):
        view = build_possession_view(possession, user.role, state)
        view["replayed"] = True
        return view

    body_dict = body.model_dump(by_alias=True, mode="json", exclude_none=True)
    if body.details:
        body_dict.update(body.details)
    if body.duration_minutes is not None:
        body_dict["durationMinutes"] = body.duration_minutes
    if body.tsr_speed_kmph is not None:
        body_dict["tsrSpeedKmph"] = body.tsr_speed_kmph
    if body.detonator_count is not None:
        body_dict["detonatorCount"] = body.detonator_count
    if body.deferred_until_utc is not None:
        body_dict["deferredUntilUtc"] = body.deferred_until_utc

    ok, msg = check_precondition(possession, action, body_dict, norm_role, state)
    if not ok:
        code = "TEST_TOO_SHORT" if "TEST_TOO_SHORT" in msg else "PRECONDITION_FAILED"
        raise HTTPException(422 if code == "TEST_TOO_SHORT" else 409, {"code": code, "message": msg})

    now_iso = datetime.now(timezone.utc).isoformat()
    from_st = possession.state
    to_st = rule.to_state

    with state.transaction():
        if action == "defer":
            possession.deferralCount += 1
            possession.deferredUntilUtc = body_dict.get("deferredUntilUtc")
        elif action == "issue-t351":
            t_num = body.form_reference or f"T351-{uuid.uuid4().hex[:6].upper()}"
            possession.formT351 = FormT351(
                formNumber=t_num,
                sectionId=possession.sectionId,
                track=possession.track,
                issuedBy=user.user_id,
                issuedAtUtc=now_iso,
                remarks=body.note,
            )
        elif action == "endorse-t351":
            if possession.formT351:
                possession.formT351.status = "ENDORSED"
                possession.formT351.endorsedBy = user.user_id
                possession.formT351.endorsedAtUtc = now_iso
        elif action == "confirm-earthing":
            if not possession.permitToWork:
                possession.permitToWork = PermitToWork(
                    ptwNumber=body.form_reference or f"PTW-{uuid.uuid4().hex[:6].upper()}",
                    oheSection=possession.sectionId,
                    isolatorNumber=body_dict.get("isolatorNumber", "ISO-01"),
                    issuedBy="",
                    issuedAtUtc=now_iso,
                    earthingConfirmed=True,
                    status="PENDING",
                    remarks=body.note,
                )
            else:
                possession.permitToWork.earthingConfirmed = True
        elif action == "issue-ptw":
            ptw_num = body.form_reference or (possession.permitToWork.ptwNumber if possession.permitToWork else f"PTW-{uuid.uuid4().hex[:6].upper()}")
            iso_num = possession.permitToWork.isolatorNumber if possession.permitToWork else "ISO-01"
            possession.permitToWork = PermitToWork(
                ptwNumber=ptw_num,
                oheSection=possession.sectionId,
                isolatorNumber=iso_num,
                issuedBy=user.user_id,
                issuedAtUtc=now_iso,
                earthingConfirmed=True,
                status="ISSUED",
                remarks=body.note,
            )
        elif action == "plant-protection":
            det_count = int(body_dict.get("detonatorCount", 3))
            possession.protectionRecord = ProtectionRecord(
                bannerFlagsPlaced=True,
                detonatorCount=det_count,
                handSignalPosted=True,
                plantedBy=user.user_id,
                plantedAtUtc=now_iso,
                remarks=body.note,
            )
        elif action == "start-work":
            if not possession.actualStartUtc:
                possession.actualStartUtc = now_iso
        elif action == "record-correspondence-test":
            dur = int(body_dict.get("durationMinutes", 30))
            possession.correspondenceTest = CorrespondenceTest(
                testId=f"TEST-{uuid.uuid4().hex[:6].upper()}",
                testedBy=user.user_id,
                startAtUtc=body_dict.get("startAtUtc", now_iso),
                completedAtUtc=now_iso,
                durationMinutes=dur,
                pointsTested=True,
                signalsTested=True,
                trackCircuitsTested=True,
                passed=True,
                remarks=body.note,
            )
        elif action == "remove-discharge-rods":
            if possession.permitToWork:
                possession.permitToWork.dischargeRodsRemoved = True
        elif action == "cancel-ptw":
            if possession.permitToWork:
                possession.permitToWork.status = "CANCELLED"
                possession.permitToWork.cancelledBy = user.user_id
                possession.permitToWork.cancelledAtUtc = now_iso
        elif action == "reconnect-t351":
            if possession.formT351:
                possession.formT351.status = "RECONNECTED"
                possession.formT351.reconnectedBy = user.user_id
                possession.formT351.reconnectedAtUtc = now_iso
        elif action == "re-energise":
            if possession.permitToWork:
                possession.permitToWork.reEnergised = True
                possession.permitToWork.reEnergisedBy = user.user_id
                possession.permitToWork.reEnergisedAtUtc = now_iso
        elif action == "certify-fitness":
            tsr = body_dict.get("tsrSpeedKmph", 20)
            possession.fitnessCertificate = FitnessCertificate(
                certificateNumber=f"FIT-{uuid.uuid4().hex[:6].upper()}",
                certifiedBy=user.user_id,
                certifiedAtUtc=now_iso,
                tsrSpeedKmph=tsr,
                trackFitForTraffic=True,
                overheadClearanceFit=True,
                signallingFit=True,
                remarks=body.note,
            )
        elif action == "station-close":
            possession.stationClosed = True
            possession.stationClosedBy = user.user_id
            possession.stationClosedAtUtc = now_iso
        elif action == "close":
            possession.actualEndUtc = now_iso
            actual_end_dt = parse_datetime(now_iso)
            planned_end_dt = parse_datetime(possession.plannedEndUtc)
            overrun_min = int((actual_end_dt - planned_end_dt).total_seconds() / 60)
            if overrun_min > 0:
                burst_id = f"BST-{possession.possessionId}"
                if burst_id not in state.block_bursts:
                    burst = BlockBurst(
                        burstId=burst_id,
                        possessionId=possession.possessionId,
                        planId=possession.planId,
                        sectionId=possession.sectionId,
                        track=possession.track,
                        department=possession.department or "ENGG",
                        plannedEndUtc=possession.plannedEndUtc,
                        actualCloseUtc=now_iso,
                        overrunMinutes=overrun_min,
                        causeCategory=body_dict.get("causeCategory") or "EXECUTION",
                        remarks=body.note,
                        occurredAtUtc=now_iso,
                    )
                    state.block_bursts[burst_id] = burst
                    state.emit("BLOCK_BURST_RECORDED", burst_id, burst.model_dump(mode="json"), user.user_id, recipient_role="CONTROL_OFFICER")

        possession.state = to_st
        possession.updatedAtUtc = now_iso
        transition_record = PossessionTransition(
            transitionId=f"TRN-{uuid.uuid4().hex[:8]}",
            fromState=from_st,
            toState=to_st,
            action=action,
            actor=user.user_id,
            role=norm_role,
            occurredAtUtc=now_iso,
            clientEventAtUtc=body.client_event_at_utc,
            ruleCitation=rule.rule_citation,
            details={"note": body.note, **body_dict},
            replayed=is_replay,
        )
        possession.transitions.append(transition_record)
        state.emit(
            f"POSSESSION_{action.upper().replace('-', '_')}",
            possession.possessionId,
            possession.model_dump(mode="json"),
            user.user_id,
            body.note,
        )

        view = build_possession_view(possession, user.role, state)
        if key:
            state.idempotency[key] = {"response": copy.deepcopy(view), "fingerprint": fingerprint}
        return view

@app.get("/api/v1/possessions")
def list_possessions(
    status: PossessionState | None = None,
    sectionId: str | None = None,
    user: User = Depends(auth),
):
    now = datetime.now(timezone.utc)
    with state.transaction():
        for p in list(state.possessions.values()):
            if p.state == PossessionState.LIVE:
                planned_end = parse_datetime(p.plannedEndUtc)
                if now > planned_end:
                    p.state = PossessionState.OVERRUNNING
                    p.updatedAtUtc = now.isoformat()
                    p.transitions.append(PossessionTransition(
                        transitionId=f"TRN-{uuid.uuid4().hex[:8]}",
                        fromState=PossessionState.LIVE,
                        toState=PossessionState.OVERRUNNING,
                        action="declare-overrun",
                        actor="system-sweeper",
                        role="CONTROL_OFFICER",
                        occurredAtUtc=now.isoformat(),
                        ruleCitation="SO-005",
                        details={"reason": "Automatic sweep: planned block window elapsed"}
                    ))
                    state.emit("POSSESSION_OVERRUN", p.possessionId, p.model_dump(mode="json"), "system-sweeper", "Planned block window elapsed")

    views = []
    for p in state.possessions.values():
        if status and p.state != status:
            continue
        if sectionId and p.sectionId != sectionId:
            continue
        views.append(build_possession_view(p, user.role, state))
    return {"items": views, "count": len(views), "synthetic": True}

@app.get("/api/v1/possessions/mine")
def my_possessions(user: User = Depends(auth)):
    norm_role = normalize_role(user.role)
    views = []
    for p in state.possessions.values():
        view = build_possession_view(p, user.role, state)
        if norm_role in {"ADMIN", "CONTROL_OFFICER"} or len(view["allowedActions"]) > 0:
            views.append(view)
        elif norm_role == "STATION_MASTER" and p.requiresT351:
            views.append(view)
        elif norm_role == "TPC" and p.requiresPTW:
            views.append(view)
        elif norm_role in {"ENGINEERING", "SIGNAL_TELECOM", "TRACTION", "FIELD_SUPERVISOR"}:
            views.append(view)
    return {"items": views, "count": len(views), "synthetic": True}

@app.get("/api/v1/possessions/{possession_id}")
def get_possession(possession_id: str, user: User = Depends(auth)):
    possession = state.possessions.get(possession_id)
    if possession is None:
        raise HTTPException(404, {"code": "NOT_FOUND", "message": f"Possession '{possession_id}' not found"})
    return build_possession_view(possession, user.role, state)

@app.post("/api/v1/possessions/{possession_id}/transitions/{action}")
def post_possession_transition(
    possession_id: str,
    action: str,
    body: PossessionTransitionRequest = PossessionTransitionRequest(),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    offline_replay: str | None = Header(None, alias="X-RailOS-Offline-Replay"),
    user: User = Depends(auth),
):
    return handle_possession_action(possession_id, action, body, user, idempotency_key, offline_replay)

# Convenience routes for all actions
@app.post("/api/v1/possessions/{possession_id}/request-clearance")
def possession_request_clearance(possession_id: str, body: PossessionTransitionRequest = PossessionTransitionRequest(), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), offline_replay: str | None = Header(None, alias="X-RailOS-Offline-Replay"), user: User = Depends(auth)):
    return handle_possession_action(possession_id, "request-clearance", body, user, idempotency_key, offline_replay)

@app.post("/api/v1/possessions/{possession_id}/grant-clearance")
def possession_grant_clearance(possession_id: str, body: PossessionTransitionRequest = PossessionTransitionRequest(), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), offline_replay: str | None = Header(None, alias="X-RailOS-Offline-Replay"), user: User = Depends(auth)):
    return handle_possession_action(possession_id, "grant-clearance", body, user, idempotency_key, offline_replay)

@app.post("/api/v1/possessions/{possession_id}/defer")
def possession_defer(possession_id: str, body: PossessionTransitionRequest = PossessionTransitionRequest(), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), offline_replay: str | None = Header(None, alias="X-RailOS-Offline-Replay"), user: User = Depends(auth)):
    return handle_possession_action(possession_id, "defer", body, user, idempotency_key, offline_replay)

@app.post("/api/v1/possessions/{possession_id}/start-isolation")
def possession_start_isolation(possession_id: str, body: PossessionTransitionRequest = PossessionTransitionRequest(), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), offline_replay: str | None = Header(None, alias="X-RailOS-Offline-Replay"), user: User = Depends(auth)):
    return handle_possession_action(possession_id, "start-isolation", body, user, idempotency_key, offline_replay)

@app.post("/api/v1/possessions/{possession_id}/issue-t351")
def possession_issue_t351(possession_id: str, body: PossessionTransitionRequest = PossessionTransitionRequest(), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), offline_replay: str | None = Header(None, alias="X-RailOS-Offline-Replay"), user: User = Depends(auth)):
    return handle_possession_action(possession_id, "issue-t351", body, user, idempotency_key, offline_replay)

@app.post("/api/v1/possessions/{possession_id}/endorse-t351")
def possession_endorse_t351(possession_id: str, body: PossessionTransitionRequest = PossessionTransitionRequest(), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), offline_replay: str | None = Header(None, alias="X-RailOS-Offline-Replay"), user: User = Depends(auth)):
    return handle_possession_action(possession_id, "endorse-t351", body, user, idempotency_key, offline_replay)

@app.post("/api/v1/possessions/{possession_id}/confirm-earthing")
def possession_confirm_earthing(possession_id: str, body: PossessionTransitionRequest = PossessionTransitionRequest(), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), offline_replay: str | None = Header(None, alias="X-RailOS-Offline-Replay"), user: User = Depends(auth)):
    return handle_possession_action(possession_id, "confirm-earthing", body, user, idempotency_key, offline_replay)

@app.post("/api/v1/possessions/{possession_id}/issue-ptw")
def possession_issue_ptw(possession_id: str, body: PossessionTransitionRequest = PossessionTransitionRequest(), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), offline_replay: str | None = Header(None, alias="X-RailOS-Offline-Replay"), user: User = Depends(auth)):
    return handle_possession_action(possession_id, "issue-ptw", body, user, idempotency_key, offline_replay)

@app.post("/api/v1/possessions/{possession_id}/plant-protection")
def possession_plant_protection(possession_id: str, body: PossessionTransitionRequest = PossessionTransitionRequest(), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), offline_replay: str | None = Header(None, alias="X-RailOS-Offline-Replay"), user: User = Depends(auth)):
    return handle_possession_action(possession_id, "plant-protection", body, user, idempotency_key, offline_replay)

@app.post("/api/v1/possessions/{possession_id}/start-work")
def possession_start_work(possession_id: str, body: PossessionTransitionRequest = PossessionTransitionRequest(), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), offline_replay: str | None = Header(None, alias="X-RailOS-Offline-Replay"), user: User = Depends(auth)):
    return handle_possession_action(possession_id, "start-work", body, user, idempotency_key, offline_replay)

@app.post("/api/v1/possessions/{possession_id}/declare-overrun")
def possession_declare_overrun(possession_id: str, body: PossessionTransitionRequest = PossessionTransitionRequest(), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), offline_replay: str | None = Header(None, alias="X-RailOS-Offline-Replay"), user: User = Depends(auth)):
    return handle_possession_action(possession_id, "declare-overrun", body, user, idempotency_key, offline_replay)

@app.post("/api/v1/possessions/{possession_id}/start-testing")
def possession_start_testing(possession_id: str, body: PossessionTransitionRequest = PossessionTransitionRequest(), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), offline_replay: str | None = Header(None, alias="X-RailOS-Offline-Replay"), user: User = Depends(auth)):
    return handle_possession_action(possession_id, "start-testing", body, user, idempotency_key, offline_replay)

@app.post("/api/v1/possessions/{possession_id}/record-correspondence-test")
def possession_record_correspondence_test(possession_id: str, body: PossessionTransitionRequest = PossessionTransitionRequest(), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), offline_replay: str | None = Header(None, alias="X-RailOS-Offline-Replay"), user: User = Depends(auth)):
    return handle_possession_action(possession_id, "record-correspondence-test", body, user, idempotency_key, offline_replay)

@app.post("/api/v1/possessions/{possession_id}/request-handback")
def possession_request_handback(possession_id: str, body: PossessionTransitionRequest = PossessionTransitionRequest(), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), offline_replay: str | None = Header(None, alias="X-RailOS-Offline-Replay"), user: User = Depends(auth)):
    return handle_possession_action(possession_id, "request-handback", body, user, idempotency_key, offline_replay)

@app.post("/api/v1/possessions/{possession_id}/remove-discharge-rods")
def possession_remove_discharge_rods(possession_id: str, body: PossessionTransitionRequest = PossessionTransitionRequest(), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), offline_replay: str | None = Header(None, alias="X-RailOS-Offline-Replay"), user: User = Depends(auth)):
    return handle_possession_action(possession_id, "remove-discharge-rods", body, user, idempotency_key, offline_replay)

@app.post("/api/v1/possessions/{possession_id}/cancel-ptw")
def possession_cancel_ptw(possession_id: str, body: PossessionTransitionRequest = PossessionTransitionRequest(), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), offline_replay: str | None = Header(None, alias="X-RailOS-Offline-Replay"), user: User = Depends(auth)):
    return handle_possession_action(possession_id, "cancel-ptw", body, user, idempotency_key, offline_replay)

@app.post("/api/v1/possessions/{possession_id}/reconnect-t351")
def possession_reconnect_t351(possession_id: str, body: PossessionTransitionRequest = PossessionTransitionRequest(), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), offline_replay: str | None = Header(None, alias="X-RailOS-Offline-Replay"), user: User = Depends(auth)):
    return handle_possession_action(possession_id, "reconnect-t351", body, user, idempotency_key, offline_replay)

@app.post("/api/v1/possessions/{possession_id}/re-energise")
def possession_re_energise(possession_id: str, body: PossessionTransitionRequest = PossessionTransitionRequest(), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), offline_replay: str | None = Header(None, alias="X-RailOS-Offline-Replay"), user: User = Depends(auth)):
    return handle_possession_action(possession_id, "re-energise", body, user, idempotency_key, offline_replay)

@app.post("/api/v1/possessions/{possession_id}/certify-fitness")
def possession_certify_fitness(possession_id: str, body: PossessionTransitionRequest = PossessionTransitionRequest(), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), offline_replay: str | None = Header(None, alias="X-RailOS-Offline-Replay"), user: User = Depends(auth)):
    return handle_possession_action(possession_id, "certify-fitness", body, user, idempotency_key, offline_replay)

@app.post("/api/v1/possessions/{possession_id}/station-close")
def possession_station_close(possession_id: str, body: PossessionTransitionRequest = PossessionTransitionRequest(), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), offline_replay: str | None = Header(None, alias="X-RailOS-Offline-Replay"), user: User = Depends(auth)):
    return handle_possession_action(possession_id, "station-close", body, user, idempotency_key, offline_replay)

@app.post("/api/v1/possessions/{possession_id}/close")
def possession_close(possession_id: str, body: PossessionTransitionRequest = PossessionTransitionRequest(), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), offline_replay: str | None = Header(None, alias="X-RailOS-Offline-Replay"), user: User = Depends(auth)):
    return handle_possession_action(possession_id, "close", body, user, idempotency_key, offline_replay)

@app.post("/api/v1/possessions/{possession_id}/cancel")
def possession_cancel(possession_id: str, body: PossessionTransitionRequest = PossessionTransitionRequest(), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), offline_replay: str | None = Header(None, alias="X-RailOS-Offline-Replay"), user: User = Depends(auth)):
    return handle_possession_action(possession_id, "cancel", body, user, idempotency_key, offline_replay)

@app.post("/api/v1/possessions/{possession_id}/abandon")
def possession_abandon(possession_id: str, body: PossessionTransitionRequest = PossessionTransitionRequest(), idempotency_key: str | None = Header(None, alias="Idempotency-Key"), offline_replay: str | None = Header(None, alias="X-RailOS-Offline-Replay"), user: User = Depends(auth)):
    return handle_possession_action(possession_id, "abandon", body, user, idempotency_key, offline_replay)

@app.post("/api/v1/possessions/backfill")
def backfill_possessions(user: User = Depends(allow("CONTROL_OFFICER"))):
    created = []
    with state.transaction():
        for p in state.plans.values():
            if p.status == PlanStatus.APPROVED:
                ensure_chain(p)
                for b in p.blocks:
                    pid = f"POS-{b.blockId}"
                    if pid not in state.possessions:
                        created.extend(open_possessions_for_plan(p, user.user_id, normalize_role(user.role)))
    return {"createdPossessionIds": created, "count": len(created), "synthetic": True}

@app.get("/api/v1/block-bursts")
def list_block_bursts(_: User = Depends(auth)):
    bursts = list(state.block_bursts.values())
    return {"items": [b.model_dump(by_alias=True, mode="json") if hasattr(b, "model_dump") else b for b in bursts], "count": len(bursts), "synthetic": True}

@app.get("/api/v1/notifications")
def notifications(recipientRole: str | None = None, _: User = Depends(auth)):
    items = list(state.notifications.values())
    if recipientRole:
        norm = normalize_role(recipientRole)
        items = [i for i in items if normalize_role(i.get("recipientRole")) == norm]
    return {"items": items, "count": len(items), "synthetic": True}

@app.post("/api/v1/notifications/{notification_id}/acknowledge")
@app.post("/api/v1/notifications/{notification_id}/ack")
def acknowledge(notification_id:str,user:User=Depends(auth)):
    with state.transaction():
        note=state.notifications.get(notification_id)
        if note is None: raise HTTPException(404,{"code":"NOT_FOUND","message":"notification not found"})
        before=copy.deepcopy(note); note["acknowledged"]=True; note["acknowledgedBy"]=user.user_id; state.emit("NOTIFICATION_ACKNOWLEDGED",notification_id,note,user.user_id,before=before,notify=False); return note

@app.get("/api/v1/analytics")
@app.get("/api/v1/analytics/summary")
def analytics(_:User=Depends(auth)):
    bursts = list(state.block_bursts.values())
    total_burst_min = sum(b.overrunMinutes for b in bursts)
    burst_by_dept: dict[str, int] = {}
    burst_by_cause: dict[str, int] = {}
    for b in bursts:
        burst_by_dept[b.department] = burst_by_dept.get(b.department, 0) + b.overrunMinutes
        burst_by_cause[b.causeCategory] = burst_by_cause.get(b.causeCategory, 0) + b.overrunMinutes

    return {
        "label": "Synthetic Hackathon Simulation",
        "tasks": len(state.tasks),
        "defects": len(state.defects),
        "criticalTasks": sum(t.severity>=9 for t in state.tasks.values()),
        "overdueTasks": sum(t.overdueDays>0 for t in state.tasks.values()),
        "completedTasks": sum(t.status==TaskStatus.COMPLETED for t in state.tasks.values()),
        "maintenanceDebt": sum(t.overdueDays*t.criticality for t in state.tasks.values()),
        "blockBursts": {
            "totalBursts": len(bursts),
            "totalOverrunMinutes": total_burst_min,
            "byDepartment": burst_by_dept,
            "byCause": burst_by_cause,
            "items": [b.model_dump(by_alias=True, mode="json") if hasattr(b, "model_dump") else b for b in bursts],
        },
        "synthetic": True,
    }

@app.get("/api/v1/integrations/status")
def integration_status(_:User=Depends(auth)): return {"synthetic":True,"scenario":"GZB_ALJN_DEMO","sources":{n:a.health() for n,a in state.adapters.items()},"ingestion":state.ingestion_records}

@app.get("/api/v1/events")
def events(after:int=0,_:User=Depends(auth)): return {"events":[e for e in state.events if e["sequence"]>after],"nextSequence":len(state.events)}

@app.post("/api/v1/events/replay")
def replay(after:int=0,user:User=Depends(auth)): return events(after,user)

async def websocket_events(socket:WebSocket):
    # Browsers cannot attach arbitrary headers during a native WebSocket
    # handshake.  Keep the existing header contract for native/mobile clients,
    # while allowing the desk browser to authenticate with the same normalized
    # values in the query string (wss://.../events/ws?userId=...&role=...).
    from .auth import ENABLE_SYNTHETIC_AUTH
    token = socket.query_params.get("access_token")
    authorization = socket.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
    if token:
        try:
            payload = decode_access_token(token)
        except HTTPException:
            await socket.close(code=4401)
            return
        user, role = payload.get("sub"), payload.get("role")
    elif ENABLE_SYNTHETIC_AUTH:
        user = socket.headers.get("x-railos-user") or socket.query_params.get("userId") or socket.query_params.get("user")
        role = socket.headers.get("x-railos-role") or socket.query_params.get("role")
    else:
        await socket.close(code=4401)
        return
    if not user: await socket.close(code=4401); return
    norm_role = normalize_role(role)
    if norm_role not in VALID_ROLES: await socket.close(code=4403); return
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
