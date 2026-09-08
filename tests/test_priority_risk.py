"""Priority and risk are deterministic, decomposable and monotonic."""

from railos_model import Severity
from risk_engine import assess, score_all, score_task
from risk_engine.priority import _band
from risk_engine.config import load_weights


def test_factors_sum_to_the_score(world):
    for result in score_all(world).values():
        assert abs(sum(f.contribution for f in result.factors) - result.score) < 1e-6


def test_weights_are_visible_on_every_factor(world):
    for result in score_all(world).values():
        assert all(f.weight > 0 for f in result.factors)


def test_more_overdue_never_lowers_priority(world):
    task = world.tasks[0].model_copy(deep=True)
    previous = -1.0
    for days in (0, 5, 20, 60, 120):
        task.overdueDays = days
        score = score_task(task, world).score
        assert score >= previous
        previous = score


def test_higher_severity_never_lowers_priority(world):
    task = world.tasks[0].model_copy(deep=True)
    previous = -1.0
    for severity in range(1, 11):
        task.severity = severity
        score = score_task(task, world).score
        assert score >= previous
        previous = score


def test_bands_follow_thresholds():
    cfg = load_weights()
    assert _band(95, cfg) == "CRITICAL"
    assert _band(65, cfg) == "HIGH"
    assert _band(45, cfg) == "MEDIUM"
    assert _band(5, cfg) == "LOW"


def test_emergency_is_floored_at_the_top(world):
    task = world.tasks[0].model_copy(deep=True)
    task.isEmergency = True
    result = score_task(task, world)
    assert result.score == 100.0
    assert any(f.name == "emergency_override" for f in result.factors)


def test_imr_deferral_is_capped_by_statute(world):
    task = world.tasks[0].model_copy(deep=True)
    task.taskId = "IMR-TEST"
    task.detectedAtMinute = 100
    task.dueMinute = 99_999
    w = world.model_copy(deep=True)
    w.tasks.append(task)
    w.defects.append(
        w.defects[0].model_copy(
            update={
                "defectId": "D-IMR",
                "taskId": "IMR-TEST",
                "severityCode": Severity.IMR,
                "detectedAtMinute": 100,
            }
        )
    )
    result = assess(task, w)
    assert result.maxDeferralMinutes == 100 + 4320  # HC-011, 72 h from detection
    assert result.trend == "RISING"


def test_risk_is_labelled_as_a_heuristic(world):
    result = assess(world.tasks[0], world)
    assert "not a trained model" in result.basis
