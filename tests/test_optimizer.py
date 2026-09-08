"""The charter's required optimizer tests, plus the independent audit."""
import importlib.util
if importlib.util.find_spec("ortools") is None:
    import unittest
    raise unittest.SkipTest("ortools unavailable in stdlib test runtime")

from bundling_engine import prohibited
from optimizer import SolveOptions, audit, solve
from optimizer.config import PTW_LEAD_IN
from railos_model import ObjectiveProfile, PlanStatus


def test_plan_passes_the_independent_hard_constraint_audit(world, plan):
    violations = audit(world, plan)
    assert not violations, "\n".join(str(v) for v in violations)


def test_solver_reaches_a_solution(world, plan):
    assert plan.solverStatus in ("OPTIMAL", "FEASIBLE")


def test_no_task_falls_outside_its_block(world, plan):
    blocks = {b.blockId: b for b in plan.blocks}
    for a in plan.assignments:
        block = blocks[a.blockId]
        assert block.start <= a.start and a.end <= block.end


def test_no_duplicate_assignment(plan):
    ids = [a.taskId for a in plan.assignments]
    assert len(ids) == len(set(ids))


def test_every_task_is_either_scheduled_or_reported(world, plan):
    covered = {a.taskId for a in plan.assignments} | {u.taskId for u in plan.unassigned}
    assert covered == {t.taskId for t in world.tasks}


def test_unassigned_tasks_carry_a_reason(plan):
    assert all(u.reason for u in plan.unassigned)


def test_dependencies_are_respected(world, plan):
    at = {a.taskId: a for a in plan.assignments}
    for d in world.dependencies:
        a, b = at.get(d.predecessorTaskId), at.get(d.successorTaskId)
        if a and b:
            assert a.end + d.lagMinutes <= b.start


def test_incompatible_tasks_never_share_time_and_place(world, plan):
    at = [(world.task(a.taskId), a) for a in plan.assignments]
    for i in range(len(at)):
        for j in range(i + 1, len(at)):
            (ti, ai), (tj, aj) = at[i], at[j]
            if ti.sectionId != tj.sectionId or ti.track != tj.track:
                continue
            if ai.start < aj.end and aj.start < ai.end:
                assert not prohibited(ti, tj)


def test_no_hard_train_conflict(world, plan):
    for a in plan.assignments:
        task = world.task(a.taskId)
        for tr in world.trains:
            if tr.sectionId != task.sectionId or tr.track != task.track:
                continue
            assert not (a.start < tr.exit and tr.entry < a.end)


def test_power_block_buffers_are_inside_the_possession(world, plan):
    blocks = {b.blockId: b for b in plan.blocks}
    for a in plan.assignments:
        if world.task(a.taskId).requiresPTW:
            assert a.start - blocks[a.blockId].start >= PTW_LEAD_IN


def test_locked_work_does_not_move(world):
    first = solve(world)
    victim = first.assignments[0]
    locked = solve(world, SolveOptions(locked_starts={victim.taskId: victim.start}))
    kept = next(a for a in locked.assignments if a.taskId == victim.taskId)
    assert kept.start == victim.start


def test_emergency_work_is_scheduled_and_prioritised(world):
    from simulator import emergency_imr

    w = emergency_imr(world, detected_at=600)
    plan = solve(w)
    emergency = next(a for a in plan.assignments if a.taskId == "ENG-EMG-IMR")
    assert emergency.start >= 600
    assert emergency.start <= 600 + 4320  # HC-011 statutory ceiling
    assert not audit(w, plan)


def test_metrics_are_reproducible(world):
    a, b = solve(world), solve(world)
    assert a.metrics == b.metrics
    assert a.objectiveBreakdown == b.objectiveBreakdown


def test_profiles_change_the_answer_not_the_algorithm(world):
    plans = {p: solve(world, SolveOptions(profile=p)) for p in ObjectiveProfile}
    for p, plan in plans.items():
        assert plan.solverStatus in ("OPTIMAL", "FEASIBLE"), p
        assert not audit(world, plan), p
    # OPERATIONS_FIRST protects traffic, so it must not schedule MORE work than
    # SAFETY_FIRST does.
    assert (
        plans[ObjectiveProfile.OPERATIONS_FIRST].metrics.tasksScheduled
        <= plans[ObjectiveProfile.SAFETY_FIRST].metrics.tasksScheduled
    )


def test_every_assignment_explains_itself(plan):
    expected = {
        "priority_contribution",
        "urgency_contribution",
        "bundling_benefit",
        "traffic_penalty",
        "unused_window_penalty",
        "risk_reduction",
    }
    for a in plan.assignments:
        assert expected <= {f.name for f in a.explanation}


def test_plan_envelope_is_complete(plan):
    assert plan.planId and plan.planVersion == 1
    assert plan.status is PlanStatus.GENERATED
    assert plan.runtime["solver"] == "OR-Tools CP-SAT"
    assert "TOTAL" in plan.objectiveBreakdown


def test_infeasible_demand_is_reported_not_relaxed(world):
    """A task with no legal window must come back unassigned with a reason -- the
    optimizer must never invent room for it."""
    w = world.model_copy(deep=True)
    victim = w.task("ENG-1005").model_copy(deep=True)
    victim.taskId = "ENG-IMPOSSIBLE"
    victim.estimatedDuration = 1400  # longer than any traffic-free window
    victim.durationStdDev = 0
    w.tasks.append(victim)
    plan = solve(w)
    reason = next(u.reason for u in plan.unassigned if u.taskId == "ENG-IMPOSSIBLE")
    assert "window" in reason
    assert not audit(w, plan)
