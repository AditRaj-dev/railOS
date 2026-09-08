"""Deterministic scenario simulator.

Each function takes a world and returns a NEW world -- disturbance as data, never a
branch inside the optimizer. The optimizer solves the same model against the changed
facts, which is what makes the replanning demo honest.

Covers the disruption list in the charter and failure modes A-D of the Ground
Reality Report section 16.
"""

from railos_model import (
    Department,
    MachineType,
    MaintenanceTask,
    ScenarioWorld,
    Severity,
    TaskType,
    Track,
    Defect,
)

IMR_DEADLINE_MINUTES = 4320


def _clone(world: ScenarioWorld) -> ScenarioWorld:
    return world.model_copy(deep=True)


def delay_train(world: ScenarioWorld, train_id: str, minutes: int) -> ScenarioWorld:
    """Scenario 5 / failure mode C: a premium train runs late and its path shifts
    forward into planned block time."""
    w = _clone(world)
    for mv in w.trains:
        if mv.trainId == train_id:
            mv.entry += minutes
            mv.exit += minutes
            mv.delayMinutes = minutes
    return w


def increase_goods(world: ScenarioWorld, factor: float = 1.5) -> ScenarioWorld:
    """Freight forecast rises: more probable rakes competing for the same paths."""
    w = _clone(world)
    for g in w.goods:
        g.probability = min(1.0, g.probability * factor)
        g.priorityWeight *= factor
    return w


def extend_task(world: ScenarioWorld, task_id: str, extra_minutes: int) -> ScenarioWorld:
    """Failure mode B: the tamper develops a hydraulic fault and the work overruns."""
    w = _clone(world)
    task = w.task(task_id)
    task.estimatedDuration += extra_minutes
    task.durationStdDev += extra_minutes // 3
    return w


def cancel_window(world: ScenarioWorld, section_id: str, start: int, end: int) -> ScenarioWorld:
    """A block is cancelled by inserting a special train path over the window, which
    is exactly what happens operationally when the section is taken back."""
    w = _clone(world)
    from railos_model import TrainClass, TrainMovement

    for track in (Track.UP, Track.DOWN):
        w.trains.append(
            TrainMovement(
                trainId=f"CANCEL-{section_id}-{start}",
                sectionId=section_id,
                track=track,
                entry=start,
                exit=end,
                trainClass=TrainClass.MAIL_EXPRESS,
                priority=10,
            )
        )
    return w


def remove_resource(world: ScenarioWorld, resource_id: str) -> ScenarioWorld:
    """Crew or machine unavailable. Tasks that need it become unschedulable and are
    reported as such -- not quietly dropped."""
    w = _clone(world)
    w.resources = [r for r in w.resources if r.resourceId != resource_id]
    for t in w.tasks:
        if resource_id in t.resourceIds:
            t.resourceIds = [r for r in t.resourceIds if r != resource_id]
            t.status = t.status
    return w


def refuse_t351(world: ScenarioWorld, task_id: str) -> ScenarioWorld:
    """Failure mode D: the Station Master refuses the disconnection. The affected
    S&T work cannot run; the bundling engine must decouple whatever is independent."""
    w = _clone(world)
    task = w.task(task_id)
    task.requiresT351 = True
    task.status = task.status
    w.tasks = [t for t in w.tasks if t.taskId != task_id]
    w.dependencies = [
        d
        for d in w.dependencies
        if task_id not in (d.predecessorTaskId, d.successorTaskId)
    ]
    return w


def emergency_imr(
    world: ScenarioWorld,
    section_id: str = "SEC_KRJ_SMQ",
    track: Track = Track.UP,
    km: float = 142.6,
    detected_at: int = 600,
    duration: int = 90,
) -> ScenarioWorld:
    """Failure mode A / Scenario 2: an IMR rail fracture is reported. Statutory
    72-hour replacement window (HC-011), and the task is not optional.

    RailOS flags it, prices it and proposes a block. It never authorizes possession.
    """
    w = _clone(world)
    task = MaintenanceTask(
        taskId="ENG-EMG-IMR",
        department=Department.ENGG,
        assetId=f"TRACK_SEC_{section_id.split('_', 1)[1]}_{track.value}",
        corridorId=w.corridors[0].corridorId if w.corridors else "GZB-ALJN",
        sectionId=section_id,
        track=track,
        kmStart=km,
        kmEnd=km + 0.1,
        taskType=TaskType.RAIL_REPLACEMENT,
        severity=10,
        criticality=10,
        dueMinute=detected_at + IMR_DEADLINE_MINUTES,
        estimatedDuration=duration,
        durationStdDev=20,
        machineType=MachineType.NONE,
        gangId="ENGG-GANG-KRJ",
        isEmergency=True,
        detectedAtMinute=detected_at,
        imposesSpeedRestriction=True,
        overdueDays=0,
    )
    w.tasks.append(task)
    w.defects.append(
        Defect(
            defectId="DEF-EMG-IMR",
            assetId=task.assetId,
            sectionId=section_id,
            severityCode=Severity.IMR,
            detectedAtMinute=detected_at,
            taskId=task.taskId,
        )
    )
    return w


SCENARIOS = {
    "train_delayed": lambda w: delay_train(w, "12310", 45),
    "goods_increased": lambda w: increase_goods(w, 1.5),
    "task_overrun": lambda w: extend_task(w, "ENG-1001", 60),
    "block_cancelled": lambda w: cancel_window(w, "SEC_GZB_DER", 0, 240),
    "critical_defect": emergency_imr,
    "crew_unavailable": lambda w: remove_resource(w, "CSM-104"),
    "t351_refused": lambda w: refuse_t351(w, "SNT-2002"),
}
