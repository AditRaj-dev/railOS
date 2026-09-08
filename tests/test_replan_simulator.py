"""Replanning never mutates an approved plan, and every scenario stays feasible-or-honest."""
import importlib.util
if importlib.util.find_spec("ortools") is None:
    import unittest
    raise unittest.SkipTest("ortools unavailable in stdlib test runtime")

import pytest

import simulator as sim
from optimizer import approve, audit, diff, replan, solve
from railos_model import PlanStatus


def test_approval_creates_a_new_version(world, plan):
    approved = approve(plan, "Sr.DOM/GZB")
    assert approved.status is PlanStatus.APPROVED
    assert approved.planVersion == plan.planVersion + 1
    assert approved.parentPlanId == plan.planId
    assert plan.status is PlanStatus.GENERATED  # the original is untouched


def test_approved_plan_cannot_be_approved_twice(world, plan):
    approved = approve(plan, "Sr.DOM/GZB")
    with pytest.raises(ValueError):
        approve(approved, "someone else")


def test_replan_returns_a_proposal_not_an_approval(world, plan):
    approved = approve(plan, "Sr.DOM/GZB")
    revised, _ = replan(world, approved, now=200)
    assert revised.status is PlanStatus.PROPOSED
    assert revised.planVersion == approved.planVersion + 1
    assert revised.parentPlanId == approved.planId
    assert approved.status is PlanStatus.APPROVED


def test_started_work_is_not_moved_by_a_replan(world, plan):
    approved = approve(plan, "Sr.DOM/GZB")
    now = min(a.start for a in approved.assignments) + 5  # something is under way
    revised, delta = replan(world, approved, now=now)
    started = [a for a in approved.assignments if a.start <= now < a.end]
    assert started, "test needs at least one operation in progress"
    for a in started:
        kept = next(x for x in revised.assignments if x.taskId == a.taskId)
        assert kept.start == a.start


def test_emergency_replan_inserts_work_and_reports_displacement(world, plan):
    approved = approve(plan, "Sr.DOM/GZB")
    w = sim.emergency_imr(world, detected_at=600)
    revised, delta = replan(w, approved, now=300, reason="IMR rail fracture")
    assert "ENG-EMG-IMR" in delta.added
    assert revised.warnings[0].startswith("PROPOSED plan")
    assert not audit(w, revised)
    assert set(delta.displaced) == set(delta.removed)


def test_diff_reports_metric_movement(world, plan):
    approved = approve(plan, "Sr.DOM/GZB")
    w = sim.emergency_imr(world, detected_at=600)
    revised, delta = replan(w, approved, now=300)
    assert delta.metric_deltas
    assert delta.summary()


@pytest.mark.parametrize("name", sorted(sim.SCENARIOS))
def test_every_scenario_still_produces_an_auditable_answer(world, name):
    disturbed = sim.SCENARIOS[name](world)
    plan = solve(disturbed)
    if plan.solverStatus in ("OPTIMAL", "FEASIBLE"):
        assert not audit(disturbed, plan), name
    else:
        # No feasible plan is a legitimate answer -- but it must say so, and it must
        # not pretend to have scheduled anything.
        assert not plan.assignments
        assert plan.warnings


def test_scenarios_do_not_mutate_the_original_world(world):
    before = world.model_dump_json()
    for build in sim.SCENARIOS.values():
        build(world)
    assert world.model_dump_json() == before
