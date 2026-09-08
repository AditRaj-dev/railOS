# RailOS — planning intelligence

Railway maintenance planning for the Ghaziabad–Aligarh corridor: risk-aware
prioritisation, block opportunity detection, verified multi-department bundling,
CP-SAT optimisation under Indian Railways statutory constraints, emergency
replanning, and an explanation for every decision.

This repository currently contains the **architecture and optimisation layer**
(Claude's ownership per `CLAUDE.md`). The API, database, UI and field apps are
other agents' work and are not here yet.

> All data is **synthetic**. Nothing here is connected to TMS, SMMS, TDMS, COA or
> BDMS, and no output is a railway authorisation. RailOS proposes; an authorized
> railway officer decides.

## Quick start

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/Scripts/python.exe -e ".[dev]"
```

```bash
railos validate
```

```bash
railos plan --objective BALANCED -v
```

```bash
railos replan --scenario critical_defect --now 300
```

Other commands: `railos opportunities`, `railos risk -v`, `railos scenarios`.

Regenerate the dataset or the contracts:

```bash
python -m railos_data.generate datasets
```

```bash
python -m railos_model.export_schemas schemas
```

## What is where

```
packages/railos_model/        contracts (Pydantic) + JSON Schema export
packages/railos_data/         synthetic dataset generator and loader
packages/risk_engine/         priority scoring + deferral risk
packages/opportunity_engine/  traffic-free windows, shadow blocks
packages/bundling_engine/     verified compatibility matrix, bundle candidates
packages/optimizer/           CP-SAT model, independent audit, replanning
packages/simulator/           deterministic disturbances
packages/railos_cli/          the demo without a UI
config/                       all weights and buffers, no magic numbers in code
datasets/                     nine generated files, IR-authentic naming
docs/domain/                  domain model, HC-001..HC-018, schema deltas
docs/optimization/            the mathematical model
docs/handoff/                 implementation-ready handoffs to the other agents
```

## The chain this proves

```
uncoordinated demand -> feasible windows -> risk-aware priority -> verified bundling
 -> constraint optimisation -> three candidate plans -> human approval -> emergency replan
```

## Honesty rules this codebase keeps

- Hard constraints (`docs/domain/01-constraints.md`) are never relaxed. `INFEASIBLE`
  is a legitimate answer; a quietly relaxed plan is not.
- Every produced plan is re-checked by `optimizer/audit.py`, which does not reuse the
  CP-SAT model. A plan that fails the audit is not a plan.
- Priority and risk are **deterministic heuristics over configured weights**. They are
  not machine learning and are never described as such.
- No LLM schedules anything. The optimizer emits its own contribution factors; a
  language model may read them aloud later.
- Unassigned work is reported with a reason. It is never dropped.
- A plan is solved against the timetable **it creates**, not the one it started from:
  caution orders and speed restrictions slow trains, so the solver iterates to a
  fixed point and the audit re-checks HC-001 against the recomputed graph.

## Tests

```bash
pytest -q
```

71 tests: dataset conformance, priority monotonicity and factor decomposition,
opportunity/train disjunction (including a randomised property check), the
compatibility matrix (`STRICTLY_PROHIBITED` and conservative unknown defaults), the
nine optimizer properties the charter requires, plan-version immutability, all seven
simulator scenarios, and the train-graph consequences of HC-010 / HC-012 / HC-018 --
including a plan that is rejected because it ignores its own restrictions.
