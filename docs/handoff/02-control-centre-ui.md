# HANDOFF -> Antigravity (Control Centre & Field PWA)

**CHANGE:**
There is now real planning output to render. Everything below comes out of
`optimizer.solve()` / `replan()` as JSON; nothing needs to be invented in the UI.

**FILES:** read-only for the UI -- `schemas/Plan.schema.json`, `schemas/Opportunity.schema.json`,
`schemas/BundleCandidate.schema.json`, `schemas/PriorityResult.schema.json`,
`schemas/RiskResult.schema.json`.

**WHAT EACH SCREEN CAN BIND TO**

| Screen | Source |
|---|---|
| Time-distance / Gantt | `plan.blocks[]` (section, track, start, end, blockType) over `world.trains[]` |
| Block detail | `plan.assignments[]` filtered by `blockId`; each carries its own `explanation[]` |
| "Why this plan?" panel | `assignment.explanation[]` + `plan.objectiveBreakdown` -- **display these numbers, do not ask an LLM to invent reasons** |
| Opportunities view | `GET /opportunities`; `blockType == SHADOW` deserves its own visual treatment |
| Demanded vs Granted | `metrics.tasksScheduled` vs `tasksScheduled + tasksUnassigned` |
| Block burst risk | `unused_window_penalty` factor per assignment (SO-005) |
| Coordination ratio | `metrics.coordinationRatio` -- share of blocks with more than one department |
| Deferred work list | `plan.unassigned[]` with its `reason` -- never hide this list |
| Obligations panel | `plan.warnings[]` -- T/409 caution orders, T/351, PTW, SR footprint |
| Replan diff | `{added, removed (displaced), moved, metricDeltas}` from `/replanning/propose` |
| Approval | button calls `/plans/{id}/approve`; a `PROPOSED` plan must look visibly unapproved |

**CONSTRAINT EFFECT ON THE UI:**
- Time is integer minutes from `horizonStartIso`. `D1 00:02` in the CLI is
  `minute 2`. Do the conversion once, in one helper.
- Three objective profiles are three weight vectors over one model. Present them as
  *alternatives to compare*, not as three different systems.
- `PROPOSED` never renders as a decided plan. Approval is a human act, and the
  screen must say who approved it (`plan.provenance`).
- Blocks are typed: `TRAFFIC / POWER / INTEGRATED / SHADOW / DISCONNECTION / MEGA /
  EMERGENCY`. Use the real vocabulary; controllers read those words daily.
- A block spans the *possession*, not the work: the 20-minute PTW lead-in and the
  15-minute handback are inside `block.start..block.end` but outside
  `assignment.start..assignment.end`. Draw that gap -- it is the safety margin.

**MIGRATION REQUIRED:** none, no UI exists yet.

**TESTS:** run `railos plan -v` to see exactly the fields a screen can bind to,
and `railos replan --scenario critical_defect` for the emergency flow.

**EXAMPLE INPUT / OUTPUT:** see `docs/handoff/01-optimization-api.md`.
