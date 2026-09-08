# HANDOFF -> Codex (API & data platform)

**CHANGE:**
Planning intelligence is implemented and passing its own hard-constraint audit.
`/apps/api` can now expose it; no scheduling logic belongs in the API layer.

**FILES:**
```
packages/railos_model/     contracts + JSON Schema export
packages/railos_data/      dataset generator + loader
packages/risk_engine/      priority + risk
packages/opportunity_engine/  free-window and shadow-block detection
packages/bundling_engine/  compatibility matrix + bundle candidates
packages/optimizer/        CP-SAT model, independent audit, replanning
packages/simulator/        deterministic disturbances
config/weights.yaml        priority + risk weights
config/objectives.yaml     SO-001..SO-008 weights, three profiles, solver settings
schemas/*.schema.json      generated contracts -- generate your types from these
```

**NEW DATA TYPES:**
All in `schemas/`. The additions beyond the PRD are catalogued with the constraint
that forces each one in `docs/domain/02-schema-deltas.md`. The important ones:
`MaintenanceTask.machineType / requiresPTW / requiresT351 / requiresCorrespondenceTest /
infringesAdjacent / hasMobileLighting / requiresSntEscort / imposesSpeedRestriction /
oheElementarySection / gangId / durationStdDev / detectedAtMinute / locked`.

**NEW ENDPOINT REQUIREMENT:**

```
POST /optimization/generate
  body:  { datasets|worldRef, objective: SAFETY_FIRST|BALANCED|OPERATIONS_FIRST }
  impl:  optimizer.solve(world, SolveOptions(profile=...))
  200:   Plan   (schemas/Plan.schema.json)

POST /replanning/propose
  body:  { planId, now, scenario|worldPatch, reason }
  impl:  optimizer.replan(world, previous_plan, now=..., reason=...)
  200:   { plan: Plan (status=PROPOSED), diff: { added, removed, moved, metricDeltas } }

POST /plans/{planId}/approve
  body:  { approver }
  impl:  optimizer.approve(plan, approver)
  200:   Plan (status=APPROVED, planVersion+1, parentPlanId set)

GET  /opportunities         opportunity_engine.detect(world)
GET  /bundles               bundling_engine.build(world, opportunities, priorities)
GET  /maintenance/priority  risk_engine.score_all(world)
GET  /maintenance/risk      risk_engine.assess_all(world)
GET  /scenarios             simulator.SCENARIOS keys
```

**CONSTRAINT EFFECT:**
- The API must **never** filter `plan.unassigned`. Unassigned work with a reason is
  part of a correct answer.
- `solverStatus == INFEASIBLE` is a 200 with an empty schedule and a warning, not a
  500 and not a relaxed plan.
- A plan reaches `APPROVED` only through the approve endpoint, with an approver
  recorded. No other transition may set that status.
- Time in every payload is integer minutes from `ScenarioWorld.horizonStartIso`.
  Convert to ISO at the HTTP boundary only.

**MIGRATION REQUIRED:**
Yes, for any table already modelled on the PRD JSON: add the columns in
`02-schema-deltas.md`. `estimatedDuration` must be validated against
`MIN_MACHINE_BLOCK_MINUTES` on write (HC-002) -- the Pydantic model already does this,
so route writes through it.

**TESTS:**
`pytest -q` at the repo root: 55 tests covering dataset conformance, priority
monotonicity, opportunity/train disjunction, the compatibility matrix, all nine
charter-required optimizer properties, replanning immutability and all seven
simulator scenarios.

**EXAMPLE INPUT:**
```bash
railos plan --objective BALANCED --json plan.json
```

**EXAMPLE OUTPUT:** (abridged `Plan`)
```json
{
  "planId": "PLAN-BFCDC7AA", "planVersion": 1, "status": "GENERATED",
  "objectiveProfile": "BALANCED", "solverStatus": "OPTIMAL",
  "blocks": [{ "blockId": "BLK-ZB_DER-00002", "sectionId": "SEC_GZB_DER",
               "track": "UP", "blockType": "INTEGRATED", "start": 2, "end": 182,
               "taskIds": ["ENG-1001","SNT-2001","TRD-3001"],
               "departments": ["ENGG","SNT","TRD"] }],
  "assignments": [{ "taskId": "ENG-1001", "blockId": "BLK-ZB_DER-00002",
                    "start": 2, "end": 182,
                    "explanation": [{ "name": "priority_contribution", "raw": 71.5,
                                      "weight": 0.30, "contribution": 3861.0,
                                      "note": "SO-001 critical maintenance yield" }] }],
  "unassigned": [],
  "metrics": { "blockUtilisation": 82.74, "coordinationRatio": 75.0,
               "criticalCompletionRate": 100.0, "trainDisruptionMinutes": 0 },
  "objectiveBreakdown": { "yield": 22848.0, "TOTAL": 18274.0 },
  "warnings": ["HC-010: ENG-1002 infringes the adjacent line -- Caution Order T/409 ..."],
  "runtime": { "wallSeconds": 5.595, "solver": "OR-Tools CP-SAT" }
}
```
