"""HC-010, HC-012 and HC-018: the consequences a plan leaves on the train graph."""

import pytest

from optimizer import audit, solve, solve_converged
from optimizer.config import CAUTION_ORDER_SPEED_KMPH, MACHINE_TRANSIT_PER_SECTION
from optimizer.traingraph import (
    SR_DAY_SPEEDS_KMPH,
    caution_orders,
    delay_minutes,
    disruption,
    recompute,
    speed_restrictions,
    worked_km,
)
from railos_model import Assignment, Plan, ObjectiveProfile, ScheduledBlock, Track


def test_delay_is_computed_over_the_restricted_length_not_the_section(world):
    """A 300 m turnout does not put 36 km at 20 kmph. Getting this wrong makes the
    optimizer refuse work it should be doing."""
    whole_section = delay_minutes(world, "SEC_KRJ_SMQ", 20)
    short_work = delay_minutes(world, "SEC_KRJ_SMQ", 20, 0.3)
    assert short_work < whole_section
    assert short_work <= 2


def test_delay_is_zero_when_the_restriction_matches_line_speed(world):
    section = world.corridors[0].sections[0]
    assert delay_minutes(world, section.sectionId, section.mps, 1.0) == 0


def test_worked_km_never_collapses_to_zero(world):
    task = world.task("SNT-2003")  # 100 m of point work
    assert worked_km(task) >= 0.1


def test_infringing_work_produces_a_caution_order(world, plan):
    orders = caution_orders(world, plan)
    assert orders, "ENG-1002 infringes the adjacent line; a T/409 must be issued"
    for o in orders:
        assert o.speedKmph == CAUTION_ORDER_SPEED_KMPH
        assert o.lengthKm > 0
        assert "HC-01" in o.describe() or "HC-012" in o.cause or "HC-010" in o.cause


def test_caution_order_applies_to_the_other_track(world, plan):
    tasks = {a.taskId: world.task(a.taskId) for a in plan.assignments}
    for o in caution_orders(world, plan):
        cause = o.cause.split(" ")[0]
        assert o.track != tasks[cause].track


def test_speed_restriction_follows_the_block_and_decays(world, plan):
    restrictions = speed_restrictions(world, plan)
    assert restrictions
    sr = restrictions[0]
    assert sr.speed_at(sr.start) == SR_DAY_SPEEDS_KMPH[0]
    assert sr.speed_at(sr.start + 1440) == SR_DAY_SPEEDS_KMPH[1]
    assert sr.speed_at(sr.start + 2 * 1440) == SR_DAY_SPEEDS_KMPH[2]
    assert sr.speed_at(sr.end) is None
    assert sr.speed_at(sr.start - 1) is None


def test_recompute_slows_trains_and_cascades_down_the_path(world, plan):
    after = recompute(world, plan)
    before = {(m.trainId, m.sectionId, m.track): m for m in world.trains}
    slowed = [
        m
        for m in after.trains
        if (m.exit - m.entry) > (lambda o: o.exit - o.entry)(before[(m.trainId, m.sectionId, m.track)])
    ]
    assert slowed, "a plan with restrictions must slow somebody down"
    # Delay carried forward: a train delayed in one section enters the next one late.
    cascaded = [m for m in after.trains if m.delayMinutes > 0]
    assert len(cascaded) >= len(slowed)


def test_recompute_does_not_mutate_the_input(world, plan):
    snapshot = world.model_dump_json()
    recompute(world, plan)
    assert world.model_dump_json() == snapshot


def test_disruption_is_reported_and_no_longer_assumed_zero(world, plan):
    numbers = disruption(world, plan, {"RAJDHANI": 50, "MAIL_EXPRESS": 30})
    assert numbers["trainDisruptionMinutes"] > 0
    assert plan.metrics.trainDisruptionMinutes == numbers["trainDisruptionMinutes"]


def test_no_maintenance_on_the_adjacent_line_during_infringing_work(world, plan):
    """HC-010 / HC-012 as a scheduling constraint, not a note in the margin."""
    scheduled = [(world.task(a.taskId), a) for a in plan.assignments]
    for ti, ai in scheduled:
        if not (ti.infringesAdjacent or ti.machineType.value == "TOWER_WAGON"):
            continue
        for tj, aj in scheduled:
            if tj.taskId == ti.taskId or tj.sectionId != ti.sectionId or tj.track == ti.track:
                continue
            assert not (ai.start < aj.end and aj.start < ai.end), f"{ti.taskId} vs {tj.taskId}"


def test_a_machine_cannot_teleport_between_sections(world, plan):
    order = {s.sectionId: i for c in world.corridors for i, s in enumerate(c.sections)}
    by_machine: dict[str, list] = {}
    for a in plan.assignments:
        for r in world.task(a.taskId).resourceIds:
            by_machine.setdefault(r, []).append((world.task(a.taskId), a))
    for items in by_machine.values():
        items.sort(key=lambda x: x[1].start)
        for (t1, a1), (t2, a2) in zip(items, items[1:]):
            hops = abs(order.get(t1.sectionId, 0) - order.get(t2.sectionId, 0))
            assert a2.start - a1.end >= hops * MACHINE_TRANSIT_PER_SECTION


def test_concurrent_speed_restrictions_stay_within_the_corridor_budget(world, plan):
    from optimizer.config import MAX_CONCURRENT_SR_KM

    restrictions = speed_restrictions(world, plan)
    for sr in restrictions:
        concurrent = sum(
            o.lengthKm
            for o in restrictions
            if o.start < sr.start + 1440 and sr.start < o.start + 1440
        )
        assert concurrent <= MAX_CONCURRENT_SR_KM + 1e-6


def test_audit_catches_a_plan_that_ignores_its_own_restrictions(world):
    """Hand-build a plan that only survives if the SR it creates is ignored. The
    recompute check must reject it -- otherwise the check is decoration."""
    task = world.task("ENG-1002")  # imposes a speed restriction
    victim = next(
        t
        for t in world.trains
        if t.sectionId == task.sectionId and t.track == task.track and t.entry > 100
    )
    start = victim.entry - task.estimatedDuration - 200
    bad = Plan(
        planId="PLAN-BAD",
        planVersion=1,
        objectiveProfile=ObjectiveProfile.BALANCED,
        horizonMinutes=world.horizonMinutes,
        blocks=[
            ScheduledBlock(
                blockId="BLK-BAD",
                sectionId=task.sectionId,
                track=task.track,
                blockType=task.blockType,
                start=start - 20,
                end=start + task.estimatedDuration + 15,
                taskIds=[task.taskId],
                departments=[task.department],
            )
        ],
        assignments=[
            Assignment(
                taskId=task.taskId,
                blockId="BLK-BAD",
                start=start,
                end=start + task.estimatedDuration,
            )
        ],
    )
    codes = {v.code for v in audit(world, bad)}
    assert codes, "a plan overlapping a train path must not audit clean"


def test_solve_converged_returns_the_timetable_it_planned_against(world):
    plan, after = solve_converged(world)
    assert plan.solverStatus in ("OPTIMAL", "FEASIBLE")
    assert plan.runtime["graphIterations"] >= 1
    assert not audit(after, plan)
    # The consequences exist whether or not a second pass was needed: recomputing
    # the graph under this plan must move somebody.
    consequence = recompute(world, plan)
    moved = sum(1 for a, b in zip(world.trains, consequence.trains) if a.exit != b.exit)
    assert moved > 0, "the plan imposes restrictions, so the graph must move"


def test_convergence_repairs_a_plan_that_collided_with_its_own_restrictions(world):
    """The loop must earn its place: on a disturbed world, the single pass produces
    collisions that the converged solve resolves."""
    import simulator as sim

    disturbed = sim.SCENARIOS["train_delayed"](world)
    single = solve(disturbed, converge=False)
    converged = solve(disturbed)
    single_conflicts = [v for v in audit(disturbed, single) if v.code == "HC-001/RECOMPUTE"]
    assert single_conflicts, "expected the undisturbed pass to miss its own consequences"
    assert not audit(disturbed, converged)
    assert converged.runtime["graphIterations"] > 1
