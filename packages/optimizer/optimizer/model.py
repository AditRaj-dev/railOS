"""RailOS Constraint Optimizer -- OR-Tools CP-SAT.

One model, three weight vectors. Hard constraints are never relaxed: if the model
is INFEASIBLE the honest answer is "no feasible plan", not a prettier plan.

Formulation
-----------
Tasks are placed inside *candidate windows* -- maximal traffic-free intervals on a
(section, track) produced by the opportunity engine, so HC-001 holds by
construction and the solver never has to reason about individual train paths.
A window that receives work becomes a block; its span is a decision variable, which
is what HC-003/004/006/016 attach to.

Every objective coefficient is static per (task, window) pair, which is why the
optimizer can hand back an exact contribution breakdown per assignment instead of
asking a language model to guess why it chose something.
"""

import itertools
import time
import uuid
from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from opportunity_engine import free_intervals
from railos_model import (
    Assignment,
    BlockType,
    Department,
    Factor,
    MaintenanceTask,
    ObjectiveProfile,
    Plan,
    PlanMetrics,
    PlanStatus,
    ScenarioWorld,
    ScheduledBlock,
    TaskType,
    Track,
    UnassignedTask,
)
from risk_engine import score_all

from .config import (
    CAUTION_ORDER_SPEED_KMPH,
    CORRESPONDENCE_TEST,
    DEFAULT_HEADWAY,
    EMERGENCY_TARGET_MINUTES,
    GRAPH_RECOMPUTE_ITERATIONS,
    MACHINE_TRANSIT_PER_SECTION,
    MAX_CONCURRENT_SR_KM,
    SR_DAY_SPEEDS_KMPH,
    GANG_TRANSIT_PER_SECTION,
    IMR_DEADLINE_MINUTES,
    MACHINE_SPACING_M,
    MAX_BLOCK_MINUTES,
    PREMIUM_BUFFER_MINUTES,
    PTW_HANDBACK,
    PTW_LEAD_IN,
    SUNRISE_MINUTE,
    SUNSET_MINUTE,
    T351_LEAD_IN,
    load_objectives,
    weights_for,
)


@dataclass(frozen=True)
class Window:
    key: str
    sectionId: str
    track: Track
    start: int
    end: int

    @property
    def minutes(self) -> int:
        return self.end - self.start


@dataclass
class SolveOptions:
    profile: ObjectiveProfile = ObjectiveProfile.BALANCED
    headway: int = DEFAULT_HEADWAY
    max_time_seconds: float | None = None
    locked_starts: dict[str, int] = field(default_factory=dict)
    """taskId -> fixed start minute. Started or already-approved work cannot move."""
    reference_starts: dict[str, int] = field(default_factory=dict)
    """taskId -> start in the plan we are revising. Drives the churn penalty."""
    churn_weight: float = 0.0
    horizon_lock_before: int = 0
    """Nothing may be scheduled before this minute (the past is not re-plannable)."""


# --------------------------------------------------------------------------
# window construction


def build_windows(world: ScenarioWorld, headway: int) -> list[Window]:
    out: list[Window] = []
    for corridor in world.corridors:
        for section in corridor.sections:
            for track in section.tracks:
                for n, (start, end) in enumerate(
                    free_intervals(world, section.sectionId, track, headway)
                ):
                    out.append(
                        Window(
                            key=f"W:{section.sectionId}:{track.value}:{n}",
                            sectionId=section.sectionId,
                            track=track,
                            start=start,
                            end=end,
                        )
                    )
    return out


def required_span(task: MaintenanceTask) -> int:
    """Minutes of possession this task consumes, statutory buffers included.

    The work is not the block: a power block also pays 20 minutes of switching and
    earthing (HC-003) and 15 minutes of handback (HC-004) before it can be cleared.
    """
    span = task.estimatedDuration
    if task.requiresPTW:
        span += PTW_LEAD_IN + PTW_HANDBACK
    if task.requiresT351:
        span += T351_LEAD_IN
    if task.requiresCorrespondenceTest:
        span += CORRESPONDENCE_TEST
    return span


def _daylight_clip(task: MaintenanceTask, w: Window) -> tuple[int, int] | None:
    """HC-015: work without mobile lighting happens between sunrise and sunset."""
    if task.hasMobileLighting:
        return w.start, w.end
    best: tuple[int, int] | None = None
    day = w.start // 1440
    while day * 1440 <= w.end:
        lo = max(w.start, day * 1440 + SUNRISE_MINUTE)
        hi = min(w.end, day * 1440 + SUNSET_MINUTE)
        if hi - lo >= task.estimatedDuration and (best is None or hi - lo > best[1] - best[0]):
            best = (lo, hi)
        day += 1
    return best


def eligible_windows(task: MaintenanceTask, windows: list[Window], opts: SolveOptions):
    """(window, earliest_start, latest_end) triples this task may legally occupy."""
    out = []
    for w in windows:
        if w.sectionId != task.sectionId or w.track != task.track:
            continue
        clip = _daylight_clip(task, w)
        if clip is None:
            continue
        lo, hi = clip
        if task.taskId not in opts.locked_starts:
            # Work already under way keeps its published time; only free work is
            # pushed past the replanning boundary.
            lo = max(lo, opts.horizon_lock_before)
        # Statutory buffers consume block time at both ends.
        if task.requiresPTW:
            lo += PTW_LEAD_IN                     # HC-003
            hi -= PTW_HANDBACK                    # HC-004
        if task.requiresT351:
            lo += T351_LEAD_IN                    # HC-005
        if task.requiresCorrespondenceTest:
            hi -= CORRESPONDENCE_TEST             # HC-006
        if hi - lo < task.estimatedDuration:
            continue
        out.append((w, lo, hi))
    return out


# --------------------------------------------------------------------------
# objective coefficients (static per task/window pair -> explainable)


def _class_weights(cfg: dict) -> dict[str, int]:
    return cfg["train_class_weight"]


def traffic_pressure(world: ScenarioWorld, w: Window, cfg: dict) -> int:
    """SO-002 proxy. Planned passenger delay is zero (HC-001 is hard), so what we
    price here is *proximity*: work butted against a premium path is one late
    handback away from regulating a Rajdhani."""
    cw = _class_weights(cfg)
    total = 0
    for t in world.trains:
        if t.sectionId != w.sectionId or t.track != w.track:
            continue
        gap = min(abs(t.entry - w.end), abs(w.start - t.exit))
        if gap <= PREMIUM_BUFFER_MINUTES:
            total += cw.get(t.trainClass.value, 10)
    return total


def freight_pressure(world: ScenarioWorld, w: Window) -> int:
    """SO-004. Freight paths are probabilistic; detention is priced by expectation."""
    total = 0.0
    for g in world.goods:
        if g.sectionId != w.sectionId or g.track != w.track:
            continue
        overlap = min(w.end, g.windowEnd) - max(w.start, g.windowStart)
        if overlap > 0:
            total += overlap * g.probability * g.priorityWeight
    return int(total)


def overrun_penalty(task: MaintenanceTask, w: Window) -> int:
    """SO-005. A block with less than two standard deviations of slack bursts."""
    slack = w.minutes - task.estimatedDuration
    needed = 2 * task.durationStdDev
    return max(0, needed - slack)


def caution_delay_cost(world: ScenarioWorld, task: MaintenanceTask, w: Window, cfg: dict) -> int:
    """HC-010 / HC-012 priced: the caution order this task imposes on the adjacent
    line, in class-weighted minutes of delay to the trains that actually run there.

    Static per (task, window), so it can sit in the objective and still be explained
    exactly afterwards.
    """
    if not (task.infringesAdjacent or task.machineType.value == "TOWER_WAGON"):
        return 0
    from .traingraph import delay_minutes, worked_km

    other = Track.DOWN if task.track is Track.UP else Track.UP
    per_train = delay_minutes(
        world, task.sectionId, CAUTION_ORDER_SPEED_KMPH, worked_km(task)
    )
    cw = _class_weights(cfg)
    total = 0
    for t in world.trains:
        if t.sectionId != task.sectionId or t.track != other:
            continue
        if t.entry < w.end and w.start < t.exit:
            total += per_train * cw.get(t.trainClass.value, 10) // 10
    return total


def sr_delay_cost(world: ScenarioWorld, task: MaintenanceTask, w: Window, cfg: dict) -> int:
    """HC-018 priced: every train crossing this section for the three days after the
    block runs slower. This is the bill the plan leaves behind."""
    if not task.imposesSpeedRestriction:
        return 0
    from .traingraph import delay_minutes, worked_km

    cw = _class_weights(cfg)
    # The SR starts when the work ends; before the solver picks a start time the
    # window start is the available proxy, and it is the conservative one.
    total = 0
    for day, speed in enumerate(SR_DAY_SPEEDS_KMPH):
        lo = w.start + day * 1440
        hi = lo + 1440
        per_train = delay_minutes(world, task.sectionId, speed, worked_km(task))
        for t in world.trains:
            if t.sectionId != task.sectionId or t.track != task.track:
                continue
            if lo <= t.entry < hi:
                total += per_train * cw.get(t.trainClass.value, 10) // 10
    return total


def sr_footprint(task: MaintenanceTask) -> int:
    """SO-007. km x days of temporary speed restriction created by this work
    (HC-018: 20 / 45 / 75 kmph on days 1-3, so three restricted days)."""
    if not task.imposesSpeedRestriction:
        return 0
    length_km = max(1, int(round((task.kmEnd - task.kmStart))))
    return length_km * 3


# --------------------------------------------------------------------------


def solve(
    world: ScenarioWorld,
    opts: SolveOptions | None = None,
    config_path=None,
    converge: bool = True,
) -> Plan:
    """Produce a plan that survives its own consequences.

    A single CP-SAT pass plans against the timetable as charted. But the plan itself
    imposes caution orders (HC-010/HC-012) and speed restrictions (HC-018), and under
    those the trains run slower -- which can push a path straight into a possession
    the same plan just booked. So: solve, recompute the graph, solve again, until the
    schedule stops colliding with the timetable it creates.

    `converge=False` gives the single undisturbed pass, which is what the recompute
    itself needs and what tests use to demonstrate the difference.
    """
    plan, _ = solve_converged(world, opts, config_path) if converge else (
        _solve_once(world, opts, config_path),
        world,
    )
    return plan


def _solve_once(world: ScenarioWorld, opts: SolveOptions | None = None, config_path=None) -> Plan:
    opts = opts or SolveOptions()
    cfg = load_objectives(config_path) if config_path else load_objectives()
    w_obj = weights_for(opts.profile, config_path)
    scale = cfg["solver"]["scale"]
    priorities = {k: v.score for k, v in score_all(world).items()}

    model = cp_model.CpModel()
    H = world.horizonMinutes
    windows = build_windows(world, opts.headway)
    by_key = {w.key: w for w in windows}

    present: dict[str, cp_model.IntVar] = {}
    start: dict[str, cp_model.IntVar] = {}
    end: dict[str, cp_model.IntVar] = {}
    interval: dict[str, cp_model.IntervalVar] = {}
    assign: dict[tuple[str, str], cp_model.IntVar] = {}
    eligible: dict[str, list] = {}
    unassignable: list[UnassignedTask] = []

    for task in world.tasks:
        elig = eligible_windows(task, windows, opts)
        eligible[task.taskId] = elig
        p = model.NewBoolVar(f"present[{task.taskId}]")
        s = model.NewIntVar(0, H, f"start[{task.taskId}]")
        e = model.NewIntVar(0, H, f"end[{task.taskId}]")
        present[task.taskId], start[task.taskId], end[task.taskId] = p, s, e
        interval[task.taskId] = model.NewOptionalIntervalVar(
            s, task.estimatedDuration, e, p, f"iv[{task.taskId}]"
        )
        if not elig:
            model.Add(p == 0)
            unassignable.append(
                UnassignedTask(
                    taskId=task.taskId,
                    reason="no traffic-free window on this section and track can hold the task "
                    "once statutory buffers are applied (HC-001 with HC-003/004/005/006/015)",
                )
            )
            continue
        lits = []
        for w, lo, hi in elig:
            a = model.NewBoolVar(f"a[{task.taskId},{w.key}]")
            assign[(task.taskId, w.key)] = a
            model.Add(s >= lo).OnlyEnforceIf(a)
            model.Add(e <= hi).OnlyEnforceIf(a)
            lits.append(a)
        model.Add(sum(lits) == 1).OnlyEnforceIf(p)
        model.Add(sum(lits) == 0).OnlyEnforceIf(p.Not())

        # HC-011: an IMR rail flaw is not optional and has a statutory clock.
        if task.isEmergency:
            model.Add(p == 1)
            if task.detectedAtMinute is not None:
                detected = task.detectedAtMinute
                feasible = [lo for _w, lo, _hi in elig if lo >= detected]
                target = detected + EMERGENCY_TARGET_MINUTES
                # The next feasible possession, or the operational target, whichever
                # is later -- but never beyond the statutory 72 h (HC-011).
                bound = min(
                    detected + IMR_DEADLINE_MINUTES,
                    max(target, min(feasible)) if feasible else detected + IMR_DEADLINE_MINUTES,
                )
                model.Add(s <= bound)

        # Replanning: locked work does not move.
        if task.taskId in opts.locked_starts:
            model.Add(p == 1)
            model.Add(s == opts.locked_starts[task.taskId])

    # ---- block span variables (a used window becomes a block) --------------
    bstart: dict[str, cp_model.IntVar] = {}
    bend: dict[str, cp_model.IntVar] = {}
    used: dict[str, cp_model.IntVar] = {}
    for w in windows:
        members = [(t, a) for (tid, k), a in assign.items() if k == w.key for t in [tid]]
        if not members:
            continue
        bs = model.NewIntVar(w.start, w.end, f"bstart[{w.key}]")
        be = model.NewIntVar(w.start, w.end, f"bend[{w.key}]")
        u = model.NewBoolVar(f"used[{w.key}]")
        bstart[w.key], bend[w.key], used[w.key] = bs, be, u
        s_eff, e_eff, span_eff = [], [], []
        for tid, a in members:
            task = world.task(tid)
            # The possession starts before the work does and ends after it: switching
            # and earthing (HC-003), T/351 endorsement (HC-005), handback (HC-004)
            # and correspondence testing (HC-006) are all block time.
            lead = (PTW_LEAD_IN if task.requiresPTW else 0) + (
                T351_LEAD_IN if task.requiresT351 else 0
            )
            trail = (PTW_HANDBACK if task.requiresPTW else 0) + (
                CORRESPONDENCE_TEST if task.requiresCorrespondenceTest else 0
            )
            se = model.NewIntVar(w.start, w.end, f"seff[{tid},{w.key}]")
            ee = model.NewIntVar(w.start, w.end, f"eeff[{tid},{w.key}]")
            model.Add(se == start[tid] - lead).OnlyEnforceIf(a)
            model.Add(se == w.end).OnlyEnforceIf(a.Not())
            model.Add(ee == end[tid] + trail).OnlyEnforceIf(a)
            model.Add(ee == w.start).OnlyEnforceIf(a.Not())
            # HC-016 cap depends on which tasks actually land here, not on which
            # ones could have: a mega-block allowance follows the mega work.
            span = model.NewIntVar(MAX_BLOCK_MINUTES, max(MAX_BLOCK_MINUTES, required_span(task)),
                                   f"span[{tid},{w.key}]")
            model.Add(span == max(MAX_BLOCK_MINUTES, required_span(task))).OnlyEnforceIf(a)
            model.Add(span == MAX_BLOCK_MINUTES).OnlyEnforceIf(a.Not())
            s_eff.append(se)
            e_eff.append(ee)
            span_eff.append(span)
            model.AddImplication(a, u)
        model.AddMinEquality(bs, s_eff)
        model.AddMaxEquality(be, e_eff)
        model.Add(sum(a for _t, a in members) >= 1).OnlyEnforceIf(u)
        # HC-016: no continuous weekday possession beyond 4 h, unless the work
        # itself is a mega-block activity (a BCM deep screening cannot be shorter,
        # and its statutory buffers are part of the possession).
        cap = model.NewIntVar(
            MAX_BLOCK_MINUTES,
            max([MAX_BLOCK_MINUTES] + [required_span(world.task(t)) for t, _a in members]),
            f"cap[{w.key}]",
        )
        model.AddMaxEquality(cap, span_eff)
        model.Add(be - bs <= cap).OnlyEnforceIf(u)

    # ---- HC-007 dependencies ---------------------------------------------
    for dep in world.dependencies:
        a, b = dep.predecessorTaskId, dep.successorTaskId
        if a not in present or b not in present:
            continue
        model.Add(end[a] + dep.lagMinutes <= start[b]).OnlyEnforceIf(
            [present[a], present[b]]
        )
        # A sequenced chain is all-or-nothing: you cannot leave a point disconnected.
        model.Add(present[a] == present[b])

    # ---- HC-009 machine occupancy, HC-013 gang transit --------------------
    section_index = {
        s.sectionId: i for c in world.corridors for i, s in enumerate(c.sections)
    }
    by_resource: dict[str, list[str]] = {}
    for task in world.tasks:
        for r in task.resourceIds:
            by_resource.setdefault(r, []).append(task.taskId)
    for _r, tids in by_resource.items():
        if len(tids) < 2:
            continue
        model.AddNoOverlap([interval[t] for t in tids])
        # A track machine is a rail vehicle: it needs a path and time to reach the
        # next site. This is the sequence-dependent setup of the problem, and without
        # it a tamper teleports between sections.
        for i, j in itertools.combinations(tids, 2):
            ti, tj = world.task(i), world.task(j)
            hops = abs(section_index.get(ti.sectionId, 0) - section_index.get(tj.sectionId, 0))
            if not hops:
                continue
            transit = hops * MACHINE_TRANSIT_PER_SECTION
            before = model.NewBoolVar(f"machine_move[{i},{j}]")
            model.Add(start[j] >= end[i] + transit).OnlyEnforceIf(
                [before, present[i], present[j]]
            )
            model.Add(start[i] >= end[j] + transit).OnlyEnforceIf(
                [before.Not(), present[i], present[j]]
            )

    by_gang: dict[str, list[str]] = {}
    for task in world.tasks:
        if task.gangId:
            by_gang.setdefault(task.gangId, []).append(task.taskId)
    for _g, tids in by_gang.items():
        for i, j in itertools.combinations(tids, 2):
            ti, tj = world.task(i), world.task(j)
            hops = abs(section_index.get(ti.sectionId, 0) - section_index.get(tj.sectionId, 0))
            transit = hops * GANG_TRANSIT_PER_SECTION
            before = model.NewBoolVar(f"gang_order[{i},{j}]")
            model.Add(start[j] >= end[i] + transit).OnlyEnforceIf(
                [before, present[i], present[j]]
            )
            model.Add(start[i] >= end[j] + transit).OnlyEnforceIf(
                [before.Not(), present[i], present[j]]
            )

    # ---- HC-010 / HC-012 adjacent line ------------------------------------
    # Machine work that infringes the adjacent line, and a tower wagon whose boom and
    # wire spans reach across it, put men and steel inside the adjacent line's
    # infringement envelope. Trains there run under caution (priced in the objective);
    # maintenance there at the same time is not permitted at all.
    for ti in world.tasks:
        wagon = ti.machineType.value == "TOWER_WAGON"
        if not (ti.infringesAdjacent or wagon):
            continue
        for tj in world.tasks:
            if tj.taskId == ti.taskId or tj.sectionId != ti.sectionId:
                continue
            if tj.track == ti.track:
                continue
            code = "HC-012" if wagon else "HC-010"
            before = model.NewBoolVar(f"adjacent[{code},{ti.taskId},{tj.taskId}]")
            model.Add(start[tj.taskId] >= end[ti.taskId]).OnlyEnforceIf(
                [before, present[ti.taskId], present[tj.taskId]]
            )
            model.Add(start[ti.taskId] >= end[tj.taskId]).OnlyEnforceIf(
                [before.Not(), present[ti.taskId], present[tj.taskId]]
            )

    # ---- HC-018 concurrent speed restrictions -----------------------------
    # Each SR-imposing task leaves its section restricted for three days. Let those
    # windows stack without limit and the corridor quietly loses capacity for a week
    # after every block is cleared.
    from .traingraph import worked_km

    sr_tasks = [t for t in world.tasks if t.imposesSpeedRestriction]
    budget_dm = int(
        round(cfg.get("speed_restriction", {}).get("max_concurrent_km", MAX_CONCURRENT_SR_KM) * 10)
    )
    demands = [max(1, int(round(worked_km(t) * 10))) for t in sr_tasks]
    if sum(demands) > budget_dm:
        # The budget rations the SEVERE period only -- day 1 at 20 kmph. Days 2 and 3
        # (45 / 75 kmph) still cost, and are priced in the objective, but they do not
        # occupy the corridor's restriction budget.
        severe = 1440
        sr_intervals = []
        for t in sr_tasks:
            sr_end = model.NewIntVar(0, H + severe, f"srend[{t.taskId}]")
            model.Add(sr_end == end[t.taskId] + severe)
            sr_intervals.append(
                model.NewOptionalIntervalVar(
                    end[t.taskId], severe, sr_end, present[t.taskId], f"sr[{t.taskId}]"
                )
            )
        # Decimetre units keep the cumulative integral without losing 100 m of
        # resolution on a short turnout.
        model.AddCumulative(sr_intervals, demands, budget_dm)

    # ---- HC-008 machine spacing ------------------------------------------
    machine_tasks = [t for t in world.tasks if t.machineType.value != "NONE"]
    for ti, tj in itertools.combinations(machine_tasks, 2):
        if ti.sectionId != tj.sectionId or ti.track != tj.track:
            continue
        if abs(ti.locationM - tj.locationM) >= MACHINE_SPACING_M:
            continue
        # Too close to work side by side: they must not overlap in time.
        before = model.NewBoolVar(f"spacing[{ti.taskId},{tj.taskId}]")
        model.Add(start[tj.taskId] >= end[ti.taskId]).OnlyEnforceIf(
            [before, present[ti.taskId], present[tj.taskId]]
        )
        model.Add(start[ti.taskId] >= end[tj.taskId]).OnlyEnforceIf(
            [before.Not(), present[ti.taskId], present[tj.taskId]]
        )

    # ---- HC-017 S&T escort ------------------------------------------------
    escorts = [r.resourceId for r in world.resources if r.resourceType == "ESCORT"]
    escorted = [t.taskId for t in world.tasks if t.requiresSntEscort]
    if escorted and escorts:
        # One escort: escorted works cannot overlap each other.
        model.AddNoOverlap([interval[t] for t in escorted])
    elif escorted and not escorts:
        for t in escorted:
            model.Add(present[t] == 0)

    # ---- objective --------------------------------------------------------
    terms: list[tuple[str, int, cp_model.IntVar]] = []
    coeff_detail: dict[str, dict[str, int]] = {}

    def add(name: str, coeff: float, var) -> None:
        c = int(round(coeff))
        if c:
            terms.append((name, c, var))

    for task in world.tasks:
        tid = task.taskId
        p = present[tid]
        prio = priorities[tid]
        add(
            "yield",
            w_obj["yield"] * scale * prio * task.estimatedDuration / 100.0,
            p,
        )  # SO-001
        add(
            "machine_use",
            w_obj["machine_use"] * scale * (task.estimatedDuration if task.machineType.value != "NONE" else 0),
            p,
        )  # SO-008
        add("sr_footprint", -w_obj["sr_footprint"] * scale * sr_footprint(task), p)  # SO-007
        # SO-006: debt is paid by NOT doing the work, so it loads the absent literal.
        debt = task.overdueDays * task.criticality
        add("deferral_debt", -w_obj["deferral_debt"] * scale * debt, p.Not())

        for w, _lo, _hi in eligible[tid]:
            a = assign[(tid, w.key)]
            tp = traffic_pressure(world, w, cfg)
            fp = freight_pressure(world, w)
            op_ = overrun_penalty(task, w)
            cd = caution_delay_cost(world, task, w, cfg)   # HC-010 / HC-012
            sd = sr_delay_cost(world, task, w, cfg)        # HC-018
            coeff_detail[f"{tid}@{w.key}"] = {
                "traffic_pressure": tp,
                "freight_pressure": fp,
                "overrun_penalty": op_,
                "caution_delay": cd,
                "sr_delay": sd,
            }
            add("passenger_delay", -w_obj["passenger_delay"] * scale * tp, a)      # SO-002
            add("freight_detention", -w_obj["freight_detention"] * scale * fp, a)  # SO-004
            add("overrun_risk", -w_obj["overrun_risk"] * scale * op_, a)           # SO-005
            # HC-010 / HC-012 / HC-018 are obligations the plan creates. They are
            # priced through SO-002 (delay to trains) and SO-007 (restriction
            # footprint) so the optimizer pays for them instead of noting them.
            add("caution_order_delay", -w_obj["passenger_delay"] * scale * cd, a)
            add("speed_restriction_delay", -w_obj["sr_footprint"] * scale * sd, a)

    # SO-003: cross-department pairs sharing a block.
    bundle_lits: list[cp_model.IntVar] = []
    for ti, tj in itertools.combinations(world.tasks, 2):
        if ti.department == tj.department or ti.sectionId != tj.sectionId or ti.track != tj.track:
            continue
        for w, _lo, _hi in eligible[ti.taskId]:
            key = (tj.taskId, w.key)
            if key not in assign:
                continue
            both = model.NewBoolVar(f"bundle[{ti.taskId},{tj.taskId},{w.key}]")
            model.AddBoolAnd([assign[(ti.taskId, w.key)], assign[key]]).OnlyEnforceIf(both)
            model.AddBoolOr(
                [assign[(ti.taskId, w.key)].Not(), assign[key].Not(), both]
            )
            bundle_lits.append(both)
            add("bundling", w_obj["bundling"] * scale * 60, both)

    # Replanning churn: moving work that was already published has a cost.
    if opts.churn_weight and opts.reference_starts:
        for tid, ref in opts.reference_starts.items():
            if tid not in start:
                continue
            dev = model.NewIntVar(0, H, f"churn[{tid}]")
            model.AddAbsEquality(dev, start[tid] - ref)
            add("churn", -opts.churn_weight * scale, dev)

    model.Maximize(sum(c * v for _n, c, v in terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = (
        opts.max_time_seconds or cfg["solver"]["max_time_seconds"]
    )
    solver.parameters.num_search_workers = cfg["solver"]["num_workers"]
    solver.parameters.random_seed = cfg["solver"]["random_seed"]
    t0 = time.perf_counter()
    status = solver.Solve(model)
    wall = time.perf_counter() - t0
    status_name = solver.StatusName(status)

    plan = Plan(
        planId=f"PLAN-{uuid.uuid4().hex[:8].upper()}",
        planVersion=1,
        status=PlanStatus.GENERATED,
        objectiveProfile=opts.profile,
        horizonMinutes=H,
        solverStatus=status_name,
        runtime={
            "wallSeconds": round(wall, 3),
            "branches": solver.NumBranches(),
            "conflicts": solver.NumConflicts(),
            "solver": "OR-Tools CP-SAT",
        },
        provenance="synthetic dataset; deterministic scoring; no ML in the loop",
    )
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        plan.unassigned = [
            UnassignedTask(taskId=t.taskId, reason=f"model {status_name}") for t in world.tasks
        ]
        plan.warnings.append(
            "No feasible plan under the current hard constraints. Constraints were not "
            "relaxed; review demand, windows or resources."
        )
        return plan

    # ---- read the solution ------------------------------------------------
    chosen: dict[str, str] = {}
    for (tid, key), a in assign.items():
        if solver.Value(a):
            chosen[tid] = key

    blocks: list[ScheduledBlock] = []
    for key, u in used.items():
        if not solver.Value(u):
            continue
        members = [t for t, k in chosen.items() if k == key]
        if not members:
            continue
        w = by_key[key]
        member_tasks = [world.task(t) for t in members]
        blocks.append(
            ScheduledBlock(
                blockId=f"BLK-{key.split(':')[1][-6:]}-{solver.Value(bstart[key]):05d}",
                sectionId=w.sectionId,
                track=w.track,
                blockType=_block_type(member_tasks),
                start=solver.Value(bstart[key]),
                end=solver.Value(bend[key]),
                taskIds=sorted(members),
                departments=sorted({t.department for t in member_tasks}),
                opportunityId=key,
            )
        )
    blocks.sort(key=lambda b: (b.start, b.sectionId))
    block_of = {t: b.blockId for b in blocks for t in b.taskIds}

    for tid, key in sorted(chosen.items()):
        task = world.task(tid)
        detail = coeff_detail[f"{tid}@{key}"]
        plan.assignments.append(
            Assignment(
                taskId=tid,
                blockId=block_of[tid],
                start=solver.Value(start[tid]),
                end=solver.Value(end[tid]),
                explanation=_explain(task, priorities[tid], detail, w_obj, scale, blocks, block_of),
            )
        )
    plan.blocks = blocks
    chained: dict[str, set[str]] = {}
    for dep in world.dependencies:
        chained.setdefault(dep.predecessorTaskId, set()).add(dep.successorTaskId)
        chained.setdefault(dep.successorTaskId, set()).add(dep.predecessorTaskId)
    blocked = {u.taskId for u in unassignable}
    for t in world.tasks:
        if t.taskId in chosen or t.taskId in blocked:
            continue
        partners = sorted(chained.get(t.taskId, ()))
        if partners:
            reason = (
                "deferred as part of a sequenced chain -- HC-007 work is all-or-nothing, "
                f"so this moves only together with {', '.join(partners)}"
            )
        else:
            reason = (
                "deferred by the optimizer: the objective was better served by other work "
                "in the available windows"
            )
        unassignable.append(UnassignedTask(taskId=t.taskId, reason=reason))
    plan.unassigned = unassignable
    plan.objectiveBreakdown = _breakdown(terms, solver)
    from .traingraph import disruption

    consequences = disruption(world, plan, cfg["train_class_weight"])
    plan.metrics = _metrics(world, plan, priorities, consequences["trainDisruptionMinutes"])
    plan.runtime["weightedDisruption"] = consequences["weightedDisruption"]
    plan.runtime["premiumDelayMinutes"] = consequences["premiumMinutes"]
    plan.warnings = _warnings(world, plan)
    return plan


def solve_converged(
    world: ScenarioWorld,
    opts: SolveOptions | None = None,
    config_path=None,
    max_iterations: int = GRAPH_RECOMPUTE_ITERATIONS,
) -> tuple[Plan, ScenarioWorld]:
    """Solve against the timetable the plan itself creates.

    A block is not free of consequences: HC-010 puts the adjacent line under caution
    and HC-018 leaves the worked line restricted for three days, so trains run slower
    afterwards, so the traffic-free windows move. Planning against the *undisturbed*
    timetable quietly assumes the plan changes nothing.

    So: solve, recompute the graph, and solve again against it until the schedule
    stops moving. Returns the plan and the timetable it will actually run under.
    """
    from .audit import audit
    from .traingraph import recompute

    current = world
    plan = _solve_once(current, opts, config_path)
    plan.runtime["graphIterations"] = 1
    for iteration in range(max_iterations - 1):
        if plan.solverStatus not in ("OPTIMAL", "FEASIBLE"):
            break
        conflicts = [v for v in audit(world, plan) if v.code == "HC-001/RECOMPUTE"]
        if not conflicts:
            break
        after = recompute(world, plan)
        candidate = _solve_once(after, opts, config_path)
        if candidate.solverStatus not in ("OPTIMAL", "FEASIBLE"):
            plan.warnings.append(
                "The speed restrictions this plan creates close the windows it relies "
                "on, and no revised plan is feasible. Returning the undisturbed "
                "solution with its conflicts listed -- this needs a human decision."
            )
            break
        plan, current = candidate, after
        plan.runtime["graphIterations"] = iteration + 2
    remaining = [v for v in audit(world, plan) if v.code == "HC-001/RECOMPUTE"]
    if remaining:
        plan.warnings.append(
            f"{len(remaining)} maintenance windows still collide with the timetable "
            f"once this plan's own restrictions are applied, after "
            f"{plan.runtime['graphIterations']} recompute passes."
        )
    return plan, current


def _block_type(tasks: list[MaintenanceTask]) -> BlockType:
    departments = {t.department for t in tasks}
    needs_power = any(t.requiresPTW for t in tasks)
    if any(t.isEmergency for t in tasks):
        return BlockType.EMERGENCY
    if len(departments) > 1:
        return BlockType.INTEGRATED
    if departments == {Department.TRD} and needs_power:
        return BlockType.POWER
    if needs_power:
        return BlockType.INTEGRATED
    if departments == {Department.SNT} and all(t.requiresT351 for t in tasks):
        return BlockType.DISCONNECTION
    return BlockType.TRAFFIC


def _explain(task, priority, detail, w_obj, scale, blocks, block_of) -> list[Factor]:
    """The optimizer states its own reasons. A language model may read these numbers
    out loud; it does not invent them."""
    block = next(b for b in blocks if b.blockId == block_of[task.taskId])
    partners = [t for t in block.taskIds if t != task.taskId]
    return [
        Factor(
            name="priority_contribution",
            raw=priority,
            weight=w_obj["yield"],
            contribution=round(w_obj["yield"] * scale * priority * task.estimatedDuration / 100.0, 2),
            note="SO-001 critical maintenance yield",
        ),
        Factor(
            name="urgency_contribution",
            raw=float(task.overdueDays * task.criticality),
            weight=w_obj["deferral_debt"],
            contribution=round(w_obj["deferral_debt"] * scale * task.overdueDays * task.criticality, 2),
            note="SO-006 debt avoided by scheduling rather than deferring",
        ),
        Factor(
            name="bundling_benefit",
            raw=float(len(partners)),
            weight=w_obj["bundling"],
            contribution=round(w_obj["bundling"] * scale * 60 * len(partners), 2),
            note=f"SO-003 shares block {block.blockId} with {partners or 'no other task'}",
        ),
        Factor(
            name="traffic_penalty",
            raw=float(detail["traffic_pressure"]),
            weight=w_obj["passenger_delay"],
            contribution=-round(w_obj["passenger_delay"] * scale * detail["traffic_pressure"], 2),
            note="SO-002 weighted train paths within the buffer of this window",
        ),
        Factor(
            name="freight_penalty",
            raw=float(detail["freight_pressure"]),
            weight=w_obj["freight_detention"],
            contribution=-round(w_obj["freight_detention"] * scale * detail["freight_pressure"], 2),
            note="SO-004 expected freight detention",
        ),
        Factor(
            name="caution_order_penalty",
            raw=float(detail["caution_delay"]),
            weight=w_obj["passenger_delay"],
            contribution=-round(w_obj["passenger_delay"] * scale * detail["caution_delay"], 2),
            note="HC-010/HC-012 Form T/409 caution order on the adjacent line, "
            "in class-weighted delay minutes",
        ),
        Factor(
            name="speed_restriction_penalty",
            raw=float(detail["sr_delay"]),
            weight=w_obj["sr_footprint"],
            contribution=-round(w_obj["sr_footprint"] * scale * detail["sr_delay"], 2),
            note="HC-018 temporary SR after the block, in class-weighted delay minutes "
            "over the following three days",
        ),
        Factor(
            name="unused_window_penalty",
            raw=float(detail["overrun_penalty"]),
            weight=w_obj["overrun_risk"],
            contribution=-round(w_obj["overrun_risk"] * scale * detail["overrun_penalty"], 2),
            note="SO-005 shortfall against a 2-sigma block-burst buffer",
        ),
        Factor(
            name="risk_reduction",
            raw=priority,
            weight=1.0,
            contribution=round(priority, 2),
            note="priority score removed from the outstanding risk pool once completed",
        ),
    ]


def _breakdown(terms, solver) -> dict[str, float]:
    out: dict[str, float] = {}
    for name, coeff, var in terms:
        out[name] = out.get(name, 0.0) + coeff * solver.Value(var)
    out["TOTAL"] = sum(out.values())
    return {k: round(v, 2) for k, v in out.items()}


def _union_minutes(spans: list[tuple[int, int]]) -> int:
    total, cursor = 0, -1
    for start, end in sorted(spans):
        lo = max(start, cursor)
        if end > lo:
            total += end - lo
            cursor = end
    return total


def _metrics(
    world: ScenarioWorld, plan: Plan, priorities: dict[str, float], disruption_minutes: int = 0
) -> PlanMetrics:
    block_minutes = sum(b.end - b.start for b in plan.blocks) or 1
    # Useful maintenance time is the UNION of task intervals inside a block:
    # two gangs working side by side do not make a block 200% utilised.
    by_block: dict[str, list[tuple[int, int]]] = {}
    for a in plan.assignments:
        by_block.setdefault(a.blockId, []).append((a.start, a.end))
    work_minutes = sum(_union_minutes(v) for v in by_block.values())
    weighted_work = sum(
        priorities[a.taskId] * (a.end - a.start) / 100.0 for a in plan.assignments
    )
    debt = sum(
        t.overdueDays * t.criticality * priorities[t.taskId] / 100.0
        for t in world.tasks
        if any(u.taskId == t.taskId for u in plan.unassigned)
    )
    multi = sum(1 for b in plan.blocks if len(b.departments) > 1)
    critical = [t for t in world.tasks if priorities[t.taskId] >= 70]
    critical_done = [t for t in critical if any(a.taskId == t.taskId for a in plan.assignments)]
    freight = 0
    for b in plan.blocks:
        for g in world.goods:
            if g.sectionId == b.sectionId and g.track == b.track:
                overlap = min(b.end, g.windowEnd) - max(b.start, g.windowStart)
                if overlap > 0:
                    freight += int(overlap * g.probability)
    return PlanMetrics(
        blockUtilisation=round(100.0 * work_minutes / block_minutes, 2),
        maintenanceYield=round(weighted_work / block_minutes, 4),
        maintenanceDebt=round(debt, 2),
        coordinationRatio=round(100.0 * multi / len(plan.blocks), 2) if plan.blocks else 0.0,
        criticalCompletionRate=round(100.0 * len(critical_done) / len(critical), 2)
        if critical
        else 100.0,
        # HC-001 is hard, so no charted path is displaced by a block. What trains do
        # lose is running time under the caution orders and speed restrictions the
        # plan creates -- recomputed from the graph, not assumed to be zero.
        trainDisruptionMinutes=disruption_minutes,
        freightDetentionMinutes=freight,
        tasksScheduled=len(plan.assignments),
        tasksUnassigned=len(plan.unassigned),
        srFootprintKmDays=float(
            sum(sr_footprint(world.task(a.taskId)) for a in plan.assignments)
        ),
    )


def _warnings(world: ScenarioWorld, plan: Plan) -> list[str]:
    """Obligations the plan creates. These are not constraint violations -- they are
    the operational price of the plan, and a controller must see them."""
    out: list[str] = []
    for a in plan.assignments:
        task = world.task(a.taskId)
        if task.infringesAdjacent:
            out.append(
                f"HC-010: {task.taskId} infringes the adjacent line -- Caution Order T/409 "
                f"for trains on the parallel track of {task.sectionId} at "
                f"{CAUTION_ORDER_SPEED_KMPH} kmph; no maintenance may run there "
                f"concurrently"
            )
        if task.imposesSpeedRestriction:
            speeds = " / ".join(str(v) for v in SR_DAY_SPEEDS_KMPH)
            out.append(
                f"HC-018: {task.taskId} leaves {task.sectionId} {task.track.value} under a "
                f"temporary speed restriction from minute {a.end} -- {speeds} kmph over "
                f"the following {len(SR_DAY_SPEEDS_KMPH)} days"
            )
        if task.machineType.value == "TOWER_WAGON":
            out.append(
                f"HC-012: tower wagon on {task.sectionId} {task.track.value} occupies the "
                f"line for the whole possession of {task.taskId}; the adjacent track is "
                f"under caution and closed to maintenance"
            )
        if task.requiresT351:
            out.append(
                f"HC-005: {task.taskId} needs Station Master endorsement on Form T/351 "
                f"before work starts"
            )
        if task.requiresPTW:
            out.append(f"HC-003: {task.taskId} needs a Permit To Work under the power block")
    return sorted(set(out))
