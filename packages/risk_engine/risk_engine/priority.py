"""Maintenance Priority Engine.

Deterministic weighted scoring. Every contribution is returned as a named Factor
with its raw value and weight, so the number shown to a controller can always be
taken apart. Nothing here is machine learning.
"""

from railos_model import Factor, MaintenanceTask, PriorityResult, ScenarioWorld, Severity

from .config import load_weights

#: Consequence-of-failure proxy per defect code, 0-10. Used when a task has a defect.
_FAILURE_RISK = {
    Severity.IMR: 10.0,
    Severity.IMRW: 9.0,
    Severity.OHE_DROPPING_FAULT: 8.0,
    Severity.OMS_PEAK_HIGH: 7.0,
    Severity.POINT_SLACK_DETECTION: 6.5,
    Severity.OBS: 3.0,
}

#: Traffic density proxy: how much the section is used, 0-10. Derived from the WTT.
_MAX_TRAINS_FOR_SCALE = 60


def _operational_impact(task: MaintenanceTask, world: ScenarioWorld) -> float:
    """Line traffic density on the task's section, scaled 0-10."""
    n = sum(1 for t in world.trains if t.sectionId == task.sectionId)
    return min(10.0, 10.0 * n / _MAX_TRAINS_FOR_SCALE)


def _failure_risk(task: MaintenanceTask, world: ScenarioWorld) -> float:
    codes = [d.severityCode for d in world.defects if d.taskId == task.taskId]
    repeats = sum(d.repeatCount for d in world.defects if d.taskId == task.taskId)
    base = max((_FAILURE_RISK.get(c, 3.0) for c in codes), default=float(task.severity))
    return min(10.0, base + 0.5 * repeats)


def _overdue_factor(task: MaintenanceTask) -> float:
    """0-10, saturating at 60 days overdue. Monotonic in overdueDays by construction."""
    return min(10.0, task.overdueDays / 6.0)


def score_task(task: MaintenanceTask, world: ScenarioWorld, config_path=None) -> PriorityResult:
    cfg = load_weights(config_path) if config_path else load_weights()
    w = cfg["priority"]

    raws = {
        "safety_criticality": float(task.criticality),
        "defect_severity": float(task.severity),
        "overdue_factor": _overdue_factor(task),
        "asset_criticality": _asset_criticality(task, world),
        "operational_impact": _operational_impact(task, world),
        "failure_risk": _failure_risk(task, world),
    }
    factors = [
        Factor(
            name=name,
            raw=raw,
            weight=w[name],
            contribution=round(raw * 10.0 * w[name], 4),  # raw 0-10 -> score 0-100
        )
        for name, raw in raws.items()
    ]
    score = round(sum(f.contribution for f in factors), 4)
    if task.isEmergency:
        factors.append(
            Factor(
                name="emergency_override",
                raw=1.0,
                weight=1.0,
                contribution=round(100.0 - score, 4),
                note="emergency defect: priority floored at 100 (see HC-011 for IMR deadline)",
            )
        )
        score = 100.0
    return PriorityResult(taskId=task.taskId, score=score, band=_band(score, cfg), factors=factors)


def _asset_criticality(task: MaintenanceTask, world: ScenarioWorld) -> float:
    for a in world.assets:
        if a.assetId == task.assetId:
            return float(a.criticality)
    return float(task.criticality)


def _band(score: float, cfg: dict) -> str:
    for band, threshold in sorted(cfg["bands"].items(), key=lambda kv: -kv[1]):
        if score >= threshold:
            return band
    return "LOW"


def score_all(world: ScenarioWorld, config_path=None) -> dict[str, PriorityResult]:
    return {t.taskId: score_task(t, world, config_path) for t in world.tasks}
