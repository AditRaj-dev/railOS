"""Objective weights and solver settings. No magic numbers in the model."""

import functools
import pathlib

import yaml

from railos_model import ObjectiveProfile

DEFAULT_PATH = pathlib.Path("config") / "objectives.yaml"

# Statutory buffers, in minutes. Each cites the rule it comes from.
PTW_LEAD_IN = 20        # HC-003 ACTM 20603: switching + discharge rod earthing
PTW_HANDBACK = 15       # HC-004 ACTM 20610: men and material clear, rods removed
T351_LEAD_IN = 10       # HC-005 SEM 11.4: Station Master endorsement
CORRESPONDENCE_TEST = 30  # HC-006 post-Balasore safety directive
MACHINE_SPACING_M = 200   # HC-008 IRTMM 3.2.1
IMR_DEADLINE_MINUTES = 4320  # HC-011 IRPWM USFD 6.3: 72 h outer statutory limit
EMERGENCY_TARGET_MINUTES = 240
"""Operational target for emergency work: the next feasible possession, not the
statutory ceiling. A fractured rail is protected immediately and repaired in hours;
72 h is the outer limit for the replacement, not a scheduling goal."""
MAX_BLOCK_MINUTES = 240      # HC-016 Railway Board operating policy
SUNRISE_MINUTE = 360         # HC-015 06:00
SUNSET_MINUTE = 1080         # HC-015 18:00
DEFAULT_HEADWAY = 15         # HC-001 clear headway either side of a charted path
GANG_TRANSIT_PER_SECTION = 45  # HC-013 crude transit matrix: minutes per section hop
PREMIUM_BUFFER_MINUTES = 30    # SO-002: how close to a premium path is uncomfortable
MACHINE_TRANSIT_PER_SECTION = 60
"""HC-012/HC-009: a track machine is a rail vehicle. Moving it between sections
takes a path and time -- the sequence-dependent setup of the RCPSP-SDST."""
CAUTION_ORDER_SPEED_KMPH = 45   # HC-010 IRPWM 806, Form T/409 on the adjacent line
SR_DAY_SPEEDS_KMPH = (20, 45, 75)  # HC-018 IRPWM 308, days 1-3 after the block
MAX_CONCURRENT_SR_KM = 5.0
"""HC-018 consequence: overlapping temporary speed restrictions stack into a
corridor-wide capacity loss that outlives the blocks that caused them. The budget is
a LENGTH, not a task count -- see config/objectives.yaml, which overrides this."""
GRAPH_RECOMPUTE_ITERATIONS = 3
"""Plan -> speed restrictions -> slower timetable -> different windows. Iterate to
a fixed point rather than pretending the timetable is unaffected by the plan."""


@functools.lru_cache(maxsize=8)
def load_objectives(path: str | pathlib.Path = DEFAULT_PATH) -> dict:
    cfg = yaml.safe_load(pathlib.Path(path).read_text(encoding="utf-8"))
    for name, weights in cfg["profiles"].items():
        total = sum(weights.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"profile {name} weights must sum to 1.0, got {total}")
    return cfg


def weights_for(profile: ObjectiveProfile, path=None) -> dict[str, float]:
    cfg = load_objectives(path) if path else load_objectives()
    return cfg["profiles"][profile.value]
