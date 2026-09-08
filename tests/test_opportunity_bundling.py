"""Opportunities never touch a train path; bundles never break the compatibility matrix."""

import random

from bundling_engine import evaluate, pair
from bundling_engine import build as build_bundles
from opportunity_engine import detect, detect_shadow
from opportunity_engine.engine import DEFAULT_HEADWAY
from railos_model import Compatibility, ScheduledBlock, TaskType, Track


def test_opportunities_never_overlap_a_train_path(world):
    for op in detect(world):
        for tr in world.trains:
            if tr.sectionId != op.sectionId or tr.track != op.track:
                continue
            assert not (
                op.start < tr.exit + DEFAULT_HEADWAY and tr.entry - DEFAULT_HEADWAY < op.end
            ), f"{op.opportunityId} overlaps train {tr.trainId}"


def test_opportunity_detection_survives_random_timetables(world):
    """Property check: shuffle the timetable, the invariant must hold."""
    rng = random.Random(7)
    w = world.model_copy(deep=True)
    for mv in w.trains:
        shift = rng.randint(-120, 120)
        mv.entry = max(0, mv.entry + shift)
        mv.exit = max(mv.entry + 1, mv.exit + shift)
    for op in detect(w):
        for tr in w.trains:
            if tr.sectionId != op.sectionId or tr.track != op.track:
                continue
            assert not (
                op.start < tr.exit + DEFAULT_HEADWAY and tr.entry - DEFAULT_HEADWAY < op.end
            )


def test_shadow_blocks_are_found_on_the_parallel_line(world):
    primary = ScheduledBlock(
        blockId="BLK-TEST",
        sectionId="SEC_DER_KRJ",
        track=Track.UP,
        blockType="TRAFFIC",
        start=60,
        end=240,
        taskIds=[],
        departments=[],
    )
    shadows = detect_shadow(world, [primary])
    assert shadows
    assert all(s.track != primary.track for s in shadows)
    assert all(s.shadowOf == "BLK-TEST" for s in shadows)


def _task(world, task_type: TaskType):
    base = world.tasks[0].model_copy(deep=True)
    base.taskType = task_type
    base.taskId = f"T-{task_type.value}"
    base.machineType = base.machineType.NONE
    base.requiresPTW = task_type is TaskType.DEEP_SCREENING
    base.requiresT351 = task_type in (TaskType.SNT_DISCONNECTION, TaskType.SNT_RECONNECTION)
    return base


def test_ballast_cleaning_never_bundles_with_point_machine_work(world):
    a = _task(world, TaskType.DEEP_SCREENING)
    b = _task(world, TaskType.POINT_MACHINE_MAINT)
    verdict, why = pair(a, b)
    assert verdict is Compatibility.INCOMPATIBLE
    assert "vibration" in why


def test_deep_screening_under_live_ohe_is_prohibited(world):
    a = _task(world, TaskType.DEEP_SCREENING)
    a.requiresPTW = False
    b = _task(world, TaskType.TRACK_CIRCUIT_BOND)
    verdict, why = pair(a, b)
    assert verdict is Compatibility.STRICTLY_PROHIBITED
    assert "ACTM 20.3" in why


def test_unknown_pairs_default_to_incompatible(world):
    a = _task(world, TaskType.USFD_INSPECTION)
    b = _task(world, TaskType.INTERLOCKING_WORK)
    verdict, why = pair(a, b)
    assert verdict is Compatibility.INCOMPATIBLE
    assert "defaulting to incompatible" in why


def test_turnout_chain_is_sequentially_compatible(world):
    a = world.task("SNT-2003")
    b = world.task("ENG-1004")
    verdict, _ = pair(a, b)
    assert verdict is Compatibility.SEQUENTIALLY_COMPATIBLE


def test_built_bundles_are_never_incompatible(world):
    for bundle in build_bundles(world, detect(world)):
        tasks = [world.task(t) for t in bundle.taskIds]
        verdict, _ = evaluate(tasks, world)
        assert verdict not in (Compatibility.INCOMPATIBLE, Compatibility.STRICTLY_PROHIBITED)


def test_bundle_rationale_is_never_empty(world):
    for bundle in build_bundles(world, detect(world)):
        assert bundle.rationale
