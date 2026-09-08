"""Task compatibility matrix -- Ground Reality Report section 9.1.

Co-location does NOT imply compatibility. This module is an explicit table, not a
distance test. Any pair that is not listed is INCOMPATIBLE: the conservative
default is deliberate, because an unlisted pair means nobody has verified it.
"""

from railos_model import Compatibility, MaintenanceTask, TaskType

C = Compatibility

#: Verified pairwise verdicts. Key is a frozenset of two task types.
#: value = (verdict, condition text)
_MATRIX: dict[frozenset, tuple[Compatibility, str]] = {
    # Row 1: plain track tamping + track circuit bonds + tower wagon OHE inspection
    frozenset({TaskType.TAMPING, TaskType.TRACK_CIRCUIT_BOND}): (
        C.SEQUENTIALLY_COMPATIBLE,
        "S&T bonds checked after the tamper has passed",
    ),
    frozenset({TaskType.TAMPING, TaskType.OHE_INSPECTION}): (
        C.CONDITIONAL,
        "tower wagon must stay >200 m from the tamper (HC-008, IRTMM 3.2.1)",
    ),
    frozenset({TaskType.TRACK_CIRCUIT_BOND, TaskType.OHE_INSPECTION}): (
        C.COMPATIBLE,
        "independent work, no shared equipment",
    ),
    # Row 2: ballast cleaning is hostile to everything delicate
    frozenset({TaskType.DEEP_SCREENING, TaskType.POINT_MACHINE_MAINT}): (
        C.INCOMPATIBLE,
        "BCM vibration and ballast removal damage point machines and detection rods",
    ),
    frozenset({TaskType.DEEP_SCREENING, TaskType.CATENARY_REPLACEMENT}): (
        C.INCOMPATIBLE,
        "catenary replacement needs a tower wagon on the same track the BCM occupies",
    ),
    frozenset({TaskType.DEEP_SCREENING, TaskType.TRACK_CIRCUIT_BOND}): (
        C.INCOMPATIBLE,
        "ballast bed is removed; bonds cannot be verified until screening completes",
    ),
    # Row 3: turnout renewal -- the three-department handshake
    frozenset({TaskType.TURNOUT_RENEWAL, TaskType.SNT_DISCONNECTION}): (
        C.SEQUENTIALLY_COMPATIBLE,
        "HC-007: S&T disconnects the point under T/351 before civil work starts",
    ),
    frozenset({TaskType.TURNOUT_RENEWAL, TaskType.TRD_ISOLATION}): (
        C.SEQUENTIALLY_COMPATIBLE,
        "HC-007: OHE isolated under PTW before civil work starts",
    ),
    frozenset({TaskType.TURNOUT_RENEWAL, TaskType.OHE_SLEWING}): (
        C.SEQUENTIALLY_COMPATIBLE,
        "HC-007: TRD checks OHE alignment after the turnout is replaced",
    ),
    frozenset({TaskType.TURNOUT_RENEWAL, TaskType.SNT_RECONNECTION}): (
        C.SEQUENTIALLY_COMPATIBLE,
        "HC-007: S&T reconnects and performs correspondence testing last",
    ),
    frozenset({TaskType.SNT_DISCONNECTION, TaskType.TRD_ISOLATION}): (
        C.SEQUENTIALLY_COMPATIBLE,
        "HC-007 step 1 then step 2",
    ),
    frozenset({TaskType.SNT_DISCONNECTION, TaskType.OHE_SLEWING}): (
        C.SEQUENTIALLY_COMPATIBLE,
        "same turnout possession",
    ),
    frozenset({TaskType.SNT_DISCONNECTION, TaskType.SNT_RECONNECTION}): (
        C.SEQUENTIALLY_COMPATIBLE,
        "disconnection precedes reconnection on the same gear",
    ),
    frozenset({TaskType.TRD_ISOLATION, TaskType.OHE_SLEWING}): (
        C.SEQUENTIALLY_COMPATIBLE,
        "isolate, then align",
    ),
    frozenset({TaskType.TRD_ISOLATION, TaskType.SNT_RECONNECTION}): (
        C.SEQUENTIALLY_COMPATIBLE,
        "same turnout possession",
    ),
    frozenset({TaskType.OHE_SLEWING, TaskType.SNT_RECONNECTION}): (
        C.SEQUENTIALLY_COMPATIBLE,
        "HC-007 step 4 then step 5",
    ),
    # Row 4: manual renewals piggyback well
    frozenset({TaskType.SLEEPER_RENEWAL, TaskType.GJ_REPLACEMENT}): (
        C.COMPATIBLE,
        "track circuit disconnected and re-bonded around the joint",
    ),
    frozenset({TaskType.SLEEPER_RENEWAL, TaskType.OHE_BRACKET_ADJUST}): (
        C.CONDITIONAL,
        "power block required if work comes within 2 m of live OHE (ACTM 20.3)",
    ),
    frozenset({TaskType.RAIL_REPLACEMENT, TaskType.GJ_REPLACEMENT}): (
        C.COMPATIBLE,
        "same rail, one possession",
    ),
    frozenset({TaskType.RAIL_REPLACEMENT, TaskType.OHE_BRACKET_ADJUST}): (
        C.CONDITIONAL,
        "power block required if work comes within 2 m of live OHE (ACTM 20.3)",
    ),
    # Row 5: de-stressing
    frozenset({TaskType.DESTRESSING, TaskType.AXLE_COUNTER_CALIB}): (
        C.CONDITIONAL,
        "axle counters unbolted before de-stressing, recalibrated after",
    ),
    frozenset({TaskType.DESTRESSING, TaskType.OHE_BRACKET_ADJUST}): (
        C.CONDITIONAL,
        "rails lifted on rollers; electrical clearance to live OHE must be maintained",
    ),
    # Inspections coexist with most things
    frozenset({TaskType.USFD_INSPECTION, TaskType.OHE_INSPECTION}): (
        C.COMPATIBLE,
        "both non-intrusive",
    ),
}


def pair(a: MaintenanceTask, b: MaintenanceTask) -> tuple[Compatibility, str]:
    """Verdict for two tasks sharing a block. Unknown pairs are INCOMPATIBLE."""
    if a.taskId == b.taskId:
        return C.COMPATIBLE, "same task"

    # Row 6: deep screening under live OHE is prohibited outright (ACTM 20.3).
    for x in (a, b):
        if x.taskType is TaskType.DEEP_SCREENING and not x.requiresPTW:
            return (
                C.STRICTLY_PROHIBITED,
                f"{x.taskId}: deep screening under live OHE violates the 2 m clearance "
                "rule (ACTM 20.3); a power block is non-negotiable",
            )

    if a.taskType is b.taskType:
        # Two of the same trade in one block is normal, but not two machines of the
        # same type in one section -- HC-008 spacing decides that in the optimizer.
        return C.COMPATIBLE, "same work type"

    verdict = _MATRIX.get(frozenset({a.taskType, b.taskType}))
    if verdict is None:
        return (
            C.INCOMPATIBLE,
            f"no verified compatibility for {a.taskType.value} + {b.taskType.value}; "
            "defaulting to incompatible",
        )
    return verdict


def bundleable(a: MaintenanceTask, b: MaintenanceTask) -> bool:
    verdict, _ = pair(a, b)
    return verdict in (C.COMPATIBLE, C.SEQUENTIALLY_COMPATIBLE, C.CONDITIONAL)


def prohibited(a: MaintenanceTask, b: MaintenanceTask) -> bool:
    verdict, _ = pair(a, b)
    return verdict is C.STRICTLY_PROHIBITED


def unary_violations(task: MaintenanceTask) -> list[str]:
    """Rules a task can break on its own, with no second task involved."""
    out = []
    if task.taskType is TaskType.DEEP_SCREENING and not task.requiresPTW:
        out.append(
            f"{task.taskId}: deep screening requires a power block (ACTM 20.3, 2 m clearance)"
        )
    if task.taskType in (TaskType.SNT_DISCONNECTION, TaskType.SNT_RECONNECTION) and not task.requiresT351:
        out.append(f"{task.taskId}: S&T disconnection work requires Form T/351 (HC-005, SEM 11.4)")
    return out
