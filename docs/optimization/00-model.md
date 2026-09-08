# RailOS Optimization Model

Problem class: **RCPSP-SDST** — resource-constrained project scheduling with
disjunctive spatial windows and sequence-dependent setups. Solver: OR-Tools CP-SAT.

## Decision variables

```
s[i]  IntVar(0, H)             task start, minutes
e[i]  IntVar(0, H)             task end
p[i]  BoolVar                  task is scheduled (optional interval)
iv[i] OptionalIntervalVar(s,e,dur,p)
bs[b], be[b]                   block start/end
a[i,b] BoolVar                 task i assigned to block b
```

Unassigned tasks are **legal and reported**, never silently dropped. A task is
inside exactly one block: `sum_b a[i,b] == p[i]`, and `bs[b] <= s[i]`, `e[i] <= be[b]`
whenever `a[i,b]`.

## Hard vs soft

Hard constraints (`docs/domain/01-constraints.md`) are inviolable. If the model is
`INFEASIBLE` the answer is "no feasible plan" plus the conflicting constraint set —
never a relaxed plan presented as valid.

Soft objectives are the single weighted linear expression below. Weights live in
`config/objectives.yaml`; no magic numbers in code.

```
Z =  w1 * Yield            (SO-001, 30%)   sum priority[i] * work_units[i] * p[i]
   + w3 * Bundling         (SO-003, 15%)   cross-department task pairs sharing a block
   + w8 * MachineUse       (SO-008,  2%)   scheduled machine minutes
   - w2 * PassengerDelay   (SO-002, 25%)   delay_min * class_weight
   - w4 * FreightDetention (SO-004, 10%)
   - w5 * OverrunRisk      (SO-005, 10%)   penalty when window - dur < 2 * sigma
   - w6 * DeferralDebt     (SO-006,  5%)   overdue_days * risk_slope * (1 - p[i])
   - w7 * SRFootprint      (SO-007,  3%)   length_km * days_active
```

Class weights (SO-002): Vande Bharat/Rajdhani 5.0, Suburban peak 4.0, Mail/Express 3.0,
Passenger 1.5. Freight is priced separately through SO-004, not as a passenger class.

All terms are integers (weights scaled ×100) — CP-SAT is an integer solver.

## Objective profiles

`SAFETY_FIRST`, `BALANCED`, `OPERATIONS_FIRST` are **three weight vectors over one
model**, not three algorithms. Profile only changes `w1..w8`.

## Explainability

The optimizer emits, per assignment: priority contribution, urgency contribution,
bundling benefit, traffic penalty, unused-window penalty, risk reduction — plus the
objective breakdown, solver status and wall time. An LLM may verbalize these numbers
afterwards; it never produces them and never schedules.

## The plan changes the timetable it was planned against

A block is not consequence-free. HC-010 and HC-012 put the adjacent line under a
Form T/409 caution order at 45 kmph for the possession; HC-018 leaves the worked line
at 20 / 45 / 75 kmph for three days. Trains therefore run slower *after* the plan,
which moves the traffic-free windows the plan depends on.

`solve()` closes that loop:

```
solve once  ->  recompute the graph under this plan's own restrictions
            ->  any maintenance now colliding with a train path?
            ->  yes: re-solve against the recomputed timetable and repeat
            ->  no:  done  (runtime.graphIterations records the passes)
```

`solve(..., converge=False)` gives the single naive pass, which is what the recompute
consumes and what makes the difference demonstrable. `trainDisruptionMinutes` is the
recomputed figure, not an assumed zero.

## Audit pass

`optimizer/audit.py` re-checks every hard constraint against the produced schedule,
independently of the model. A modelling bug that relaxes a safety constraint must
fail loudly rather than ship a plausible-looking plan.
