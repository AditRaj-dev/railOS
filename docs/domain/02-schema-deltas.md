# Schema deltas vs the PRD canonical models

The PRD (section 4.3–4.5) gives illustrative JSON. Those shapes cannot express the
verified hard constraints of Ground Reality Report section 23. Everything added below
is required by a specific HC and must exist in the API and database schema.

Generated JSON Schema for every model lives in `schemas/` — generate types from there:

```bash
python -m railos_model.export_schemas schemas
```

## MaintenanceTask — added fields

| Field | Type | Required by | Why |
|---|---|---|---|
| `sectionId` | str | HC-001, HC-008 | Conflict detection is per block section, not per corridor. |
| `track` | UP/DOWN/THIRD/SINGLE | HC-001, HC-012 | Occupancy is per track. |
| `dueMinute` | int | SO-006 | Horizon-relative deadline; ISO date is an edge format. |
| `durationStdDev` | int | SO-005 | Block-burst buffer needs a spread, not a point estimate. |
| `machineType` | enum | HC-002, HC-008, HC-009 | Statutory minimum duration and machine spacing. |
| `requiresPTW` | bool | HC-003, HC-004 | Permit To Work gate and energization buffer. |
| `requiresT351` | bool | HC-005 | S&T disconnection endorsement gate. |
| `requiresCorrespondenceTest` | bool | HC-006 | 30-minute post-work testing window. |
| `infringesAdjacent` | bool | HC-010 | Caution Order T/409 obligation. |
| `hasMobileLighting` | bool | HC-015 | Daylight restriction for non-illuminated work. |
| `requiresSntEscort` | bool | HC-017 | Track circuit continuity during tamping. |
| `imposesSpeedRestriction` | bool | HC-018 | Post-block SR footprint (SO-007). |
| `oheElementarySection` | str? | HC-003 | A power block de-energizes a whole elementary section. |
| `resourceIds`, `gangId` | str list / str? | HC-009, HC-013 | Machine occupancy and gang transit feasibility. |
| `overdueDays` | int | priority, SO-006 | Maintenance debt. |
| `isEmergency`, `detectedAtMinute` | bool, int? | HC-011 | IMR 72-hour statutory clock. |
| `locked` | bool | replanning | Started or immutable operations must not move. |

`estimatedDuration` is validated on construction against `MIN_MACHINE_BLOCK_MINUTES`
(HC-002) — a CSM task of 90 minutes is rejected at the model boundary, not at solve time.

## BlockSection - added field

| Field | Type | Required by | Why |
|---|---|---|---|
| `mps` | int (kmph) | HC-010, HC-018 | The cost of a caution order or a speed restriction is `dist/restricted - dist/mps`. Without a sectional speed those consequences cannot be computed at all. |

## TrainMovement

Added `sectionId` + `track` (per-section paths), `delayMinutes` (Scenario 5 cascade).

## New models not in the PRD

`BlockSection`, `Resource`, `Dependency`, `GoodsForecast`, `ScenarioWorld`,
`Opportunity`, `BundleCandidate`, `PriorityResult`, `RiskResult`, `Factor`,
`Assignment`, `ScheduledBlock`, `UnassignedTask`, `PlanMetrics`, `Plan`.

`Plan` is the envelope the charter requires: plan id, version, objective profile,
blocks, assignments, unassigned tasks, warnings, metrics, explanation factors,
solver status, runtime metadata, provenance.

## Conventions the API must preserve

- Time is **integer minutes from `horizonStartIso`**, everywhere inside the platform.
  Convert to ISO only at the HTTP/UI boundary.
- Distance is **integer metres** (HC-008 needs 200 m precision; floats and CP-SAT
  do not mix).
- Unassigned tasks are part of a valid response. Never filter them out.
