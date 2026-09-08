# RailOS Domain Model (frozen)

Owner: Architecture & Optimization Agent. Source of truth order: verified railway
constraints (Ground Reality Report) > PRD > data contracts > implementation > UI.

## Units & conventions

| Concept | Representation | Notes |
|---|---|---|
| Time | `int` minutes since `horizon_start` | Solver-native. ISO timestamps only at I/O edges. |
| Horizon | `[0, horizon_minutes)` | Default 72 h = 4320. |
| Location | `int` metres from section datum (`km * 1000`) | Avoids float in CP-SAT (HC-008 needs 200 m). |
| Duration | `int` minutes | Statutory minimums per machine, §8.1. |
| IDs | `str`, IR-authentic | `TRACK_SEC_GZB_ALJN_UP`, `POINT_102B_GZB`, `OHE_ELEM_2041_ALJN`. |

Departments: `ENGG` (Civil/P-Way) · `SNT` (Signal & Telecom) · `TRD` (Traction Distribution).
Operating is not a maintenance department; it is the authority that grants blocks.

## Entities

- **Corridor** — ordered chain of **BlockSections** between block stations; line config
  (`SINGLE`, `DOUBLE`, `MULTI`), tracks (`UP`, `DOWN`, `THIRD`).
- **Asset** — track section, point, OHE elementary section, signal, level crossing.
  Carries `criticality` 1–10 and the OHE elementary section it sits under.
- **MaintenanceTask** — the unit the optimizer schedules. Canonical PRD §4.3 fields plus
  the statutory fields listed in `02-schema-deltas.md`.
- **Defect** — observed fault feeding priority/risk (`IMR`, `IMRW`, `OBS`, `OMS_PEAK_HIGH`,
  `POINT_SLACK_DETECTION`, `OHE_DROPPING_FAULT`). An `IMR` carries a statutory 72 h deadline.
- **TrainMovement** — charted WTT path over a section: entry, exit, class, priority.
- **GoodsForecast** — probabilistic freight rake with a target window and priority weight.
- **BlockWindow** — officially charted corridor block opportunity in the WTT.
- **Resource** — machine (`BCM`, `CSM`, `UNIMAT`, `TRT`, `DGS`, `TOWER_WAGON`) or gang,
  with a home depot; a resource is in one place at one time (HC-009).
- **Dependency** — hard precedence between tasks (`FINISH_TO_START` with optional lag).
- **Block** — the scheduled possession the optimizer produces.
- **Plan** — versioned envelope of blocks, assignments, unassigned tasks, metrics,
  explanation and solver metadata.

## Block types (Ground Reality Report §2.3)

`TRAFFIC` · `POWER` · `INTEGRATED` · `SHADOW` · `DISCONNECTION` · `MEGA` · `EMERGENCY`

A **shadow block** is a possession on a line that is idle *because of* a primary block
elsewhere on the corridor — it is free capacity, and detecting it is a differentiator.

## What RailOS is not

The platform proposes. Authorized railway personnel dispose. No plan reaches
`APPROVED` without a human. All source-system adapters in this prototype are
synthetic; none is a real TMS/SMMS/TDMS/COA/BDMS integration.
