"""Canonical RailOS data contracts.

Matches PRD section 4.3/4.4/4.5 field names, plus the statutory fields the hard
constraints (Ground Reality Report section 23) need. Additions are catalogued in
docs/domain/02-schema-deltas.md so the API/DB agent can mirror them.

Time is integer minutes from the horizon start. Distance is integer metres.
"""

from pydantic import BaseModel, Field, model_validator

from .enums import (
    MIN_MACHINE_BLOCK_MINUTES,
    BlockType,
    Compatibility,
    Department,
    LineConfig,
    MachineType,
    ObjectiveProfile,
    PlanStatus,
    Severity,
    TaskStatus,
    TaskType,
    Track,
    TrainClass,
)


class BlockSection(BaseModel):
    sectionId: str
    fromStation: str
    toStation: str
    startM: int
    endM: int
    tracks: list[Track]
    mps: int = Field(default=110, gt=0, description="max permissible speed, kmph")
    """Sectional speed. Needed to price a caution order or a temporary speed
    restriction: the delay is (dist/restricted - dist/mps), so without an MPS the
    consequences of HC-010 and HC-018 cannot be computed."""

    @property
    def lengthKm(self) -> float:
        return (self.endM - self.startM) / 1000.0


class Corridor(BaseModel):
    corridorId: str
    name: str
    lineConfig: LineConfig
    tracks: list[Track]
    sections: list[BlockSection]


class Asset(BaseModel):
    assetId: str
    assetType: str
    sectionId: str
    track: Track | None = None
    locationM: int
    criticality: int = Field(ge=1, le=10)
    oheElementarySection: str | None = None


class MaintenanceTask(BaseModel):
    taskId: str
    department: Department
    assetId: str
    corridorId: str
    sectionId: str
    track: Track
    kmStart: float
    kmEnd: float
    taskType: TaskType
    severity: int = Field(ge=1, le=10)
    criticality: int = Field(ge=1, le=10)
    dueMinute: int
    estimatedDuration: int = Field(gt=0, description="minutes")
    durationStdDev: int = Field(default=0, ge=0, description="minutes; drives SO-005 buffer")
    blockRequired: bool = True
    blockType: BlockType = BlockType.TRAFFIC
    status: TaskStatus = TaskStatus.PENDING

    # Statutory / physical attributes required by the hard constraints.
    machineType: MachineType = MachineType.NONE
    requiresPTW: bool = False                  # HC-003 / HC-004 traction power block
    requiresT351: bool = False                 # HC-005 S&T disconnection
    requiresCorrespondenceTest: bool = False   # HC-006
    infringesAdjacent: bool = False            # HC-010 caution order T/409
    hasMobileLighting: bool = True             # HC-015 daylight restriction
    requiresSntEscort: bool = False            # HC-017 track circuit continuity
    imposesSpeedRestriction: bool = False      # HC-018 post-block SR footprint
    oheElementarySection: str | None = None
    resourceIds: list[str] = Field(default_factory=list)
    gangId: str | None = None
    overdueDays: int = 0
    isEmergency: bool = False
    detectedAtMinute: int | None = None        # HC-011 IMR clock start
    locked: bool = False                       # replanning: started / immutable

    @property
    def locationM(self) -> int:
        return int(self.kmStart * 1000)

    @model_validator(mode="after")
    def _duration_meets_statutory_minimum(self) -> "MaintenanceTask":
        floor = MIN_MACHINE_BLOCK_MINUTES[self.machineType]
        if self.estimatedDuration < floor:
            raise ValueError(
                f"{self.taskId}: {self.machineType} needs >= {floor} min (HC-002), "
                f"got {self.estimatedDuration}"
            )
        return self


class Defect(BaseModel):
    defectId: str
    assetId: str
    sectionId: str
    severityCode: Severity
    detectedAtMinute: int
    taskId: str | None = None
    repeatCount: int = 0


class TrainMovement(BaseModel):
    trainId: str
    sectionId: str
    track: Track
    entry: int
    exit: int
    trainClass: TrainClass
    priority: int = Field(ge=1, le=10)
    delayMinutes: int = 0


class GoodsForecast(BaseModel):
    rakeId: str
    sectionId: str
    track: Track
    windowStart: int
    windowEnd: int
    probability: float = Field(ge=0.0, le=1.0)
    priorityWeight: float = 1.0


class BlockWindow(BaseModel):
    """Officially charted corridor block opportunity in the WTT."""

    windowId: str
    sectionId: str
    track: Track
    start: int
    end: int
    availability: str = "AVAILABLE"


class Resource(BaseModel):
    resourceId: str
    resourceType: str            # MACHINE | GANG | ESCORT
    machineType: MachineType = MachineType.NONE
    department: Department
    homeDepot: str
    homeSectionId: str


class Dependency(BaseModel):
    predecessorTaskId: str
    successorTaskId: str
    lagMinutes: int = 0
    reason: str = ""


class ScenarioWorld(BaseModel):
    """Everything one optimization run reads. Immutable input."""

    horizonMinutes: int = 4320
    horizonStartIso: str = "2026-09-09T00:00:00+05:30"
    corridors: list[Corridor] = Field(default_factory=list)
    assets: list[Asset] = Field(default_factory=list)
    tasks: list[MaintenanceTask] = Field(default_factory=list)
    defects: list[Defect] = Field(default_factory=list)
    trains: list[TrainMovement] = Field(default_factory=list)
    goods: list[GoodsForecast] = Field(default_factory=list)
    windows: list[BlockWindow] = Field(default_factory=list)
    resources: list[Resource] = Field(default_factory=list)
    dependencies: list[Dependency] = Field(default_factory=list)

    def task(self, task_id: str) -> MaintenanceTask:
        for t in self.tasks:
            if t.taskId == task_id:
                return t
        raise KeyError(task_id)


# --- engine outputs -------------------------------------------------------


class Factor(BaseModel):
    """One named, weighted contribution. Weights are never hidden."""

    name: str
    raw: float
    weight: float
    contribution: float
    note: str = ""


class PriorityResult(BaseModel):
    taskId: str
    score: float
    band: str
    factors: list[Factor]


class RiskResult(BaseModel):
    taskId: str
    current: float
    at24h: float
    at72h: float
    trend: str
    maxDeferralMinutes: int
    basis: str = "deterministic heuristic, not a trained model"


class Opportunity(BaseModel):
    opportunityId: str
    sectionId: str
    track: Track
    start: int
    end: int
    minutes: int
    trafficImpact: str
    blockType: BlockType = BlockType.TRAFFIC
    shadowOf: str | None = None
    candidateTaskIds: list[str] = Field(default_factory=list)


class BundleCandidate(BaseModel):
    bundleId: str
    taskIds: list[str]
    blockType: BlockType
    sequence: list[str] = Field(default_factory=list)
    requiredResourceIds: list[str] = Field(default_factory=list)
    compatibility: Compatibility = Compatibility.COMPATIBLE
    rationale: list[str] = Field(default_factory=list)


class Assignment(BaseModel):
    taskId: str
    blockId: str
    start: int
    end: int
    explanation: list[Factor] = Field(default_factory=list)


class ScheduledBlock(BaseModel):
    blockId: str
    sectionId: str
    track: Track
    blockType: BlockType
    start: int
    end: int
    taskIds: list[str]
    departments: list[Department]
    opportunityId: str | None = None


class UnassignedTask(BaseModel):
    taskId: str
    reason: str


class PlanMetrics(BaseModel):
    blockUtilisation: float = 0.0
    maintenanceYield: float = 0.0
    maintenanceDebt: float = 0.0
    coordinationRatio: float = 0.0
    criticalCompletionRate: float = 0.0
    trainDisruptionMinutes: int = 0
    freightDetentionMinutes: int = 0
    tasksScheduled: int = 0
    tasksUnassigned: int = 0
    srFootprintKmDays: float = 0.0


class Plan(BaseModel):
    planId: str
    planVersion: int
    parentPlanId: str | None = None
    status: PlanStatus = PlanStatus.GENERATED
    objectiveProfile: ObjectiveProfile
    horizonMinutes: int
    blocks: list[ScheduledBlock] = Field(default_factory=list)
    assignments: list[Assignment] = Field(default_factory=list)
    unassigned: list[UnassignedTask] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metrics: PlanMetrics = Field(default_factory=PlanMetrics)
    objectiveBreakdown: dict[str, float] = Field(default_factory=dict)
    solverStatus: str = "UNKNOWN"
    runtime: dict[str, float | str] = Field(default_factory=dict)
    provenance: str = ""
