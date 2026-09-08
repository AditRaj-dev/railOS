# 04 — "Why This Plan?" Rationale Panel: Implementation Plan

**Status:** NOT STARTED. Placeholder shipped, wiring pending.
**Prerequisite:** none — all required data already exists in the canonical models.
**Self-contained:** implementable from this file alone. No prior conversation needed.

---

## 1. Why this exists

`mapplan.md`, section 4, requires:

> Remove Gemini-generated operational recommendations from the map. **"Why this plan?" must render optimizer factors, warnings, and objective breakdown.** Any future copilot remains a read-only, source-linked explanation surface and cannot generate or approve schedules.

The removal half is **done** (§2). This document covers the replacement half.

## 2. What was already removed

Deleted outright:

- `apps/control-center/src/app/api/gemini/route.ts` — and the now-empty `src/app/api/` directory.

Stripped from `apps/control-center/src/components/DigitalTwinView.tsx`:

- `aiAnalysis` / `isLoadingAi` state
- `handleRunAiAnalysis` (POSTed section/defects/tasks/trains to `/api/gemini`)
- the "Run Gemini Pro Corridor Assessment" button and its `Sparkles` import
- the panel body that rendered the model output

**Why it went rather than getting its missing dependency declared:** the route's no-API-key branch returned a *hardcoded* string presented as analysis — naming a specific window (`13:45-15:00`), freight rake (`BOXN-99`), circuit breakers (`CB-21/24`), point machine (`204B`), stamped `confidence: 0.94` and `source: 'Deterministic RailOS Operational Knowledge Base'` — while ignoring the `defects`, `tasks` and `trains` the caller actually posted. Only `section.name` and a defaulted `capacityUtilizationPct` were interpolated. With no key configured (the default for any fresh checkout, CI run, or demo machine) a controller saw invented possession instructions that looked derived from live corridor state. `DigitalTwinView`'s `catch` block repeated the same trick with a second hardcoded paragraph. Do not reintroduce that pattern in any form.

In its place, `DigitalTwinView.tsx` now renders a labelled placeholder ("Why This Plan?" / "Not Wired") pointing at this document. That placeholder is what you replace.

## 3. The data already exists — do not compute anything in the UI

All of it is on the canonical `Plan`. Source of truth: `packages/railos_model/railos_model/models.py`.

| Need | Field | Defined at |
|---|---|---|
| Objective breakdown | `Plan.objectiveBreakdown: dict[str, float]` | `models.py:395` |
| Warnings | `Plan.warnings: list[str]` | `models.py:391` |
| Which profile ran | `Plan.objectiveProfile: ObjectiveProfile` | `models.py:388` |
| Per-assignment factors | `Assignment.explanation: list[Factor]` | `models.py:350` |
| Factor shape | `Factor{name, raw, weight, contribution, note}` | `models.py:295` |
| Work that did not fit, and why | `UnassignedTask{taskId, reason}` | `models.py:366` |
| Plan quality metrics | `Plan.metrics: PlanMetrics` | `models.py:370` |
| Solver status / provenance | `Plan.solverStatus`, `Plan.runtime`, `Plan.provenance` | `models.py:396-398` |

`Factor` carries its own docstring: *"One named, weighted contribution. Weights are never hidden."* That is the design intent of this panel — render name, raw, weight and contribution, not a prose summary of them.

Also available for task-level rationale, already exposed as API endpoints:

- `GET /api/v1/maintenance/priority` → `PriorityResult{taskId, score, band, factors}` (`models.py:305`)
- `GET /api/v1/maintenance/risk` → `RiskResult{...,  basis}` (`models.py:312`). Note `RiskResult.basis` defaults to `"deterministic heuristic, not a trained model"` — surface that string verbatim; it is an honesty guarantee, not decoration.

## 4. Files to touch

| File | Change |
|---|---|
| `apps/control-center/src/components/PlanRationale.tsx` | **new** — presentational panel. Props only, no fetching. |
| `apps/control-center/src/components/DigitalTwinView.tsx` | replace the "Not Wired" placeholder block with `<PlanRationale/>`. Grid cell is `lg:col-span-5`; keep it. |
| `apps/control-center/src/lib/queries.ts` | add `usePlanDetail(planId)` if not already present; it is the data source. |
| `apps/control-center/src/lib/api.ts` | confirm `getPlanDetail(planId, version?)` maps `GET /api/v1/block-plans/{planId}` (+ `?version=`). Handler: `apps/api/railos_api/main.py`, `plan_detail`. |
| `apps/control-center/src/components/tokens.ts` | reuse `OBJECTIVE_TOKENS` for the profile chip and status tokens for warnings. Do not invent a local palette. |
| `apps/control-center/src/components/StatusChip.tsx` | reuse for warning severity. Colour must never be the only signal. |

## 5. Panel contents

Four stacked sections, in this order:

1. **Objective** — the `objectiveProfile` as a chip via `OBJECTIVE_TOKENS`, plus `objectiveBreakdown` as a labelled bar or table of term → weight. Show the raw numbers; do not normalise them away.
2. **Factors** — for the selected block/assignment, `Assignment.explanation` rendered as a `Factor` table: name, raw, weight, contribution, note. This is the core of the requirement.
3. **Warnings & unassigned** — `Plan.warnings` as a list, and `Plan.unassigned` as `taskId → reason` pairs. Work that did not fit must be visible; `mapplan.md` requires infeasible results, warnings and unassigned tasks be preserved rather than hidden.
4. **Provenance** — `solverStatus`, `runtime`, `provenance`, and the `synthetic` flag. The plan requires synthetic provenance be displayed and forbids presenting demo output as authoritative.

## 6. Hard constraints

- **No LLM call.** Not on this panel, not behind a flag. `mapplan.md` permits a future copilot only as a read-only, source-linked explanation surface that "cannot generate or approve schedules" — this panel is not that copilot and must not become its entry point.
- **No fabricated fallback.** When there is no plan, render an explicit empty state ("no plan generated for this section"). Never synthesise plausible-looking numbers, windows, rake IDs or equipment IDs. This is the specific failure of the removed route.
- **No computation in the UI.** Every number rendered comes from the API response. If a value you want is not on `Plan`, add it in the optimizer/API layer, not in TypeScript.
- **Accessibility.** Every status carries text or an icon in addition to colour, matching the rest of the app.
- **Planning-disabled territory.** For sections where `planningEnabled === false`, show the empty state — those regions are overview-only and have no plan to explain.

## 7. Verification

```bash
cd apps/control-center && npm run build && npm run lint
```

Build must succeed and the panel must render from real API data with the dev API running. Then confirm the backend is untouched:

```bash
.venv/Scripts/python.exe -m pytest -q
```

Expected `98 passed` or better. Never weaken a test to make it pass.

Manual check: generate a plan for a Ghaziabad–Aligarh section (the only planning-enabled corridor), open the Digital Twin view, and confirm every displayed number is traceable to a field in the `/api/v1/block-plans/{planId}` response body. If a number cannot be traced to the response, it is fabricated and must be removed.
