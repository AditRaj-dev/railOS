"""RailOS planning CLI -- the golden flow without a UI.

    railos plan                      generate a plan for the corridor
    railos plan --objective SAFETY_FIRST --json out.json
    railos replan --scenario critical_defect --now 300
    railos opportunities             what windows exist and why
    railos scenarios                 list the simulator disturbances
    railos validate                  dataset conformance + hard constraint audit
"""

import argparse
import json
import pathlib
import sys

from bundling_engine import build as build_bundles
from opportunity_engine import detect
from optimizer import SolveOptions, approve, audit, replan, solve
from optimizer.traingraph import caution_orders, disruption, speed_restrictions
from railos_data import load_world
from railos_model import ObjectiveProfile, Plan
from risk_engine import assess_all, score_all
from simulator import SCENARIOS

ROOT = pathlib.Path(__file__).resolve().parents[3]
DATASETS = ROOT / "datasets"


def hhmm(minute: int) -> str:
    return f"D{minute // 1440 + 1} {minute % 1440 // 60:02d}:{minute % 60:02d}"


def _rule(title: str) -> None:
    print(f"\n{title}\n{'-' * len(title)}")


def print_plan(world, plan: Plan, verbose: bool = False) -> None:
    _rule(f"PLAN {plan.planId} v{plan.planVersion} [{plan.status.value}] {plan.objectiveProfile.value}")
    print(f"solver {plan.solverStatus} in {plan.runtime.get('wallSeconds')}s -- {plan.provenance}")

    _rule("BLOCKS")
    for b in plan.blocks:
        depts = "+".join(sorted(d.value for d in b.departments))
        print(
            f"  {b.blockId:22s} {b.sectionId:14s} {b.track.value:4s} {b.blockType.value:13s} "
            f"{hhmm(b.start)} - {hhmm(b.end)} ({b.end - b.start:3d} min) {depts:12s} {', '.join(b.taskIds)}"
        )

    _rule("ASSIGNMENTS")
    for a in plan.assignments:
        task = world.task(a.taskId)
        print(
            f"  {a.taskId:12s} {task.department.value:5s} {task.taskType.value:22s} "
            f"{hhmm(a.start)} - {hhmm(a.end)}  in {a.blockId}"
        )
        if verbose:
            for f in a.explanation:
                print(f"        {f.name:24s} raw={f.raw:8.2f} w={f.weight:5.2f} -> {f.contribution:10.2f}  {f.note}")

    if plan.unassigned:
        _rule("UNASSIGNED (reported, never hidden)")
        for u in plan.unassigned:
            print(f"  {u.taskId:12s} {u.reason}")

    _rule("METRICS")
    for k, v in plan.metrics.model_dump().items():
        print(f"  {k:26s} {v}")

    _rule("OBJECTIVE BREAKDOWN")
    for k, v in sorted(plan.objectiveBreakdown.items(), key=lambda kv: -abs(kv[1])):
        print(f"  {k:20s} {v:12.1f}")

    orders = caution_orders(world, plan)
    restrictions = speed_restrictions(world, plan)
    if orders or restrictions:
        _rule("TRAIN-GRAPH CONSEQUENCES (what this plan costs after the block clears)")
        for o in orders:
            print(f"  {o.describe()}")
        for r in restrictions:
            print(f"  {r.describe()}")
        print(
            f"  recomputed delay: {plan.metrics.trainDisruptionMinutes} train-minutes "
            f"({plan.runtime.get('weightedDisruption', 0)} weighted, "
            f"{plan.runtime.get('premiumDelayMinutes', 0)} on Rajdhani/Vande Bharat paths) "
            f"over {plan.runtime.get('graphIterations', 1)} recompute pass(es)"
        )

    if plan.warnings:
        _rule("OPERATIONAL OBLIGATIONS & WARNINGS")
        for w in plan.warnings:
            print(f"  ! {w}")

    violations = audit(world, plan)
    _rule("HARD CONSTRAINT AUDIT (independent re-check)")
    if violations:
        for v in violations:
            print(f"  FAIL {v}")
        print("\n  This plan is NOT valid.")
    else:
        print("  PASS -- no hard constraint violated by the produced schedule.")


def cmd_plan(args) -> int:
    world = load_world(args.datasets)
    opts = SolveOptions(profile=ObjectiveProfile(args.objective))
    plan = solve(world, opts, converge=not args.no_converge)
    if args.approve:
        plan = approve(plan, args.approve)
    print_plan(world, plan, args.verbose)
    if args.json:
        pathlib.Path(args.json).write_text(plan.model_dump_json(indent=2), encoding="utf-8")
        print(f"\nwrote {args.json}")
    return 0 if plan.solverStatus in ("OPTIMAL", "FEASIBLE") else 1


def cmd_replan(args) -> int:
    world = load_world(args.datasets)
    base = approve(solve(world, SolveOptions(profile=ObjectiveProfile(args.objective))), args.approver)
    disturbed = SCENARIOS[args.scenario](world)
    revised, delta = replan(disturbed, base, now=args.now, reason=f"scenario: {args.scenario}")

    _rule(f"BEFORE -- {base.planId} v{base.planVersion} [{base.status.value}]")
    for a in base.assignments:
        print(f"  {a.taskId:12s} {hhmm(a.start)} - {hhmm(a.end)}")

    print_plan(disturbed, revised, args.verbose)

    _rule("PLAN DIFF")
    print(f"  {delta.summary()}")
    for t in delta.added:
        print(f"  + {t}")
    for t in delta.displaced:
        print(f"  - {t}   DISPLACED -- needs a controller decision")
    for t, before, after in delta.moved:
        print(f"  ~ {t}   {hhmm(before)} -> {hhmm(after)}")
    for k, v in delta.metric_deltas.items():
        print(f"    {k:26s} {v:+.4f}")
    print("\n  Nothing here is approved. An authorized railway officer decides.")
    return 0


def cmd_opportunities(args) -> int:
    world = load_world(args.datasets)
    priorities = {k: v.score for k, v in score_all(world).items()}
    ops = detect(world)[: args.limit]
    _rule(f"BLOCK OPPORTUNITIES (top {len(ops)} by size)")
    for o in ops:
        print(
            f"  {o.opportunityId:8s} {o.sectionId:14s} {o.track.value:4s} "
            f"{hhmm(o.start)} - {hhmm(o.end)} {o.minutes:4d} min  traffic={o.trafficImpact:6s} "
            f"candidates={len(o.candidateTaskIds)}"
        )
    _rule("BUNDLE CANDIDATES")
    for b in build_bundles(world, ops, priorities)[: args.limit]:
        print(f"  {b.bundleId:8s} {b.blockType.value:13s} {b.compatibility.value:24s} {b.taskIds}")
        for r in b.rationale:
            print(f"           {r}")
    return 0


def cmd_risk(args) -> int:
    world = load_world(args.datasets)
    priorities, risks = score_all(world), assess_all(world)
    _rule("PRIORITY & RISK")
    for tid in sorted(priorities, key=lambda t: -priorities[t].score):
        p, r = priorities[tid], risks[tid]
        print(
            f"  {tid:12s} {p.score:6.2f} {p.band:8s} now={r.current:6.2f} "
            f"+24h={r.at24h:6.2f} +72h={r.at72h:6.2f} {r.trend:7s} "
            f"latest start={hhmm(r.maxDeferralMinutes)}"
        )
        if args.verbose:
            for f in p.factors:
                print(f"        {f.name:22s} raw={f.raw:6.2f} x w={f.weight:5.2f} = {f.contribution:7.2f}")
    print("\n  Scores are deterministic heuristics over configured weights. No ML.")
    return 0


def cmd_scenarios(args) -> int:
    _rule("SIMULATOR SCENARIOS")
    for name, fn in sorted(SCENARIOS.items()):
        doc = (fn.__doc__ or "").strip().splitlines()[0] if fn.__doc__ else "deterministic disturbance"
        print(f"  {name:18s} {doc}")
    return 0


def cmd_validate(args) -> int:
    world = load_world(args.datasets)
    print(
        f"dataset OK: {len(world.tasks)} tasks, {len(world.trains)} train movements, "
        f"{len(world.resources)} resources, {len(world.dependencies)} dependencies"
    )
    failures = 0
    for profile in ObjectiveProfile:
        plan = solve(world, SolveOptions(profile=profile))
        violations = audit(world, plan)
        failures += len(violations)
        print(
            f"  {profile.value:17s} {plan.solverStatus:10s} "
            f"scheduled={plan.metrics.tasksScheduled:2d} audit={'PASS' if not violations else 'FAIL'}"
        )
        for v in violations:
            print(f"      {v}")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="railos", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--datasets", default=str(DATASETS))
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("plan", help="generate a plan")
    p.add_argument("--objective", default="BALANCED", choices=[o.value for o in ObjectiveProfile])
    p.add_argument("--approve", metavar="OFFICER", help="record human approval by this officer")
    p.add_argument("--json", metavar="PATH", help="write the plan envelope as JSON")
    p.add_argument(
        "--no-converge",
        action="store_true",
        help="single CP-SAT pass against the charted timetable, without recomputing "
        "the train graph under the caution orders and speed restrictions the plan "
        "itself creates (shows what the naive answer looks like)",
    )
    p.set_defaults(func=cmd_plan)

    p = sub.add_parser("replan", help="disturb the world and re-solve")
    p.add_argument("--scenario", default="critical_defect", choices=sorted(SCENARIOS))
    p.add_argument("--now", type=int, default=300, help="minute at which replanning happens")
    p.add_argument("--objective", default="BALANCED", choices=[o.value for o in ObjectiveProfile])
    p.add_argument("--approver", default="Sr.DOM/GZB")
    p.set_defaults(func=cmd_replan)

    p = sub.add_parser("opportunities", help="windows and bundle candidates")
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(func=cmd_opportunities)

    p = sub.add_parser("risk", help="priority and risk table")
    p.set_defaults(func=cmd_risk)

    p = sub.add_parser("scenarios", help="list simulator scenarios")
    p.set_defaults(func=cmd_scenarios)

    p = sub.add_parser("validate", help="dataset + all three profiles + audit")
    p.set_defaults(func=cmd_validate)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
