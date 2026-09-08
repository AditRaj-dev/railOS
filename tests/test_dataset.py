"""The dataset must load, and it must actually contain a plannable problem."""

try:
    import pytest
except ModuleNotFoundError:
    import unittest
    raise unittest.SkipTest("pytest unavailable in stdlib test runtime")

from opportunity_engine import detect
from railos_model import MIN_MACHINE_BLOCK_MINUTES, MaintenanceTask, Track


def test_world_loads(world):
    assert world.tasks and world.trains and world.corridors and world.resources


def test_every_task_sits_on_a_real_section(world):
    sections = {s.sectionId for c in world.corridors for s in c.sections}
    assert {t.sectionId for t in world.tasks} <= sections


def test_statutory_machine_minimum_is_enforced_at_the_model_boundary(world):
    sample = world.tasks[0].model_dump()
    sample.update(taskId="BAD-1", machineType="CSM", estimatedDuration=90)
    with pytest.raises(ValueError, match="HC-002"):
        MaintenanceTask.model_validate(sample)


def test_machine_tasks_respect_their_minimum_duration(world):
    for t in world.tasks:
        assert t.estimatedDuration >= MIN_MACHINE_BLOCK_MINUTES[t.machineType]


def test_a_feasible_maintenance_window_exists(world):
    opportunities = detect(world)
    assert opportunities, "no traffic-free window: the dataset is unplannable"
    assert max(o.minutes for o in opportunities) >= 240


def test_dependencies_reference_known_tasks(world):
    ids = {t.taskId for t in world.tasks}
    for d in world.dependencies:
        assert d.predecessorTaskId in ids and d.successorTaskId in ids


def test_night_window_is_traffic_free(world):
    """The 01:10-04:00 band is where corridor blocks live. If a change to the
    timetable fills it in, the demo silently loses its headroom -- fail loudly."""
    windows = [
        o
        for o in detect(world)
        if o.track == Track.UP and o.start < 240 and o.minutes >= 150
    ]
    assert windows
