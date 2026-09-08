# Implementation findings

What turned up while building the planning layer and while reading the API/data layer
next to it. Ordered by severity within each section. Items marked **FIXED** were fixed
in this pass; the rest are handed over, because they sit in another agent's territory.

---

## A. Optimizer layer — bugs found and fixed

| # | Finding | Effect if unfixed |
|---|---|---|
| A1 **FIXED** | A lone PTW task made its own block infeasible: the block span was derived as `min(task starts)`, then HC-003 demanded `start >= block_start + 20`, which is unsatisfiable when the task *is* the minimum. | Every power-block task silently dropped — the six highest-priority tasks in the dataset came back "deferred by the optimizer". A plausible plan, missing exactly the work that matters. Fixed by spanning the block over the *possession* (work ± statutory buffers), not the work. |
| A2 **FIXED** | HC-016's cap was sized from the tasks *eligible* for a window, not the ones actually scheduled in it. Model and audit therefore disagreed. | The model permitted 254-minute possessions that the audit correctly rejected. Now the cap is a CP-SAT `AddMaxEquality` over the assigned tasks, identical to what the audit computes. |
| A3 **FIXED** | CP-SAT with 8 parallel workers is not bit-reproducible; two identical runs produced different plans and different metrics. | Violates the charter's "plan metrics reproducible". Now `num_workers: 1` with a fixed seed; the model solves in a few seconds so there is nothing to buy back. |
| A4 **FIXED** | Block utilisation counted parallel work twice — two gangs side by side gave 117.5%. | A headline KPI that reads above 100% destroys trust in every other number on the screen. Now the union of task intervals. |
| A5 **FIXED** | Speed-restriction and caution-order delay were priced over the **whole section** instead of the worked length. | A 300 m turnout renewal was charged as if 36 km ran at 20 kmph, so the optimizer refused the entire five-task turnout chain. Real work rejected by a unit error. |
| A6 **FIXED** | The HC-018 concurrency budget was a *task count* over a 3-day restriction window inside a 3-day horizon — effectively "at most 2 SR tasks ever". | Arbitrary starvation. Replaced with a length budget (`speed_restriction.max_concurrent_km`) applied to the severe 20 kmph day only; days 2–3 are priced, not rationed. |
| A7 **FIXED** | My first audit implementation summed every restriction whose start fell within ±1 day of another and called that "concurrent". | Invented violations: two restrictions can both overlap a third without overlapping each other. Concurrency is now measured at an instant, matching `AddCumulative`. |
| A8 **FIXED** | Emergency IMR work was bounded only by the 72-hour statutory ceiling, so the solver parked a rail fracture 2.5 days out. | Statutorily legal, operationally indefensible. Now bounded by the next feasible possession (`EMERGENCY_TARGET_MINUTES`, 240) with HC-011 still the hard outer limit. It now lands 70 minutes after detection. |
| A9 **FIXED** | Replanning locked already-started work *and* forbade anything before `now`, which made the locked work itself illegal. | Every emergency replan returned INFEASIBLE. Locked work is now exempt from the replanning boundary. |
| A10 **FIXED** | A single CP-SAT pass plans against the charted timetable, but the plan's own caution orders and speed restrictions slow trains — and the recomputed paths collided with possessions the same plan had booked. | This is the whole HC-010/012/018 gap. `solve()` now iterates plan → recompute → re-solve to a fixed point, and the audit re-checks HC-001 against the recomputed graph. Two scenarios (`train_delayed`, `critical_defect`) genuinely need the second pass. |
| A11 **FIXED** | Tasks dropped because one link of an HC-007 chain was blocked reported the generic "deferred by the optimizer". | Misleading: five tasks disappear and the reason names none of the cause. Chain members now say so explicitly. |

## B. Optimizer layer — known limits, deliberately left

| # | Limit | When it matters |
|---|---|---|
| B1 | Gang and machine transit is `hops × constant` (45 / 60 min per section), not a real distance matrix. | Fine on one corridor; wrong the moment depots and multi-corridor moves are modelled. Replace with a transit matrix in `resources.json`. |
| B2 | The SR/caution delay coefficient uses the *window* start as the proxy for the restriction start, because the task's actual start is a decision variable. It is conservative (over-states), never under-states. | Only matters if it becomes worth the extra variables to make the coefficient time-dependent. |
| B3 | HC-008 (200 m machine spacing) is enforced only between tasks whose fixed locations are already within 200 m; machine position is not itself a decision. | Correct for our data, where a task's site is given. Wrong if a machine's working position ever becomes schedulable. |
| B4 | The recompute cascades a train's own delay down its path but does not re-sequence trains against each other (no headway propagation between trains, no platform/loop capacity). | It under-states knock-on delay in dense traffic. Naming it here rather than implying full timetable simulation. |
| B5 | `MAX_BLOCK_MINUTES` (HC-016) is applied uniformly; the "Sunday mega block" exemption is inferred from the work needing a longer possession, not from the calendar. | Add a calendar once real WTT dates are in play. |
| B6 | Solve time is ~5 s per pass on 15 tasks and up to 3 passes. Growth is dominated by (tasks × eligible windows). | 267 tasks (the API's seed) will not solve in 20 s. See C1. |

## C. API / data layer (Codex's territory) — handed over, not fixed

| # | Finding | Why it matters |
|---|---|---|
| **C1** | `apps/api/railos_api/main.py` seeds its **own** synthetic world instead of loading `datasets/`: 267 tasks that are all `TAMPING`, one 100 km section `SEC-GZB-ALJN`, no dependencies, no resources, no `machineType`, no `requiresPTW`/`requiresT351`, 41 evenly spaced train movements. | The API demo exercises none of the statutory constraints. With no `machineType`, HC-002 is vacuous; with no dependencies, HC-007 never fires; with no PTW/T351, HC-003/004/005/006 never fire. The optimizer looks like a generic scheduler. It also collides with C2. **Load `railos_data.load_world("datasets")`.** |
| **C2** | Section id schemes differ: the API uses `SEC-GZB-ALJN` (hyphens, one section), the dataset uses `SEC_GZB_DER` … `SEC_SMQ_ALJN` (underscores, four sections). | Any join across the two — a UI reading the API and the dataset, or a plan generated on one and audited on the other — silently produces empty results rather than an error. |
| **C3** | The API never calls `optimizer.audit()`. | A plan is offered for human approval without the independent hard-constraint re-check. That check exists precisely because a modelling bug can produce a plausible, illegal plan. It should run before a plan is returned, and its result should be in the response. |
| **C4** | Approval is hand-rolled in `decide()` rather than calling `optimizer.approve(plan, approver)`. The approver is recorded in the event log, but `plan.provenance` still reads "synthetic dataset; deterministic scoring…". | The plan object that a controller downloads or a UI renders does not say who approved it. Plan-level traceability is a charter requirement. |
| **C5** | `POST /optimization/generate` solves three profiles serially inside `with state.transaction()`, which holds a global `RLock`. | With the 20 s solver cap that is up to a minute of fully serialised API. Combined with B6 and 267 tasks, this is the first thing that will fall over in the demo. Solve outside the lock; store under it. |
| **C6** | "Reject" maps to `PlanStatus.SUPERSEDED` and "request revision" maps to `PROPOSED`. | A rejected plan and a plan replaced by a newer version are different facts, and the audit trail cannot distinguish them afterwards. Suggest adding `REJECTED` to `PlanStatus` — it is my model, I will add it on request. |
| **C7** | `optimizer_port.LiveOptimizer.generate` accepts `**kwargs` and discards them. | Headway, config path, locked starts and the new `converge` flag are all unreachable through the API. It also means the API cannot ask for the single-pass plan for comparison. |
| **C8** | `tests/test_api_backend.py` cannot be collected — `fastapi` is not installed in the repo venv, so a bare `pytest` at the root aborts collection for every suite. | `pytest -q` is the documented entry point for the whole repo. Either add `fastapi` to the dev extras or mark the module `importorskip`. Engine suite currently needs `--ignore=tests/test_api_backend.py`. |
| **C9** | Skip guards (`if importlib.util.find_spec("ortools") is None: raise SkipTest`) were added to my engine test modules. | If `ortools` ever fails to install, the entire optimizer suite reports **green by skipping** instead of failing. For the one package whose correctness is the product, silent skips are the wrong default. Prefer letting it fail, or make the CI job assert a minimum test count. |

## D. Cross-cutting

| # | Finding |
|---|---|
| D1 | Three agents write to one working tree with no VCS — `E:\RailOS` is not a git repository. Files appeared and were edited underneath this session mid-task. Nothing is recoverable if two agents touch one file. **`git init` before anything else.** |
| D2 | `apps/control-center/node_modules` (3.6k+ files) is committed into the tree. With no `.gitignore` in place, the first commit will be enormous. |
| D3 | The PRD's illustrative priority weights and the Ground Reality Report's SO-001…SO-008 weights are different numbers for overlapping concepts. I follow the report (source-of-truth order) and keep both in `config/`; anyone quoting the PRD's "30% safety criticality" at a demo should know it is the *priority* weight, not an objective weight. |
