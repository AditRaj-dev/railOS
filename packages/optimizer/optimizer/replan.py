"""Replanning and plan versioning.

An approved plan is never mutated. Replanning clones it, locks whatever is already
under way, re-solves the remaining horizon with a churn penalty, and returns a
PROPOSED plan plus an explicit diff. A human approves; the system does not.

    v1 generated -> v2 forecast changed -> v3 emergency inserted -> v4 human approved
"""

from dataclasses import dataclass, field

from railos_model import (
    MaintenanceTask,
    Plan,
    PlanStatus,
    ScenarioWorld,
)

from .model import SolveOptions, solve

#: Objective points charged per minute a task moves from its published time.
#: Small next to yield, large enough that gratuitous churn loses.
DEFAULT_CHURN_WEIGHT = 0.5


@dataclass
class PlanDiff:
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    moved: list[tuple[str, int, int]] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    metric_deltas: dict[str, float] = field(default_factory=dict)

    @property
    def displaced(self) -> list[str]:
        """Work that was promised and is no longer in the plan. The controller must
        see this explicitly -- a silently dropped task is how maintenance debt hides."""
        return self.removed

    def summary(self) -> str:
        return (
            f"+{len(self.added)} added, -{len(self.removed)} displaced, "
            f"{len(self.moved)} moved, {len(self.unchanged)} unchanged"
        )


def diff(old: Plan, new: Plan) -> PlanDiff:
    o = {a.taskId: a.start for a in old.assignments}
    n = {a.taskId: a.start for a in new.assignments}
    d = PlanDiff(
        added=sorted(set(n) - set(o)),
        removed=sorted(set(o) - set(n)),
        moved=sorted((t, o[t], n[t]) for t in set(o) & set(n) if o[t] != n[t]),
        unchanged=sorted(t for t in set(o) & set(n) if o[t] == n[t]),
    )
    for field_name in type(old.metrics).model_fields:
        before = getattr(old.metrics, field_name)
        after = getattr(new.metrics, field_name)
        if before != after:
            d.metric_deltas[field_name] = round(after - before, 4)
    return d


def locked_from(plan: Plan, world: ScenarioWorld, now: int) -> dict[str, int]:
    """Work already started, or explicitly immutable, keeps its published time."""
    out: dict[str, int] = {}
    for a in plan.assignments:
        task = world.task(a.taskId)
        if task.locked or a.start <= now < a.end or a.end <= now:
            out[a.taskId] = a.start
    return out


def replan(
    world: ScenarioWorld,
    previous: Plan,
    now: int = 0,
    churn_weight: float = DEFAULT_CHURN_WEIGHT,
    reason: str = "replan",
    config_path=None,
) -> tuple[Plan, PlanDiff]:
    """Re-solve the horizon after `now`, keeping started work fixed."""
    opts = SolveOptions(
        profile=previous.objectiveProfile,
        locked_starts=locked_from(previous, world, now),
        reference_starts={a.taskId: a.start for a in previous.assignments},
        churn_weight=churn_weight,
        horizon_lock_before=now,
    )
    plan = solve(world, opts, config_path)
    plan.planVersion = previous.planVersion + 1
    plan.parentPlanId = previous.planId
    plan.status = PlanStatus.PROPOSED
    plan.provenance = (
        f"{reason}; revised from {previous.planId} v{previous.planVersion} at minute {now}; "
        f"{len(opts.locked_starts)} operations locked; requires human approval"
    )
    d = diff(previous, plan)
    if d.removed:
        plan.warnings.insert(
            0,
            "DISPLACED WORK: "
            + ", ".join(d.removed)
            + " were in the previous plan and are not in this one.",
        )
    plan.warnings.insert(0, f"PROPOSED plan -- not approved. {d.summary()}.")
    return plan, d


def insert_emergency(world: ScenarioWorld, task: MaintenanceTask) -> ScenarioWorld:
    """Return a new world with an emergency task added. The original is untouched."""
    clone = world.model_copy(deep=True)
    clone.tasks.append(task)
    return clone


def approve(plan: Plan, approver: str) -> Plan:
    """Human approval at the library/solver level. Returns a new version; the proposed plan stays on record.

    Note: In RailOS, 'approved' now has two distinct layers:
    - Library-level approval (this function): marks a Plan model instance APPROVED for simulator / offline flows.
    - API-level sanctioning: multi-authority SanctionChain (Sr.DOM, Section Controller, TPC, Station Master)
      before runtime possessions are opened.
    """
    if plan.status is PlanStatus.APPROVED:
        raise ValueError(f"{plan.planId} is already approved")
    approved = plan.model_copy(deep=True)
    approved.planVersion = plan.planVersion + 1
    approved.parentPlanId = plan.planId
    approved.status = PlanStatus.APPROVED
    approved.provenance = f"approved by {approver}; derived from {plan.planId}"
    approved.warnings = [w for w in plan.warnings if not w.startswith("PROPOSED plan")]
    return approved
