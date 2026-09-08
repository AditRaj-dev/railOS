# RailOS Codex Backend

## Delivered architecture

`apps/api/railos_api` is a FastAPI orchestration layer over canonical models in
`packages/railos_model` and the architecture-owned solver in `packages/optimizer`.
It never schedules work itself: if the solver cannot be imported, optimization and
replanning return `OPTIMIZER_UNAVAILABLE`.

All bundled TMS, SMMS, TDMS, COA, BDMS, timetable, and goods inputs are deterministic
synthetic adapters for `GZB_ALJN_DEMO`. They are not live CRIS connections. Solver time
is integer minutes from `2026-09-09T00:00:00+05:30`; HTTP payloads use camelCase.

## Run and verify

```powershell
python -m pip install -r apps/api/requirements.txt
$env:PYTHONPATH="apps/api;packages/railos_model;packages/shared;packages/optimizer;."
python -m uvicorn railos_api.main:app
python -m unittest discover -s tests -v
```

Storage defaults to a thread-safe in-memory repository. PostgreSQL mode requires
`RAILOS_STORAGE_BACKEND=postgres`, `DATABASE_URL`, and `psycopg`; it stores atomic
application snapshots in the `railos_state` JSONB aggregate table while the normalized
domain migrations provide the production schema. Missing dependencies or connectivity
fail startup and never fall back to memory.

## API and authorization

All operational requests require `X-RailOS-User` and a valid `X-RailOS-Role`.
Command retries may provide `Idempotency-Key`.

| Capability | Endpoint | Roles |
|---|---|---|
| Health | `GET /api/v1/health` | Public |
| Demo reset | `POST /api/v1/demo/reset` | Admin |
| Core railway data | `GET /api/v1/{assets,corridors,train-movements,maintenance,defects,block-windows}` | Any valid role |
| Create defect | `POST /api/v1/defects` | Engineering, S&T, Traction |
| Generate three candidates | `POST /api/v1/optimization/generate` | Planner, Control Officer |
| Plan decision | `POST /api/v1/block-plans/{id}/{approve,reject,request-revision,lock}` | Controller; Planner may request revision |
| Work update | `POST /api/v1/work/assignments/{id}/updates` | Field, department, controller |
| Emergency and replan | `POST /api/v1/emergencies`, `POST /api/v1/replanning/generate` | Authorized operational roles |
| Events | `GET /api/v1/events`, `POST /api/v1/events/replay`, `WS /api/v1/events/ws` | Any valid role |

Errors use `{ "error": { "code", "message", "details", "requestId" } }`.
Approved plan history is preserved by version. Emergency replanning requires a persisted
`emergencyId`, invokes the canonical replanner, returns its diff, and leaves the parent
snapshot unchanged. Starting or locking work marks canonical tasks immutable for replanning.

## Frontend handoff

- Load command-center state from maintenance, defects, block-window, and analytics endpoints.
- Submit one optimization request and render its three `candidatePlans`.
- Preserve `planId` and `planVersion`; send `expectedVersion` when approving.
- Subscribe to `/api/v1/events/ws` with the same identity headers.
- Create an emergency first, then pass its ID with `parentPlanId`, `nowMinute`, and `reason`
  to `/api/v1/replanning/generate`.
- Always display the `Synthetic Hackathon Simulation` label in demo views.

## Known production gaps

Enterprise SSO, real Pravah/CRIS connectivity, migration orchestration, multi-process event
fan-out, and load-tested PostgreSQL deployment remain production work. The in-process
WebSocket broker is suitable for the hackathon API process only.
