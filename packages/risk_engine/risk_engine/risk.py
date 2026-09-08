"""Maintenance Risk Engine -- consequence of deferring work.

DETERMINISTIC HEURISTIC. Not a trained model, not a prediction. Risk grows linearly
from the current priority at a slope keyed to the defect code, and is capped by the
statutory deferral ceiling where one exists (HC-011: an IMR rail flaw must be dealt
with inside 72 hours).
"""

from railos_model import MaintenanceTask, RiskResult, ScenarioWorld, Severity

from .config import load_weights
from .priority import score_task


def _defect_code(task: MaintenanceTask, world: ScenarioWorld) -> str:
    codes = [d.severityCode for d in world.defects if d.taskId == task.taskId]
    if not codes:
        return "NONE"
    order = [
        Severity.IMR,
        Severity.IMRW,
        Severity.OHE_DROPPING_FAULT,
        Severity.OMS_PEAK_HIGH,
        Severity.POINT_SLACK_DETECTION,
        Severity.OBS,
    ]
    for code in order:
        if code in codes:
            return code.value
    return "NONE"


def assess(task: MaintenanceTask, world: ScenarioWorld, config_path=None) -> RiskResult:
    cfg = load_weights(config_path) if config_path else load_weights()
    rc = cfg["risk"]
    code = _defect_code(task, world)
    slope = rc["slope_per_day"].get(code, rc["slope_per_day"]["NONE"])

    current = score_task(task, world, config_path).score
    at24 = min(100.0, current + slope)
    at72 = min(100.0, current + 3 * slope)

    ceiling = rc["max_deferral_minutes"].get(code, rc["max_deferral_minutes"]["NONE"])
    # Statutory clock starts at detection, not now (HC-011).
    if task.detectedAtMinute is not None:
        ceiling = max(0, task.detectedAtMinute + ceiling)
    # A due date is a commitment too -- whichever bites first wins.
    max_deferral = int(min(ceiling, task.dueMinute))

    eps = rc["trend_epsilon"]
    trend = "RISING" if slope > eps else "STABLE"
    return RiskResult(
        taskId=task.taskId,
        current=round(current, 4),
        at24h=round(at24, 4),
        at72h=round(at72, 4),
        trend=trend,
        maxDeferralMinutes=max_deferral,
    )


def assess_all(world: ScenarioWorld, config_path=None) -> dict[str, RiskResult]:
    return {t.taskId: assess(t, world, config_path) for t in world.tasks}
