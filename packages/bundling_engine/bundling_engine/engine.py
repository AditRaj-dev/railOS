"""Task Bundling Engine.

Produces candidate bundles -- sets of tasks that could share one block. It does not
decide the schedule; the optimizer does. A bundle is a *proposal* carrying its own
justification, and every task in it has been checked pairwise against the verified
compatibility matrix.
"""

import itertools

from railos_model import (
    BlockType,
    BundleCandidate,
    Compatibility,
    Department,
    MaintenanceTask,
    Opportunity,
    ScenarioWorld,
)

from .compatibility import pair, unary_violations


def _block_type(tasks: list[MaintenanceTask]) -> BlockType:
    departments = {t.department for t in tasks}
    needs_power = any(t.requiresPTW for t in tasks)
    if len(departments) > 1:
        return BlockType.INTEGRATED
    if departments == {Department.TRD} and needs_power:
        return BlockType.POWER
    if needs_power:
        # One department, but traffic block plus power block = integrated possession.
        return BlockType.INTEGRATED
    if departments == {Department.SNT} and all(t.requiresT351 for t in tasks):
        return BlockType.DISCONNECTION
    return BlockType.TRAFFIC


def _sequence(tasks: list[MaintenanceTask], world: ScenarioWorld) -> list[str]:
    """Topological order over the declared dependencies, ids only.

    ponytail: Kahn on a handful of tasks; the optimizer enforces the real precedence
    constraints, this list is for the controller to read.
    """
    ids = {t.taskId for t in tasks}
    edges = [
        (d.predecessorTaskId, d.successorTaskId)
        for d in world.dependencies
        if d.predecessorTaskId in ids and d.successorTaskId in ids
    ]
    if not edges:
        return []
    incoming = {i: 0 for i in ids}
    for _a, b in edges:
        incoming[b] += 1
    ready = sorted(i for i, n in incoming.items() if n == 0)
    order: list[str] = []
    while ready:
        node = ready.pop(0)
        order.append(node)
        for a, b in edges:
            if a == node:
                incoming[b] -= 1
                if incoming[b] == 0:
                    ready.append(b)
        ready.sort()
    return order if len(order) == len(ids) else []


def evaluate(tasks: list[MaintenanceTask], world: ScenarioWorld) -> tuple[Compatibility, list[str]]:
    """Verdict for a whole set: the worst pairwise verdict wins."""
    rationale: list[str] = []
    worst = Compatibility.COMPATIBLE
    rank = {
        Compatibility.COMPATIBLE: 0,
        Compatibility.SEQUENTIALLY_COMPATIBLE: 1,
        Compatibility.CONDITIONAL: 2,
        Compatibility.INCOMPATIBLE: 3,
        Compatibility.STRICTLY_PROHIBITED: 4,
    }
    for t in tasks:
        rationale += unary_violations(t)
    if rationale:
        return Compatibility.STRICTLY_PROHIBITED, rationale
    for a, b in itertools.combinations(tasks, 2):
        verdict, why = pair(a, b)
        if rank[verdict] > rank[worst]:
            worst = verdict
        if verdict is not Compatibility.COMPATIBLE:
            rationale.append(f"{a.taskId} + {b.taskId}: {verdict.value} -- {why}")
    return worst, rationale


def build(
    world: ScenarioWorld,
    opportunities: list[Opportunity],
    priority: dict[str, float] | None = None,
    max_bundle: int = 5,
) -> list[BundleCandidate]:
    """One candidate bundle per opportunity, greedily filled highest priority first.

    Greedy is enough here: the optimizer re-decides everything. What matters is that
    a bundle we hand over is *legal*, not that it is optimal.
    """
    priority = priority or {}
    out: list[BundleCandidate] = []
    for n, op in enumerate(opportunities, start=1):
        pool = sorted(
            (world.task(tid) for tid in op.candidateTaskIds),
            key=lambda t: -priority.get(t.taskId, float(t.severity * 10)),
        )
        chosen: list[MaintenanceTask] = []
        for task in pool:
            if len(chosen) >= max_bundle:
                break
            trial = chosen + [task]
            verdict, _ = evaluate(trial, world)
            if verdict in (
                Compatibility.COMPATIBLE,
                Compatibility.SEQUENTIALLY_COMPATIBLE,
                Compatibility.CONDITIONAL,
            ):
                chosen = trial
        if not chosen:
            continue
        verdict, rationale = evaluate(chosen, world)
        out.append(
            BundleCandidate(
                bundleId=f"BND-{n:03d}",
                taskIds=[t.taskId for t in chosen],
                blockType=_block_type(chosen),
                sequence=_sequence(chosen, world),
                requiredResourceIds=sorted({r for t in chosen for r in t.resourceIds}),
                compatibility=verdict,
                rationale=rationale
                or [f"{len(chosen)} tasks verified compatible for a shared possession"],
            )
        )
    return out
