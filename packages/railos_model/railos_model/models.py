"""Canonical RailOS data contracts.

Matches PRD section 4.3/4.4/4.5 field names, plus the statutory fields the hard
constraints (Ground Reality Report section 23) need. Additions are catalogued in
docs/domain/02-schema-deltas.md so the API/DB agent can mirror them.

Time is integer minutes from the horizon start. Distance is integer metres.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from .enums import (
    MIN_MACHINE_BLOCK_MINUTES,
    BlockType,
    Compatibility,
    Department,
    EvidenceKind,
    EvidenceStatus,
    GeoVerdict,
    LineConfig,
    MachineType,
    ObjectiveProfile,
    PlanStatus,
    PossessionState,
    SanctionAuthority,
    Severity,
    SignatureDecision,
    TaskStatus,
    TaskType,
    Track,
    TrainClass,
    UserRole,
    WorkExecutionStatus,
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


# --- network and map contracts -------------------------------------------


class SourceSnapshot(BaseModel):
    """Immutable source reference for geometry or catalogue data.

    A snapshot describes where data came from; it does not imply that a
    community or synthetic source is operationally authoritative.
    """

    snapshotId: str
    sourceUrl: str | None = None
    retrievedAt: str | None = None
    licence: str | None = None
    checksumSha256: str | None = None
    immutable: bool = True


class DataProvenance(BaseModel):
    synthetic: bool = True
    label: str = "Synthetic regional pilot data"
    source: str = "RailOS curated demo catalogue"
    generatedAt: str | None = None
    sourceType: str = "synthetic"
    sourceSnapshot: SourceSnapshot | None = None
    isOperationallyAuthoritative: bool = False


class NetworkMetrics(BaseModel):
    pendingMaintenanceCount: int = 0
    criticalDefectCount: int = 0
    maintenanceDebt: float = 0.0
    activeBlocks: int = 0
    assetAvailability: float = 100.0
    trafficPressure: float = 0.0
    openOpportunityCount: int = 0


class GeoJSONGeometry(BaseModel):
    type: Literal["Point", "LineString", "MultiLineString", "Polygon", "MultiPolygon"]
    coordinates: Any


class RailwayZone(BaseModel):
    zoneId: str
    code: str
    name: str
    centroid: tuple[float, float]
    metrics: NetworkMetrics = Field(default_factory=NetworkMetrics)
    planningEnabled: bool = False
    provenance: DataProvenance = Field(default_factory=DataProvenance)


class RailwayDivision(BaseModel):
    divisionId: str
    zoneId: str
    code: str
    name: str
    centroid: tuple[float, float]
    metrics: NetworkMetrics = Field(default_factory=NetworkMetrics)
    planningEnabled: bool = False
    provenance: DataProvenance = Field(default_factory=DataProvenance)


class RailwaySection(BaseModel):
    sectionId: str
    divisionId: str
    zoneId: str
    corridorId: str | None = None
    code: str
    name: str
    fromStation: str
    toStation: str
    tracks: list[Track]
    geometry: GeoJSONGeometry
    metrics: NetworkMetrics = Field(default_factory=NetworkMetrics)
    planningEnabled: bool = False
    provenance: DataProvenance = Field(default_factory=DataProvenance)


class RailwaySegment(BaseModel):
    segmentId: str
    sectionId: str
    divisionId: str
    zoneId: str
    geometry: GeoJSONGeometry
    riskScore: int = Field(default=0, ge=0, le=100)
    maintenancePressure: int = Field(default=0, ge=0, le=100)
    trafficPressure: int = Field(default=0, ge=0, le=200)
    activeBlock: bool = False
    planningEnabled: bool = False
    provenance: DataProvenance = Field(default_factory=DataProvenance)


class Station(BaseModel):
    stationId: str
    code: str
    name: str
    sectionIds: list[str] = Field(default_factory=list)
    geometry: GeoJSONGeometry
    planningEnabled: bool = False
    provenance: DataProvenance = Field(default_factory=DataProvenance)


class NetworkCatalog(BaseModel):
    zones: list[RailwayZone] = Field(default_factory=list)
    divisions: list[RailwayDivision] = Field(default_factory=list)
    sections: list[RailwaySection] = Field(default_factory=list)
    segments: list[RailwaySegment] = Field(default_factory=list)
    stations: list[Station] = Field(default_factory=list)
    provenance: DataProvenance = Field(default_factory=DataProvenance)


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


# --- field evidence and execution contracts ----------------------------------


class GeoSample(BaseModel):
    timestampUtc: str
    latitude: float
    longitude: float
    altitudeMeters: float | None = None
    accuracyMeters: float
    speedMps: float | None = None
    bearingDegrees: float | None = None
    isMocked: bool = False


class EvidenceRequirement(BaseModel):
    requirementId: str
    kind: EvidenceKind
    required: bool = True
    minDurationSeconds: int | None = None
    maxDurationSeconds: int | None = 90
    targetRadiusMeters: float = 100.0
    targetAccuracyMeters: float = 50.0


class WorkStep(BaseModel):
    stepId: str
    taskId: str
    stepIndex: int
    title: str
    description: str = ""
    requiresPhoto: bool = True
    requiresVideo: bool = False
    targetLatitude: float
    targetLongitude: float
    targetRadiusMeters: float = 100.0
    status: WorkExecutionStatus = WorkExecutionStatus.READY
    evidenceId: str | None = None


class EvidenceTargetSnapshot(BaseModel):
    latitude: float
    longitude: float
    radiusMeters: float = 100.0
    sectionCode: str = ""
    kmPost: str = ""


class EvidenceManifestV1(BaseModel):
    manifestVersion: str = "1.0"
    evidenceId: str
    taskId: str
    stepId: str
    supervisorId: str
    kind: EvidenceKind
    captureStartTimeUtc: str
    captureEndTimeUtc: str | None = None
    originalSha256: str
    proofSha256: str
    originalSizeBytes: int
    proofSizeBytes: int
    mediaProperties: dict[str, Any] = Field(default_factory=dict)
    targetLocation: EvidenceTargetSnapshot
    locationSamples: list[GeoSample] = Field(default_factory=list)
    geoVerdict: GeoVerdict
    distanceToTargetMeters: float | None = None
    exceptionReason: str | None = None
    deviceInfo: dict[str, Any] = Field(default_factory=dict)
    clientCreatedTimeUtc: str
    signedAtUtc: str | None = None
    serverSignature: str | None = None


class EvidenceItem(BaseModel):
    evidenceId: str
    taskId: str
    stepId: str
    supervisorId: str
    kind: EvidenceKind
    status: EvidenceStatus = EvidenceStatus.DRAFT
    originalStorageKey: str | None = None
    proofStorageKey: str | None = None
    originalSha256: str | None = None
    proofSha256: str | None = None
    originalSizeBytes: int | None = None
    proofSizeBytes: int | None = None
    captureTimeUtc: str
    startLatitude: float
    startLongitude: float
    gpsAccuracyMeters: float
    distanceToTargetMeters: float | None = None
    geoVerdict: GeoVerdict
    exceptionReason: str | None = None
    reviewerId: str | None = None
    reviewNotes: str | None = None
    reviewedAt: str | None = None
    canonicalManifest: EvidenceManifestV1 | None = None
    ed25519Signature: str | None = None
    createdTimeUtc: str = ""
    updatedTimeUtc: str = ""


class SupervisorAreaAssignment(BaseModel):
    assignmentId: str
    supervisorId: str
    fieldAreaId: str
    areaName: str = ""
    sectionCodes: list[str] = Field(default_factory=list)
    authorizedFrom: str
    authorizedUntil: str
    active: bool = True


class EmergencyReport(BaseModel):
    reportId: str
    supervisorId: str = ""
    sectionCode: str
    kmPost: str
    latitude: float
    longitude: float
    severity: Severity = Severity.IMR
    hazardType: str
    description: str
    photoEvidenceId: str | None = None
    reportedAtUtc: str = ""
    status: str = "OPEN"


# --- Sanction chain contracts ------------------------------------------------


class AuthoritySignature(BaseModel):
    signatureId: str
    authority: SanctionAuthority
    decision: SignatureDecision = SignatureDecision.GRANTED
    role: str
    userId: str
    reason: str = ""
    formReference: str = ""
    signedAtUtc: str
    planVersion: int
    possessionId: str | None = None


class SanctionChain(BaseModel):
    planId: str
    planVersion: int
    requiredAuthorities: list[SanctionAuthority] = Field(default_factory=list)
    signatures: list[AuthoritySignature] = Field(default_factory=list)
    complete: bool = False
    refused: bool = False
    derivedFrom: list[str] = Field(default_factory=list)
    backfilled: bool = False


# --- Possession runtime entities ---------------------------------------------


class FormT351(BaseModel):
    formNumber: str
    sectionId: str
    track: Track
    issuedBy: str
    issuedAtUtc: str
    endorsedBy: str | None = None
    endorsedAtUtc: str | None = None
    reconnectedBy: str | None = None
    reconnectedAtUtc: str | None = None
    status: str = "ISSUED"  # ISSUED, ENDORSED, RECONNECTED, CLOSED, CANCELLED
    remarks: str = ""


class PermitToWork(BaseModel):
    ptwNumber: str
    oheSection: str
    isolatorNumber: str
    issuedBy: str
    issuedAtUtc: str
    earthingConfirmed: bool = False
    cancelledBy: str | None = None
    cancelledAtUtc: str | None = None
    reEnergised: bool = False
    reEnergisedBy: str | None = None
    reEnergisedAtUtc: str | None = None
    dischargeRodsRemoved: bool = False
    status: str = "ISSUED"  # PENDING (earthing), ISSUED, CANCELLED
    remarks: str = ""


class ProtectionRecord(BaseModel):
    bannerFlagsPlaced: bool = False
    detonatorCount: int = Field(default=0, ge=0)
    handSignalPosted: bool = False
    plantedBy: str = ""
    plantedAtUtc: str = ""
    ruleCitation: str = "IRPWM 806"
    remarks: str = ""


class CorrespondenceTest(BaseModel):
    testId: str
    testedBy: str
    startAtUtc: str
    completedAtUtc: str
    durationMinutes: int = Field(ge=0)
    pointsTested: bool = True
    signalsTested: bool = True
    trackCircuitsTested: bool = True
    passed: bool = True
    ruleCitation: str = "HC-006"
    remarks: str = ""


class FitnessCertificate(BaseModel):
    certificateNumber: str
    certifiedBy: str
    certifiedAtUtc: str
    tsrSpeedKmph: int = 20  # 20 / 45 / 75 TSR ladder
    trackFitForTraffic: bool = True
    overheadClearanceFit: bool = True
    signallingFit: bool = True
    ruleCitation: str = "HC-018"
    remarks: str = ""

    @model_validator(mode="after")
    def _validate_tsr_ladder(self) -> "FitnessCertificate":
        if self.tsrSpeedKmph not in {20, 45, 75}:
            raise ValueError("tsrSpeedKmph must be one of 20, 45, or 75 (HC-018)")
        return self


class PossessionTransition(BaseModel):
    transitionId: str
    fromState: PossessionState
    toState: PossessionState
    action: str
    actor: str
    role: str
    occurredAtUtc: str
    clientEventAtUtc: str | None = None
    ruleCitation: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
    replayed: bool = False


class BlockBurst(BaseModel):
    burstId: str
    possessionId: str
    planId: str
    sectionId: str
    track: Track
    department: str = "ENGG"
    plannedEndUtc: str
    actualCloseUtc: str
    overrunMinutes: int = Field(ge=0)
    causeCategory: str = "EXECUTION"
    remarks: str = ""
    occurredAtUtc: str = ""


class Possession(BaseModel):
    possessionId: str
    planId: str
    planVersion: int
    blockId: str
    sectionId: str
    track: Track
    state: PossessionState = PossessionState.SANCTIONED
    plannedStartUtc: str
    plannedEndUtc: str
    actualStartUtc: str | None = None
    actualEndUtc: str | None = None
    deferralCount: int = 0
    deferredUntilUtc: str | None = None
    requiresPTW: bool = False
    requiresT351: bool = False
    requiresCorrespondenceTest: bool = False
    stationClosed: bool = False
    stationClosedBy: str | None = None
    stationClosedAtUtc: str | None = None
    formT351: FormT351 | None = None
    permitToWork: PermitToWork | None = None
    protectionRecord: ProtectionRecord | None = None
    correspondenceTest: CorrespondenceTest | None = None
    fitnessCertificate: FitnessCertificate | None = None
    transitions: list[PossessionTransition] = Field(default_factory=list)
    assignedTaskIds: list[str] = Field(default_factory=list)
    department: str = "ENGG"
    leadInMinutes: int = 0
    createdAtUtc: str = ""
    updatedAtUtc: str = ""


