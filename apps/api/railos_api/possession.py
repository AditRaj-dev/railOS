"""Possession authority chain and runtime block lifecycle.

Implements stages 5-9 of the Indian Railways block lifecycle:
- Stage 5: Real-time clearance (Section Controller, deferrals, conflict check HC-014)
- Stage 6: Isolation & disconnection (Form T/351 SEM 11.4, PTW ACTM 20603, Protection IRPWM 806)
- Stage 7: Execution & live overrun monitoring (SO-005)
- Stage 8: Testing & handback (Correspondence test HC-006, PTW cancel HC-004, Fitness cert HC-018)
- Stage 9: Normalisation & block burst accounting (deterministic BST-{id})
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import HTTPException
from railos_model import (
    BlockBurst,
    BlockType,
    CorrespondenceTest,
    FitnessCertificate,
    FormT351,
    MaintenanceTask,
    PermitToWork,
    Plan,
    Possession,
    PossessionState,
    PossessionTransition,
    ProtectionRecord,
    SanctionAuthority,
    SignatureDecision,
)
from .roles import normalize_role

# Statutory timing constants (mirrored from domain specifications)
PTW_LEAD_IN = 20          # HC-003 ACTM 20603: switching + discharge rod earthing
PTW_HANDBACK = 15         # HC-004 ACTM 20610: men and material clear, rods removed
T351_LEAD_IN = 10         # HC-005 SEM 11.4: Station Master endorsement
CORRESPONDENCE_TEST = 30  # HC-006 post-Balasore safety directive: statutory minimum 30 min
SR_DAY_SPEEDS_KMPH = (20, 45, 75)  # HC-018 IRPWM 308: post-block speed ladder

ONLINE_AUTHORITY_ACTIONS: frozenset[str] = frozenset({
    "grant-clearance",
    "endorse-t351",
    "issue-ptw",
    "cancel-ptw",
    "re-energise",
    "certify-fitness",
    "station-close",
    "close",
    "cancel",
    "abandon",
})

AUTHORITY_ROLES: dict[SanctionAuthority, frozenset[str]] = {
    SanctionAuthority.SANCTION: frozenset({"MANAGEMENT", "ADMIN"}),
    SanctionAuthority.SECTION_CONTROL: frozenset({"CONTROL_OFFICER", "ADMIN"}),
    SanctionAuthority.TRACTION_POWER: frozenset({"TPC", "ADMIN"}),
    SanctionAuthority.STATION: frozenset({"STATION_MASTER", "ADMIN"}),
    SanctionAuthority.SNT: frozenset({"SIGNAL_TELECOM", "ADMIN"}),
    SanctionAuthority.ENGINEERING_SSE: frozenset({"ENGINEERING", "ADMIN"}),
}

ROLE_AUTHORITIES: dict[str, SanctionAuthority] = {
    "MANAGEMENT": SanctionAuthority.SANCTION,
    "CONTROL_OFFICER": SanctionAuthority.SECTION_CONTROL,
    "TPC": SanctionAuthority.TRACTION_POWER,
    "STATION_MASTER": SanctionAuthority.STATION,
    "SIGNAL_TELECOM": SanctionAuthority.SNT,
    "ENGINEERING": SanctionAuthority.ENGINEERING_SSE,
}


def parse_datetime(val: str | datetime | None) -> datetime:
    """Parse ISO timestamp or return UTC now if missing."""
    if not val:
        return datetime.now(timezone.utc)
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(val)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def derive_required_authorities(
    plan: Plan,
    tasks: dict[str, MaintenanceTask] | None = None,
) -> tuple[list[SanctionAuthority], list[str]]:
    """Derive required sanction authorities from plan blocks and tasks.

    Rules:
    - SECTION_CONTROL: always required.
    - SANCTION (Sr.DOM): MEGA / INTEGRATED or duration > 4h (240 min) or multi-department (HC-016).
    - TRACTION_POWER (TPC): POWER / INTEGRATED or requiresPTW (HC-003/HC-004).
    - SNT & STATION: DISCONNECTION or requiresT351 (HC-005).
    - SNT: requiresCorrespondenceTest (HC-006).

    Must tolerate task IDs absent from state.tasks.
    """
    authorities: set[SanctionAuthority] = {SanctionAuthority.SECTION_CONTROL}
    citations: set[str] = set()

    all_departments: set[str] = set()
    has_mega_or_integrated = False
    has_power = False
    has_disconnection = False
    max_block_duration = 0

    for block in plan.blocks:
        duration = block.end - block.start
        if duration > max_block_duration:
            max_block_duration = duration
        if block.departments:
            all_departments.update(d.value if hasattr(d, "value") else str(d) for d in block.departments)
        if block.blockType in {BlockType.MEGA, BlockType.INTEGRATED}:
            has_mega_or_integrated = True
        if block.blockType in {BlockType.POWER, BlockType.INTEGRATED}:
            has_power = True
        if block.blockType == BlockType.DISCONNECTION:
            has_disconnection = True

    # Inspect tasks if available
    needs_ptw = False
    needs_t351 = False
    needs_corr_test = False

    if tasks:
        for block in plan.blocks:
            for tid in block.taskIds:
                t = tasks.get(tid)
                if t is not None:
                    if getattr(t, "requiresPTW", False):
                        needs_ptw = True
                    if getattr(t, "requiresT351", False):
                        needs_t351 = True
                    if getattr(t, "requiresCorrespondenceTest", False):
                        needs_corr_test = True
                    if getattr(t, "department", None):
                        dept_val = t.department.value if hasattr(t.department, "value") else str(t.department)
                        all_departments.add(dept_val)

    if has_mega_or_integrated or max_block_duration > 240 or len(all_departments) > 1:
        authorities.add(SanctionAuthority.SANCTION)
        citations.add("HC-016")

    if has_power or needs_ptw:
        authorities.add(SanctionAuthority.TRACTION_POWER)
        citations.update({"HC-003", "HC-004"})

    if has_disconnection or needs_t351:
        authorities.add(SanctionAuthority.SNT)
        authorities.add(SanctionAuthority.STATION)
        citations.add("HC-005")

    if needs_corr_test:
        authorities.add(SanctionAuthority.SNT)
        citations.add("HC-006")

    # Canonical order for deterministic presentation
    canonical_order = [
        SanctionAuthority.SANCTION,
        SanctionAuthority.SECTION_CONTROL,
        SanctionAuthority.TRACTION_POWER,
        SanctionAuthority.STATION,
        SanctionAuthority.SNT,
        SanctionAuthority.ENGINEERING_SSE,
    ]
    result = [a for a in canonical_order if a in authorities]
    return result, sorted(citations)


@dataclass(frozen=True)
class TransitionDef:
    from_state: PossessionState
    action: str
    to_state: PossessionState
    allowed_roles: frozenset[str]
    rule_citation: str
    description: str

    # Keep the table pleasant to consume from API/schema tooling.  The
    # implementation uses snake_case internally, while the public contract
    # describes these columns as fromState/toState/allowedRoles.
    @property
    def fromState(self) -> PossessionState:
        return self.from_state

    @property
    def toState(self) -> PossessionState:
        return self.to_state

    @property
    def allowedRoles(self) -> frozenset[str]:
        return self.allowed_roles

    @property
    def ruleCitation(self) -> str:
        return self.rule_citation


def _check_no_conflict(possession: Possession, state: Any) -> tuple[bool, str]:
    """Precondition: no other possession is live/overrunning on the same section+track (HC-014)."""
    if not hasattr(state, "possessions"):
        return True, ""
    for pid, other in state.possessions.items():
        if pid != possession.possessionId:
            if other.sectionId == possession.sectionId and other.track == possession.track:
                # A section remains occupied from clearance through the full
                # handback/normalisation sequence.  Treating only LIVE as
                # occupied allowed a second possession to be granted while
                # isolation, protection, testing, or fitness certification
                # was still in progress.
                if other.state in {
                    PossessionState.CLEARANCE_GRANTED,
                    PossessionState.ISOLATION_IN_PROGRESS,
                    PossessionState.PROTECTED,
                    PossessionState.LIVE,
                    PossessionState.OVERRUNNING,
                    PossessionState.TESTING,
                    PossessionState.HANDBACK_REQUESTED,
                    PossessionState.FIT_CERTIFIED,
                }:
                    return False, f"Conflicting possession {pid} is currently {other.state} on section {possession.sectionId} track {possession.track} (HC-014)"
    return True, ""


# Table of all 28 statutory possession transitions
TRANSITIONS: list[TransitionDef] = [
    # Stage 5: Real-time clearance
    TransitionDef(
        PossessionState.SANCTIONED, "request-clearance", PossessionState.CLEARANCE_REQUESTED,
        frozenset({"FIELD_SUPERVISOR", "ENGINEERING", "SIGNAL_TELECOM", "TRACTION", "ADMIN"}),
        "G&SR 4.09", "Supervisor requests Section Controller to clear track"
    ),
    TransitionDef(
        PossessionState.SANCTIONED, "cancel", PossessionState.CANCELLED,
        frozenset({"CONTROL_OFFICER", "MANAGEMENT", "ADMIN"}),
        "G&SR 4.12", "Control cancels sanctioned possession before clearance"
    ),
    TransitionDef(
        PossessionState.CLEARANCE_REQUESTED, "grant-clearance", PossessionState.CLEARANCE_GRANTED,
        frozenset({"CONTROL_OFFICER", "ADMIN"}),
        "HC-014", "Section Controller grants track clearance after verifying traffic block"
    ),
    TransitionDef(
        PossessionState.CLEARANCE_REQUESTED, "defer", PossessionState.DEFERRED,
        frozenset({"CONTROL_OFFICER", "ADMIN"}),
        "SO-005", "Section Controller defers block due to preceding traffic delay"
    ),
    TransitionDef(
        PossessionState.CLEARANCE_REQUESTED, "cancel", PossessionState.CANCELLED,
        frozenset({"CONTROL_OFFICER", "MANAGEMENT", "ADMIN"}),
        "G&SR 4.12", "Control cancels block request"
    ),
    TransitionDef(
        PossessionState.DEFERRED, "request-clearance", PossessionState.CLEARANCE_REQUESTED,
        frozenset({"FIELD_SUPERVISOR", "ENGINEERING", "SIGNAL_TELECOM", "TRACTION", "ADMIN"}),
        "G&SR 4.09", "Supervisor re-requests clearance after deferral window"
    ),
    TransitionDef(
        PossessionState.DEFERRED, "cancel", PossessionState.CANCELLED,
        frozenset({"CONTROL_OFFICER", "MANAGEMENT", "ADMIN"}),
        "G&SR 4.12", "Control cancels deferred block"
    ),

    # Stage 6: Isolation & Disconnection
    TransitionDef(
        PossessionState.CLEARANCE_GRANTED, "start-isolation", PossessionState.ISOLATION_IN_PROGRESS,
        frozenset({"FIELD_SUPERVISOR", "ENGINEERING", "SIGNAL_TELECOM", "TRACTION", "TPC", "STATION_MASTER", "ADMIN"}),
        "ACTM 20603 / SEM 11.4", "Begin OHE isolation / S&T disconnection procedures"
    ),
    TransitionDef(
        PossessionState.CLEARANCE_GRANTED, "plant-protection", PossessionState.PROTECTED,
        frozenset({"FIELD_SUPERVISOR", "ENGINEERING", "ADMIN"}),
        "IRPWM 806", "Plant banner flags and detonators (for blocks requiring neither PTW nor T/351)"
    ),
    TransitionDef(
        PossessionState.CLEARANCE_GRANTED, "cancel", PossessionState.CANCELLED,
        frozenset({"CONTROL_OFFICER", "MANAGEMENT", "ADMIN"}),
        "G&SR 4.12", "Cancel granted block before isolation"
    ),
    TransitionDef(
        PossessionState.ISOLATION_IN_PROGRESS, "issue-t351", PossessionState.ISOLATION_IN_PROGRESS,
        frozenset({"SIGNAL_TELECOM", "ADMIN"}),
        "SEM 11.4 / HC-005", "Issue Form T/351 S&T Disconnection memo"
    ),
    TransitionDef(
        PossessionState.ISOLATION_IN_PROGRESS, "endorse-t351", PossessionState.ISOLATION_IN_PROGRESS,
        frozenset({"STATION_MASTER", "ADMIN"}),
        "SEM 11.4 / HC-005", "Station Master acknowledges & endorses Form T/351"
    ),
    TransitionDef(
        PossessionState.ISOLATION_IN_PROGRESS, "confirm-earthing", PossessionState.ISOLATION_IN_PROGRESS,
        frozenset({"TRACTION", "TPC", "FIELD_SUPERVISOR", "ADMIN"}),
        "ACTM 20603 / HC-003", "Field gang confirms OHE discharge rods planted and earthed"
    ),
    TransitionDef(
        PossessionState.ISOLATION_IN_PROGRESS, "issue-ptw", PossessionState.ISOLATION_IN_PROGRESS,
        frozenset({"TPC", "ADMIN"}),
        "ACTM 20603 / HC-003", "TPC issues Permit to Work after earthing confirmation"
    ),
    TransitionDef(
        PossessionState.ISOLATION_IN_PROGRESS, "plant-protection", PossessionState.PROTECTED,
        frozenset({"FIELD_SUPERVISOR", "ENGINEERING", "ADMIN"}),
        "IRPWM 806", "Plant banner flags and detonators once isolation complete"
    ),

    # Stage 7: Execution
    TransitionDef(
        PossessionState.PROTECTED, "start-work", PossessionState.LIVE,
        frozenset({"FIELD_SUPERVISOR", "ENGINEERING", "SIGNAL_TELECOM", "TRACTION", "ADMIN"}),
        "HC-003 / HC-005", "Field teams enter track and begin work after lead-in times"
    ),
    TransitionDef(
        PossessionState.LIVE, "declare-overrun", PossessionState.OVERRUNNING,
        frozenset({"CONTROL_OFFICER", "FIELD_SUPERVISOR", "ADMIN"}),
        "SO-005", "Declare block overrun as work extends past planned end time"
    ),
    TransitionDef(
        PossessionState.LIVE, "abandon", PossessionState.ABANDONED,
        frozenset({"CONTROL_OFFICER", "MANAGEMENT", "ADMIN"}),
        "G&SR 4.15", "Abandon block execution due to machine failure / emergency"
    ),
    TransitionDef(
        PossessionState.OVERRUNNING, "abandon", PossessionState.ABANDONED,
        frozenset({"CONTROL_OFFICER", "MANAGEMENT", "ADMIN"}),
        "G&SR 4.15", "Abandon overrunning block execution"
    ),

    # Stage 8: Testing & Handback (from LIVE or OVERRUNNING)
    TransitionDef(
        PossessionState.LIVE, "start-testing", PossessionState.TESTING,
        frozenset({"SIGNAL_TELECOM", "FIELD_SUPERVISOR", "ENGINEERING", "ADMIN"}),
        "HC-006", "Commence S&T correspondence testing (post-Balasore directive)"
    ),
    TransitionDef(
        PossessionState.OVERRUNNING, "start-testing", PossessionState.TESTING,
        frozenset({"SIGNAL_TELECOM", "FIELD_SUPERVISOR", "ENGINEERING", "ADMIN"}),
        "HC-006", "Commence S&T correspondence testing during overrun"
    ),
    TransitionDef(
        PossessionState.TESTING, "record-correspondence-test", PossessionState.TESTING,
        frozenset({"SIGNAL_TELECOM", "ADMIN"}),
        "HC-006", "Record completed correspondence test result (>= 30 min duration)"
    ),
    TransitionDef(
        PossessionState.TESTING, "request-handback", PossessionState.HANDBACK_REQUESTED,
        frozenset({"FIELD_SUPERVISOR", "ENGINEERING", "SIGNAL_TELECOM", "ADMIN"}),
        "HC-006 / HC-018", "Request handback following successful correspondence test"
    ),
    TransitionDef(
        PossessionState.LIVE, "request-handback", PossessionState.HANDBACK_REQUESTED,
        frozenset({"FIELD_SUPERVISOR", "ENGINEERING", "ADMIN"}),
        "HC-018", "Request handback (when correspondence test is not required)"
    ),
    TransitionDef(
        PossessionState.OVERRUNNING, "request-handback", PossessionState.HANDBACK_REQUESTED,
        frozenset({"FIELD_SUPERVISOR", "ENGINEERING", "ADMIN"}),
        "HC-018", "Request handback from overrunning state"
    ),
    TransitionDef(
        PossessionState.HANDBACK_REQUESTED, "remove-discharge-rods", PossessionState.HANDBACK_REQUESTED,
        frozenset({"TRACTION", "FIELD_SUPERVISOR", "ADMIN"}),
        "ACTM 20610 / HC-004", "Remove OHE discharge rods"
    ),
    TransitionDef(
        PossessionState.HANDBACK_REQUESTED, "cancel-ptw", PossessionState.HANDBACK_REQUESTED,
        frozenset({"TPC", "ADMIN"}),
        "ACTM 20610 / HC-004", "TPC cancels Permit to Work after rods are removed"
    ),
    TransitionDef(
        PossessionState.HANDBACK_REQUESTED, "reconnect-t351", PossessionState.HANDBACK_REQUESTED,
        frozenset({"SIGNAL_TELECOM", "ADMIN"}),
        "SEM 11.4 / HC-005", "S&T reconnects and closes the Form T/351 disconnection"
    ),
    TransitionDef(
        PossessionState.HANDBACK_REQUESTED, "re-energise", PossessionState.HANDBACK_REQUESTED,
        frozenset({"TPC", "ADMIN"}),
        "ACTM 20610", "TPC re-energises traction OHE section"
    ),
    TransitionDef(
        PossessionState.HANDBACK_REQUESTED, "certify-fitness", PossessionState.FIT_CERTIFIED,
        frozenset({"ENGINEERING", "ADMIN"}),
        "IRPWM 308 / HC-018", "SSE (Permanent Way) certifies track fitness with TSR speed ladder"
    ),

    # Stage 9: Normalisation & Closure
    TransitionDef(
        PossessionState.FIT_CERTIFIED, "station-close", PossessionState.FIT_CERTIFIED,
        frozenset({"STATION_MASTER", "ADMIN"}),
        "SEM 11.4 / G&SR 4.10", "Station Master closes block instrument on station panel"
    ),
    TransitionDef(
        PossessionState.FIT_CERTIFIED, "close", PossessionState.CLEARED,
        frozenset({"CONTROL_OFFICER", "ADMIN"}),
        "G&SR 4.11", "Section Controller closes possession and normalises section"
    ),
]

# O(1) lookup for the API and a stable table-shaped export for integrations
# that render the machine without copying its rules into a client.
TRANSITION_TABLE: dict[tuple[PossessionState, str], TransitionDef] = {
    (transition.from_state, transition.action): transition
    for transition in TRANSITIONS
}


def check_precondition(
    possession: Possession,
    action: str,
    body: dict[str, Any],
    user_role: str,
    state: Any = None,
) -> tuple[bool, str]:
    """Check action-specific statutory preconditions."""
    user_role_norm = normalize_role(user_role)

    if action == "grant-clearance":
        now_dt = datetime.now(timezone.utc)
        planned_start_value = possession.plannedStartUtc
        planned_end_value = possession.plannedEndUtc
        if planned_start_value and planned_end_value:
            planned_start = parse_datetime(planned_start_value)
            planned_end = parse_datetime(planned_end_value)
            # Day-of is evaluated in the planned window's timezone, not by
            # comparing a local wall clock to UTC's date boundary.
            if now_dt.astimezone(planned_start.tzinfo).date() != planned_start.date():
                return False, (
                    "CLEARANCE_NOT_DAY_OF: clearance may only be granted on "
                    f"the planned operating day ({planned_start.date().isoformat()})"
                )
            if now_dt < planned_start:
                # Clearance can be granted before the exact start minute on
                # the operating day, but never after a future deferral window.
                pass
            if now_dt > planned_end:
                return False, "CLEARANCE_WINDOW_EXPIRED: planned block window has ended"
        if possession.deferredUntilUtc:
            deferred_until = parse_datetime(possession.deferredUntilUtc)
            if now_dt < deferred_until:
                return False, (
                    "CLEARANCE_DEFERRED: clearance is deferred until "
                    f"{possession.deferredUntilUtc}"
                )
        ok, msg = _check_no_conflict(possession, state)
        if not ok:
            return False, msg

    elif action == "defer":
        if possession.deferralCount >= 3:
            return False, "Maximum 3 deferrals allowed before mandatory rescheduling or cancellation"

    elif action == "endorse-t351":
        if possession.formT351 is None or possession.formT351.status not in {"ISSUED", "ENDORSED"}:
            return False, "Form T/351 must be issued before endorsement"

    elif action == "reconnect-t351":
        if possession.formT351 is None or possession.formT351.status != "ENDORSED":
            return False, "Form T/351 must be endorsed before S&T reconnection"

    elif action == "issue-ptw":
        if user_role_norm not in {"TPC", "ADMIN"}:
            return False, "Only TPC may issue Permit to Work (HC-003)"
        if not (possession.permitToWork and possession.permitToWork.earthingConfirmed):
            return False, "OHE earthing must be confirmed by field team before PTW issuance (HC-003)"
        if possession.permitToWork and possession.permitToWork.status == "CANCELLED":
            return False, "A cancelled Permit to Work cannot be issued again for this possession"

    elif action == "plant-protection":
        if possession.requiresT351:
            if not (possession.formT351 and possession.formT351.status == "ENDORSED"):
                return False, "Form T/351 must be endorsed by Station Master before planting protection (HC-005)"
        if possession.requiresPTW:
            if not (possession.permitToWork and possession.permitToWork.status == "ISSUED"):
                return False, "Permit to Work must be issued by TPC before planting protection (HC-003)"
        detonator_count = body.get("detonatorCount")
        if detonator_count is not None:
            try:
                if int(detonator_count) < 1:
                    return False, "At least one detonator is required for planted protection (IRPWM 806)"
            except (TypeError, ValueError):
                return False, "detonatorCount must be a positive integer"

    elif action == "start-work":
        # A field clock is authoritative for an offline act when supplied.  A
        # request made without one is checked against the server clock.  This
        # prevents an online client from bypassing the statutory lead-in by
        # omitting clientEventAtUtc.
        event_dt = parse_datetime(body.get("clientEventAtUtc")) if body.get("clientEventAtUtc") else datetime.now(timezone.utc)
        lead_requirements: list[tuple[str, str, int]] = []
        missing_artifacts: list[str] = []
        if possession.requiresPTW:
            issued = possession.permitToWork.issuedAtUtc if possession.permitToWork else None
            if issued:
                lead_requirements.append(("Permit to Work", issued, PTW_LEAD_IN))
            else:
                missing_artifacts.append("Permit to Work")
        if possession.requiresT351:
            issued = possession.formT351.issuedAtUtc if possession.formT351 else None
            if issued:
                lead_requirements.append(("Form T/351", issued, T351_LEAD_IN))
            else:
                missing_artifacts.append("Form T/351")

        # A legacy possession is explicitly identifiable by the pre-authority
        # shape (no creation stamp and no transition history).  Do not extend
        # this grandfathering to a newly-created record with missing evidence.
        if missing_artifacts and not (not possession.createdAtUtc and not possession.transitions):
            return False, (
                "Statutory lead-in cannot be established; missing issuance "
                + ", ".join(missing_artifacts)
            )
        if missing_artifacts:
            return True, ""

        for artefact, issued_at, minutes in lead_requirements:
            issued_dt = parse_datetime(issued_at)
            if (event_dt - issued_dt).total_seconds() < minutes * 60:
                return False, f"{artefact} lead-in of {minutes} minutes has not elapsed"

    elif action == "declare-overrun":
        now_dt = datetime.now(timezone.utc)
        planned_end = parse_datetime(possession.plannedEndUtc)
        if now_dt <= planned_end:
            return False, f"Current time is within planned block window (ends {possession.plannedEndUtc})"

    elif action == "record-correspondence-test":
        duration = body.get("durationMinutes", 0)
        if duration < CORRESPONDENCE_TEST:
            return False, f"TEST_TOO_SHORT: Correspondence test must be >= {CORRESPONDENCE_TEST} minutes (got {duration})"

    elif action == "request-handback":
        if possession.requiresCorrespondenceTest and not (
            possession.correspondenceTest and possession.correspondenceTest.passed
        ):
            return False, "A passed correspondence test is required before handback (HC-006)"

    elif action == "remove-discharge-rods":
        if possession.requiresPTW and not (
            possession.permitToWork and possession.permitToWork.status == "ISSUED"
        ):
            return False, "Discharge rods can only be removed from an issued Permit to Work"

    elif action == "cancel-ptw":
        if user_role_norm not in {"TPC", "ADMIN"}:
            return False, "Only TPC may cancel Permit to Work (HC-004)"
        if not (possession.permitToWork and possession.permitToWork.status == "ISSUED"):
            return False, "Permit to Work must be issued before it can be cancelled (HC-004)"
        if not possession.permitToWork.dischargeRodsRemoved:
            return False, "Discharge rods must be removed before PTW cancellation (HC-004 ACTM 20610)"

    elif action == "re-energise":
        if possession.requiresPTW and not (
            possession.permitToWork and possession.permitToWork.status == "CANCELLED"
        ):
            return False, "Permit to Work must be cancelled before re-energising the OHE (HC-004)"

    elif action == "certify-fitness":
        if user_role_norm not in {"ENGINEERING", "ADMIN"}:
            return False, "Only ENGINEERING (SSE P-Way) may certify track fitness (HC-018)"
        if possession.requiresPTW:
            if not (possession.permitToWork and possession.permitToWork.status == "CANCELLED"):
                return False, "Permit to Work must be cancelled by TPC before fitness certification (HC-004)"
        if possession.requiresCorrespondenceTest:
            if not (possession.correspondenceTest and possession.correspondenceTest.passed):
                return False, "Correspondence test must be recorded and passed before fitness certification (HC-006)"
        if possession.requiresT351 and not (
            possession.formT351 and possession.formT351.status in {"RECONNECTED", "CLOSED"}
        ):
            return False, "Form T/351 must be reconnected and reconciled before fitness certification (HC-005)"
        if not (
            possession.protectionRecord
            and possession.protectionRecord.bannerFlagsPlaced
            and possession.protectionRecord.handSignalPosted
            and possession.protectionRecord.detonatorCount > 0
        ):
            return False, "Protection record is incomplete; flags, hand signal and detonators are required (IRPWM 806)"
        tsr = body.get("tsrSpeedKmph")
        if tsr is not None and tsr not in SR_DAY_SPEEDS_KMPH:
            return False, f"TSR speed must be one of {SR_DAY_SPEEDS_KMPH} km/h (HC-018)"

    elif action == "close":
        if not possession.stationClosed:
            return False, "Station Master must close block instrument (station-close) before Section Controller closes possession"
        if possession.requiresPTW and not (
            possession.permitToWork and possession.permitToWork.reEnergised
        ):
            return False, "OHE must be re-energised by TPC before final possession normalisation (HC-004)"

    return True, ""


def action_already_applied(possession: Possession, action: str) -> bool:
    """Return whether a same-state action has already materialised its artefact.

    Several physical acts intentionally leave the possession in the same
    state (earthing, issuing a PTW, and recording a correspondence test).  A
    mobile retry must not mint a second form or append a second audit record.
    State equality alone cannot distinguish the first call from a replay, so
    the artefact is the idempotency marker for these actions.
    """
    if action == "issue-t351":
        return possession.formT351 is not None
    if action == "endorse-t351":
        return bool(possession.formT351 and possession.formT351.status == "ENDORSED")
    if action == "confirm-earthing":
        return bool(possession.permitToWork and possession.permitToWork.earthingConfirmed)
    if action == "issue-ptw":
        return bool(possession.permitToWork and possession.permitToWork.status == "ISSUED")
    if action == "record-correspondence-test":
        return possession.correspondenceTest is not None
    if action == "remove-discharge-rods":
        return bool(possession.permitToWork and possession.permitToWork.dischargeRodsRemoved)
    if action == "cancel-ptw":
        return bool(possession.permitToWork and possession.permitToWork.status == "CANCELLED")
    if action == "reconnect-t351":
        return bool(possession.formT351 and possession.formT351.status in {"RECONNECTED", "CLOSED"})
    if action == "re-energise":
        return bool(possession.permitToWork and possession.permitToWork.reEnergised)
    if action == "station-close":
        return possession.stationClosed
    return False


def compute_handback_checklist(possession: Possession) -> list[dict[str, Any]]:
    """Compute the statutory handback checklist with fulfillment status."""
    items: list[dict[str, Any]] = []

    # 1. P-Way track clearance
    items.append({
        "item": "Permanent Way clear and safe for train movement",
        "satisfied": possession.state in {
            PossessionState.TESTING,
            PossessionState.HANDBACK_REQUESTED,
            PossessionState.FIT_CERTIFIED,
            PossessionState.CLEARED,
        },
        "rule": "IRPWM 806 / HC-018",
    })

    # 2. S&T correspondence test
    if possession.requiresCorrespondenceTest:
        items.append({
            "item": "S&T Correspondence Test completed (>= 30 min)",
            "satisfied": bool(possession.correspondenceTest and possession.correspondenceTest.passed),
            "rule": "HC-006",
        })

    # 3. PTW discharge rods and cancellation
    if possession.requiresPTW:
        items.append({
            "item": "OHE discharge rods removed",
            "satisfied": bool(possession.permitToWork and possession.permitToWork.dischargeRodsRemoved),
            "rule": "ACTM 20610 / HC-004",
        })
        items.append({
            "item": "Permit to Work cancelled by TPC",
            "satisfied": bool(possession.permitToWork and possession.permitToWork.status == "CANCELLED"),
            "rule": "ACTM 20610 / HC-004",
        })

    # 4. S&T Form T/351 reconnection
    if possession.requiresT351:
        items.append({
            "item": "S&T Form T/351 reconnection completed",
            "satisfied": bool(possession.formT351 and possession.formT351.status in {"RECONNECTED", "CLOSED"}),
            "rule": "SEM 11.4 / HC-005",
        })

    # 5. Fitness Certificate
    items.append({
        "item": "Fitness certificate issued with TSR ladder (20/45/75 km/h)",
        "satisfied": bool(possession.fitnessCertificate is not None),
        "rule": "IRPWM 308 / HC-018",
    })

    # 6. Station Master closure
    items.append({
        "item": "Station Master block instrument closure",
        "satisfied": bool(possession.stationClosed),
        "rule": "SEM 11.4 / G&SR 4.10",
    })

    return items


def compute_overrun_minutes(possession: Possession, now: datetime | None = None) -> int:
    """Compute live or final overrun minutes against planned end time."""
    if possession.state in {
        PossessionState.SANCTIONED,
        PossessionState.CLEARANCE_REQUESTED,
        PossessionState.DEFERRED,
        PossessionState.CANCELLED,
        PossessionState.ABANDONED,
    }:
        return 0

    planned_end = parse_datetime(possession.plannedEndUtc)

    if possession.state == PossessionState.CLEARED:
        if possession.actualEndUtc:
            actual_end = parse_datetime(possession.actualEndUtc)
            diff = int((actual_end - planned_end).total_seconds() / 60)
            return max(0, diff)
        return 0

    # A block that has not entered execution cannot accrue a block burst just
    # because its charted window has elapsed.  In particular, a late start is
    # recorded on actualStartUtc but is not debited as tail overrun.
    if possession.actualStartUtc is None and possession.state not in {
        PossessionState.OVERRUNNING,
        PossessionState.TESTING,
        PossessionState.HANDBACK_REQUESTED,
        PossessionState.FIT_CERTIFIED,
    }:
        return 0

    now_dt = now or datetime.now(timezone.utc)
    diff = int((now_dt - planned_end).total_seconds() / 60)
    return max(0, diff)


def get_allowed_actions_for_role(
    possession: Possession,
    role: str,
    state: Any = None,
) -> list[str]:
    """Return all actions valid for current possession state and caller role."""
    norm_role = normalize_role(role)
    allowed: list[str] = []

    for t in TRANSITIONS:
        if t.from_state == possession.state:
            if norm_role == "ADMIN" or norm_role in t.allowed_roles:
                # Test gates that are independent of the request payload.  A
                # preview should not hide an action merely because its body
                # will be supplied when the user presses the button (notably
                # the 30-minute correspondence-test duration).
                # Timing and day-of gates must remain live in allowedActions;
                # callers should not see a button that will be rejected now.
                preview_body: dict[str, Any] = {}
                if t.action == "record-correspondence-test":
                    preview_body["durationMinutes"] = CORRESPONDENCE_TEST
                ok, _ = check_precondition(possession, t.action, preview_body, norm_role, state)
                if ok:
                    allowed.append(t.action)

    return sorted(set(allowed))


def get_blocked_actions_for_role(
    possession: Possession,
    role: str,
    state: Any = None,
) -> list[dict[str, str]]:
    """Actions this role owns at this state but that a precondition refuses.

    allowedActions deliberately hides these so nobody presses a button that
    will 409. Without the reason the board just says "no action available",
    which reads as a broken screen when the truth is a lead-in timer or a
    day-of gate.
    """
    norm_role = normalize_role(role)
    blocked: dict[str, str] = {}

    for t in TRANSITIONS:
        if t.from_state != possession.state:
            continue
        if norm_role != "ADMIN" and norm_role not in t.allowed_roles:
            continue
        preview_body: dict[str, Any] = {}
        if t.action == "record-correspondence-test":
            preview_body["durationMinutes"] = CORRESPONDENCE_TEST
        ok, reason = check_precondition(possession, t.action, preview_body, norm_role, state)
        if not ok:
            blocked[t.action] = reason

    return [{"action": a, "reason": blocked[a]} for a in sorted(blocked)]


def build_possession_view(
    possession: Possession,
    role: str,
    state: Any = None,
) -> dict[str, Any]:
    """Construct PossessionView with computed keys."""
    data = possession.model_dump(by_alias=True, mode="json")
    data["overrunMinutesLive"] = compute_overrun_minutes(possession)
    data["handbackChecklist"] = compute_handback_checklist(possession)
    data["allowedActions"] = get_allowed_actions_for_role(possession, role, state)
    data["blockedActions"] = get_blocked_actions_for_role(possession, role, state)
    return data
