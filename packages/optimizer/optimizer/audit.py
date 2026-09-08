"""Independent hard-constraint audit of a produced plan.

This deliberately does NOT reuse the model. It re-derives every hard constraint from
the plan and the world, so a bug that quietly relaxes a safety rule inside the CP-SAT
formulation is caught here rather than shipped as a plausible-looking schedule.

A plan that fails the audit is not a plan.
"""

from dataclasses import dataclass

from railos_model import Plan, ScenarioWorld

from .config import (
    CAUTION_ORDER_SPEED_KMPH,
    CORRESPONDENCE_TEST,
    MACHINE_TRANSIT_PER_SECTION,
    MAX_CONCURRENT_SR_KM,
    SR_DAY_SPEEDS_KMPH,
    DEFAULT_HEADWAY,
    GANG_TRANSIT_PER_SECTION,
    IMR_DEADLINE_MINUTES,
    MACHINE_SPACING_M,
    MAX_BLOCK_MINUTES,
    PTW_HANDBACK,
    PTW_LEAD_IN,
    SUNRISE_MINUTE,
    SUNSET_MINUTE,
    T351_LEAD_IN,
)
from .model import required_span
from .traingraph import recompute, speed_restrictions, worked_km


@dataclass
class Violation:
    code: str
    detail: str

    def __str__(self) -> str:
        return f"{self.code}: {self.detail}"


def audit(world: ScenarioWorld, plan: Plan, headway: int = DEFAULT_HEADWAY) -> list[Violation]:
    out: list[Violation] = []
    at = {a.taskId: a for a in plan.assignments}
    task_of = {t.taskId: t for t in world.tasks}
    block_of = {a.taskId: next(b for b in plan.blocks if b.blockId == a.blockId) for a in plan.assignments}

    # HC-001 no maintenance across a charted train path, headway included.
    for a in plan.assignments:
        task = task_of[a.taskId]
        for tr in world.trains:
            if tr.sectionId != task.sectionId or tr.track != task.track:
                continue
            if a.start < tr.exit + headway and tr.entry - headway < a.end:
                out.append(
                    Violation(
                        "HC-001",
                        f"{a.taskId} [{a.start},{a.end}] overlaps train {tr.trainId} "
                        f"[{tr.entry},{tr.exit}] +/- {headway} min on {task.sectionId}",
                    )
                )

    # HC-002 statutory minimum machine block duration.
    from railos_model import MIN_MACHINE_BLOCK_MINUTES

    for a in plan.assignments:
        task = task_of[a.taskId]
        floor = MIN_MACHINE_BLOCK_MINUTES[task.machineType]
        if a.end - a.start < floor:
            out.append(
                Violation(
                    "HC-002",
                    f"{a.taskId} runs {a.end - a.start} min; {task.machineType.value} "
                    f"requires at least {floor}",
                )
            )

    # HC-003 / HC-004 power block buffers inside the possession.
    for a in plan.assignments:
        task = task_of[a.taskId]
        block = block_of[a.taskId]
        if task.requiresPTW:
            if a.start - block.start < PTW_LEAD_IN:
                out.append(
                    Violation(
                        "HC-003",
                        f"{a.taskId} starts {a.start - block.start} min after block start; "
                        f"{PTW_LEAD_IN} min of switching and earthing are required",
                    )
                )
            if block.end - a.end < PTW_HANDBACK:
                out.append(
                    Violation(
                        "HC-004",
                        f"{a.taskId} leaves {block.end - a.end} min before block clearance; "
                        f"{PTW_HANDBACK} min of handback are required",
                    )
                )
        # HC-005 T/351 endorsement time.
        if task.requiresT351 and a.start - block.start < T351_LEAD_IN:
            out.append(
                Violation(
                    "HC-005",
                    f"{a.taskId} starts before the Form T/351 endorsement allowance "
                    f"({T351_LEAD_IN} min)",
                )
            )
        # HC-006 correspondence testing after point / detection work.
        if task.requiresCorrespondenceTest and block.end - a.end < CORRESPONDENCE_TEST:
            out.append(
                Violation(
                    "HC-006",
                    f"{a.taskId} leaves {block.end - a.end} min for correspondence testing; "
                    f"{CORRESPONDENCE_TEST} min are mandatory",
                )
            )

    # HC-007 declared dependencies.
    for dep in world.dependencies:
        a1, a2 = at.get(dep.predecessorTaskId), at.get(dep.successorTaskId)
        if a1 and a2 and a1.end + dep.lagMinutes > a2.start:
            out.append(
                Violation(
                    "HC-007",
                    f"{dep.predecessorTaskId} ends {a1.end} but {dep.successorTaskId} "
                    f"starts {a2.start} -- {dep.reason}",
                )
            )
        if bool(a1) != bool(a2):
            out.append(
                Violation(
                    "HC-007",
                    f"sequence broken: only one of {dep.predecessorTaskId} / "
                    f"{dep.successorTaskId} is scheduled",
                )
            )

    # HC-008 machine spacing, HC-009 machine occupancy.
    scheduled = [(task_of[a.taskId], a) for a in plan.assignments]
    for i in range(len(scheduled)):
        for j in range(i + 1, len(scheduled)):
            (ti, ai), (tj, aj) = scheduled[i], scheduled[j]
            overlap = ai.start < aj.end and aj.start < ai.end
            if not overlap:
                continue
            if (
                ti.machineType.value != "NONE"
                and tj.machineType.value != "NONE"
                and ti.sectionId == tj.sectionId
                and ti.track == tj.track
                and abs(ti.locationM - tj.locationM) < MACHINE_SPACING_M
            ):
                out.append(
                    Violation(
                        "HC-008",
                        f"{ti.taskId} and {tj.taskId} work {abs(ti.locationM - tj.locationM)} m "
                        f"apart; {MACHINE_SPACING_M} m minimum separation applies",
                    )
                )
            shared = set(ti.resourceIds) & set(tj.resourceIds)
            if shared:
                out.append(
                    Violation(
                        "HC-009",
                        f"{ti.taskId} and {tj.taskId} both hold {sorted(shared)} at the same time",
                    )
                )
            if ti.gangId and ti.gangId == tj.gangId:
                out.append(
                    Violation(
                        "HC-013",
                        f"gang {ti.gangId} is booked on {ti.taskId} and {tj.taskId} simultaneously",
                    )
                )
            if ti.requiresSntEscort and tj.requiresSntEscort:
                out.append(
                    Violation(
                        "HC-017",
                        f"{ti.taskId} and {tj.taskId} both need the S&T escort at the same time",
                    )
                )

    # HC-010 / HC-012 adjacent line: no maintenance on the parallel track while
    # infringing machine work or a tower wagon occupies this one.
    for i in range(len(scheduled)):
        for j in range(i + 1, len(scheduled)):
            (ti, ai), (tj, aj) = scheduled[i], scheduled[j]
            if ti.sectionId != tj.sectionId or ti.track == tj.track:
                continue
            if not (ai.start < aj.end and aj.start < ai.end):
                continue
            for a_task, b_task in ((ti, tj), (tj, ti)):
                wagon = a_task.machineType.value == "TOWER_WAGON"
                if a_task.infringesAdjacent or wagon:
                    out.append(
                        Violation(
                            "HC-012" if wagon else "HC-010",
                            f"{a_task.taskId} infringes the adjacent line while "
                            f"{b_task.taskId} works on it "
                            f"({CAUTION_ORDER_SPEED_KMPH} kmph caution order in force)",
                        )
                    )

    # HC-012 / HC-009 machine transit: a track machine cannot teleport between
    # sections between two jobs.
    section_order = {s.sectionId: i for c in world.corridors for i, s in enumerate(c.sections)}
    by_machine: dict[str, list] = {}
    for task, a in scheduled:
        for r in task.resourceIds:
            by_machine.setdefault(r, []).append((task, a))
    for machine, items in by_machine.items():
        items.sort(key=lambda x: x[1].start)
        for (t1, a1), (t2, a2) in zip(items, items[1:]):
            hops = abs(
                section_order.get(t1.sectionId, 0) - section_order.get(t2.sectionId, 0)
            )
            need = hops * MACHINE_TRANSIT_PER_SECTION
            if a2.start - a1.end < need:
                out.append(
                    Violation(
                        "HC-012",
                        f"machine {machine} needs {need} min to move from {t1.sectionId} "
                        f"to {t2.sectionId}; the plan allows {a2.start - a1.end}",
                    )
                )

    # HC-018 concurrent speed restriction budget, measured over the severe day.
    restrictions = speed_restrictions(world, plan)
    for sr in restrictions:
        # Concurrency is measured at an instant. Two restrictions that each overlap a
        # third need not overlap each other, so summing everything "nearby" invents
        # violations that do not exist.
        concurrent = sum(
            other.lengthKm
            for other in restrictions
            if other.start <= sr.start < other.start + 1440
        )
        if concurrent > MAX_CONCURRENT_SR_KM + 1e-6:
            out.append(
                Violation(
                    "HC-018",
                    f"{concurrent:.1f} km under {SR_DAY_SPEEDS_KMPH[0]} kmph restriction at "
                    f"minute {sr.start} against a corridor budget of "
                    f"{MAX_CONCURRENT_SR_KM} km",
                )
            )

    # The plan must survive the timetable it creates: recompute the graph under its
    # own caution orders and restrictions, then re-check HC-001 against it. A plan
    # that only works if its own consequences are ignored is not a plan.
    if plan.assignments:
        after = recompute(world, plan)
        for a in plan.assignments:
            task = task_of[a.taskId]
            for tr in after.trains:
                if tr.sectionId != task.sectionId or tr.track != task.track:
                    continue
                if a.start < tr.exit + headway and tr.entry - headway < a.end:
                    out.append(
                        Violation(
                            "HC-001/RECOMPUTE",
                            f"once this plan's own restrictions slow the timetable, "
                            f"{a.taskId} [{a.start},{a.end}] collides with train "
                            f"{tr.trainId} [{tr.entry},{tr.exit}]",
                        )
                    )

    # HC-013 gang transit between sections.
    section_index = {s.sectionId: i for c in world.corridors for i, s in enumerate(c.sections)}
    by_gang: dict[str, list] = {}
    for task, a in scheduled:
        if task.gangId:
            by_gang.setdefault(task.gangId, []).append((task, a))
    for gang, items in by_gang.items():
        items.sort(key=lambda x: x[1].start)
        for (t1, a1), (t2, a2) in zip(items, items[1:]):
            hops = abs(section_index.get(t1.sectionId, 0) - section_index.get(t2.sectionId, 0))
            need = hops * GANG_TRANSIT_PER_SECTION
            if a2.start - a1.end < need:
                out.append(
                    Violation(
                        "HC-013",
                        f"gang {gang} needs {need} min to reach {t2.sectionId} from "
                        f"{t1.sectionId}; the plan allows {a2.start - a1.end}",
                    )
                )

    # HC-011 IMR statutory deadline.
    for task in world.tasks:
        if not task.isEmergency:
            continue
        a = at.get(task.taskId)
        if a is None:
            out.append(Violation("HC-011", f"emergency task {task.taskId} is not scheduled"))
        elif task.detectedAtMinute is not None and a.start > task.detectedAtMinute + IMR_DEADLINE_MINUTES:
            out.append(
                Violation(
                    "HC-011",
                    f"{task.taskId} starts at {a.start}, beyond the 72 h statutory limit "
                    f"({task.detectedAtMinute + IMR_DEADLINE_MINUTES})",
                )
            )

    # HC-014 no possession while a train occupies the section.
    for block in plan.blocks:
        for tr in world.trains:
            if tr.sectionId != block.sectionId or tr.track != block.track:
                continue
            if block.start < tr.exit and tr.entry < block.end:
                out.append(
                    Violation(
                        "HC-014",
                        f"block {block.blockId} [{block.start},{block.end}] granted while "
                        f"train {tr.trainId} occupies the section",
                    )
                )

    # HC-015 daylight restriction.
    for a in plan.assignments:
        task = task_of[a.taskId]
        if task.hasMobileLighting:
            continue
        day = a.start // 1440
        if a.start < day * 1440 + SUNRISE_MINUTE or a.end > day * 1440 + SUNSET_MINUTE:
            out.append(
                Violation(
                    "HC-015",
                    f"{a.taskId} runs [{a.start},{a.end}] without mobile lighting; "
                    f"work must fall between sunrise and sunset",
                )
            )

    # HC-016 maximum continuous possession.
    for block in plan.blocks:
        cap = max(
            MAX_BLOCK_MINUTES,
            max(required_span(task_of[t]) for t in block.taskIds),
        )
        if block.end - block.start > cap:
            out.append(
                Violation(
                    "HC-016",
                    f"block {block.blockId} runs {block.end - block.start} min against a "
                    f"cap of {cap}",
                )
            )

    # Structural integrity of the plan itself.
    for a in plan.assignments:
        block = block_of[a.taskId]
        if a.start < block.start or a.end > block.end:
            out.append(Violation("PLAN", f"{a.taskId} falls outside block {block.blockId}"))
    seen = [a.taskId for a in plan.assignments]
    if len(seen) != len(set(seen)):
        out.append(Violation("PLAN", "a task is assigned more than once"))
    covered = set(seen) | {u.taskId for u in plan.unassigned}
    missing = {t.taskId for t in world.tasks} - covered
    if missing:
        out.append(Violation("PLAN", f"tasks neither scheduled nor reported: {sorted(missing)}"))

    return out


def assert_clean(world: ScenarioWorld, plan: Plan, headway: int = DEFAULT_HEADWAY) -> None:
    violations = audit(world, plan, headway)
    if violations:
        raise AssertionError(
            "hard constraint audit failed:\n" + "\n".join(f"  {v}" for v in violations)
        )
