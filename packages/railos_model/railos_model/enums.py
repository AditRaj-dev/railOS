"""Enumerations for the RailOS domain. IR-authentic vocabulary only."""

from enum import StrEnum


class Department(StrEnum):
    ENGG = "ENGG"   # Civil / Permanent Way
    SNT = "SNT"     # Signal & Telecommunication
    TRD = "TRD"     # Traction Distribution


class Track(StrEnum):
    UP = "UP"
    DOWN = "DOWN"
    THIRD = "THIRD"
    SINGLE = "SINGLE"


class LineConfig(StrEnum):
    SINGLE = "SINGLE"
    DOUBLE = "DOUBLE"
    MULTI = "MULTI"


class BlockType(StrEnum):
    """Ground Reality Report section 2.3."""

    TRAFFIC = "TRAFFIC"
    POWER = "POWER"
    INTEGRATED = "INTEGRATED"
    SHADOW = "SHADOW"
    DISCONNECTION = "DISCONNECTION"
    MEGA = "MEGA"
    EMERGENCY = "EMERGENCY"


class MachineType(StrEnum):
    BCM = "BCM"                    # Ballast Cleaning Machine
    CSM = "CSM"                    # Plain track tamper (09-3X)
    UNIMAT = "UNIMAT"              # Points & crossing tamper
    TRT = "TRT"                    # Track Renewal Train
    DGS = "DGS"                    # Dynamic Track Stabilizer
    TOWER_WAGON = "TOWER_WAGON"    # TRD OHE vehicle
    NONE = "NONE"                  # manual / gang work


#: Statutory minimum block duration in minutes, Ground Reality Report section 8.1 (HC-002).
MIN_MACHINE_BLOCK_MINUTES: dict[MachineType, int] = {
    MachineType.BCM: 240,
    MachineType.CSM: 150,
    MachineType.UNIMAT: 150,
    MachineType.TRT: 240,
    MachineType.DGS: 120,
    MachineType.TOWER_WAGON: 120,
    MachineType.NONE: 0,
}

#: Ineffective setup / winding time in minutes, same table. Counted inside the block.
MACHINE_SETUP_MINUTES: dict[MachineType, int] = {
    MachineType.BCM: 45,
    MachineType.CSM: 30,
    MachineType.UNIMAT: 35,
    MachineType.TRT: 60,
    MachineType.DGS: 20,
    MachineType.TOWER_WAGON: 20,
    MachineType.NONE: 0,
}


class TaskType(StrEnum):
    # ENGG
    TAMPING = "TAMPING"
    DEEP_SCREENING = "DEEP_SCREENING"
    RAIL_REPLACEMENT = "RAIL_REPLACEMENT"
    SLEEPER_RENEWAL = "SLEEPER_RENEWAL"
    TURNOUT_RENEWAL = "TURNOUT_RENEWAL"
    DESTRESSING = "DESTRESSING"
    USFD_INSPECTION = "USFD_INSPECTION"
    # SNT
    POINT_MACHINE_MAINT = "POINT_MACHINE_MAINT"
    TRACK_CIRCUIT_BOND = "TRACK_CIRCUIT_BOND"
    AXLE_COUNTER_CALIB = "AXLE_COUNTER_CALIB"
    GJ_REPLACEMENT = "GJ_REPLACEMENT"
    INTERLOCKING_WORK = "INTERLOCKING_WORK"
    SNT_DISCONNECTION = "SNT_DISCONNECTION"
    SNT_RECONNECTION = "SNT_RECONNECTION"
    # TRD
    OHE_INSPECTION = "OHE_INSPECTION"
    CATENARY_REPLACEMENT = "CATENARY_REPLACEMENT"
    OHE_BRACKET_ADJUST = "OHE_BRACKET_ADJUST"
    OHE_SLEWING = "OHE_SLEWING"
    TRD_ISOLATION = "TRD_ISOLATION"


class Severity(StrEnum):
    """Defect codes used by TMS / SMMS / TDMS."""

    IMR = "IMR"                                    # Immediate Removal (rail flaw) - 72 h statutory
    IMRW = "IMRW"                                  # Immediate Removal - weld
    OBS = "OBS"                                    # Observation
    OMS_PEAK_HIGH = "OMS_PEAK_HIGH"
    POINT_SLACK_DETECTION = "POINT_SLACK_DETECTION"
    OHE_DROPPING_FAULT = "OHE_DROPPING_FAULT"


class TrainClass(StrEnum):
    RAJDHANI = "RAJDHANI"
    VANDE_BHARAT = "VANDE_BHARAT"
    MAIL_EXPRESS = "MAIL_EXPRESS"
    SUBURBAN = "SUBURBAN"
    PASSENGER = "PASSENGER"
    GOODS = "GOODS"


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    PLANNED = "PLANNED"
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    DEFERRED = "DEFERRED"


class ObjectiveProfile(StrEnum):
    SAFETY_FIRST = "SAFETY_FIRST"
    BALANCED = "BALANCED"
    OPERATIONS_FIRST = "OPERATIONS_FIRST"


class PlanStatus(StrEnum):
    GENERATED = "GENERATED"
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class Compatibility(StrEnum):
    COMPATIBLE = "COMPATIBLE"
    SEQUENTIALLY_COMPATIBLE = "SEQUENTIALLY_COMPATIBLE"
    CONDITIONAL = "CONDITIONAL"
    INCOMPATIBLE = "INCOMPATIBLE"
    STRICTLY_PROHIBITED = "STRICTLY_PROHIBITED"


class WorkExecutionStatus(StrEnum):
    READY = "READY"
    STARTED = "STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    DELAYED = "DELAYED"
    CANNOT_COMPLETE = "CANNOT_COMPLETE"
    COMPLETED_PENDING_EVIDENCE = "COMPLETED_PENDING_EVIDENCE"
    COMPLETED = "COMPLETED"


class EvidenceKind(StrEnum):
    PHOTO = "PHOTO"
    VIDEO = "VIDEO"


class EvidenceStatus(StrEnum):
    DRAFT = "DRAFT"
    UPLOAD_PENDING = "UPLOAD_PENDING"
    UPLOADING = "UPLOADING"
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"
    FLAGGED_REVIEW = "FLAGGED_REVIEW"
    ACCEPTED_EXCEPTION = "ACCEPTED_EXCEPTION"
    REJECTED = "REJECTED"


class GeoVerdict(StrEnum):
    WITHIN_RADIUS = "WITHIN_RADIUS"
    OUTSIDE_RADIUS = "OUTSIDE_RADIUS"
    LOW_ACCURACY = "LOW_ACCURACY"
    NO_FIX = "NO_FIX"
    MOCKED_LOCATION = "MOCKED_LOCATION"
    CLOCK_DRIFT = "CLOCK_DRIFT"


class UserRole(StrEnum):
    SUPERVISOR = "SUPERVISOR"
    ADMIN = "ADMIN"
    DISPATCHER = "DISPATCHER"
    INSPECTOR = "INSPECTOR"
    STATION_MASTER = "STATION_MASTER"
    TPC = "TPC"
    CONTROL_OFFICER = "CONTROL_OFFICER"
    ENGINEERING = "ENGINEERING"
    SIGNAL_TELECOM = "SIGNAL_TELECOM"


class SanctionAuthority(StrEnum):
    SANCTION = "SANCTION"                 # Sr.DOM -> MANAGEMENT
    SECTION_CONTROL = "SECTION_CONTROL"   # -> CONTROL_OFFICER
    TRACTION_POWER = "TRACTION_POWER"     # -> TPC
    STATION = "STATION"                   # -> STATION_MASTER
    SNT = "SNT"                           # -> SIGNAL_TELECOM
    ENGINEERING_SSE = "ENGINEERING_SSE"   # -> ENGINEERING


class SignatureDecision(StrEnum):
    GRANTED = "GRANTED"
    REFUSED = "REFUSED"
    DEFERRED = "DEFERRED"
    WITHDRAWN = "WITHDRAWN"


class PossessionState(StrEnum):
    SANCTIONED = "SANCTIONED"
    CLEARANCE_REQUESTED = "CLEARANCE_REQUESTED"
    DEFERRED = "DEFERRED"
    CANCELLED = "CANCELLED"
    CLEARANCE_GRANTED = "CLEARANCE_GRANTED"
    ISOLATION_IN_PROGRESS = "ISOLATION_IN_PROGRESS"
    PROTECTED = "PROTECTED"
    LIVE = "LIVE"
    OVERRUNNING = "OVERRUNNING"
    TESTING = "TESTING"
    HANDBACK_REQUESTED = "HANDBACK_REQUESTED"
    FIT_CERTIFIED = "FIT_CERTIFIED"
    CLEARED = "CLEARED"
    ABANDONED = "ABANDONED"

