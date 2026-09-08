# Design State: RailOS Control Center

_Last updated: 2026-09-08 by implementation-planning_

## Brief
- **Problem:** Railway control teams need one legible operational workspace for monitoring corridor state, planning maintenance blocks, comparing feasible plans, and responding to disruption.
- **Primary persona:** Control officers and planners working under time pressure on desktop displays; field supervisors use the companion mobile view.
- **Success metric:** A user can identify current network risk, move to the relevant planning view, compare candidates, and take the next safe action without losing operational context.
- **Brief document:** `RailOS Platform — Six Integrated Product Requirement Documents.md`
- **Status:** Inferred from the existing product documentation and frontend for this review.

## Personas
- Control officer — continuously monitors the corridor and coordinates operational response.
- Maintenance planner — balances possession windows, task dependencies, and train impact.
- Field supervisor — needs concise mobile assignments and unambiguous status updates.
- Inclusive spectrum — permanent, temporary, and situational visual, motor, cognitive, and motion needs are in scope.

## Design Principles
1. Operational truth before decoration — live, delayed, synthetic, and emergency states must be unmistakable.
2. Decision hierarchy under pressure — each view makes the primary next action and its consequences clear.
3. Dense but scannable — use alignment, typography, and restrained color to organize complexity.
4. Accessible by default — keyboard, contrast, motion, text scaling, and non-color cues are part of every component.
5. One system across desk and field — shared semantics and status language adapt to each device context.

## Taste Profile
- **Emotional target:** controlled urgency, technical confidence
- **Quality level:** Flagship hackathon demo
- **Key references:** Existing RailOS design system and operational railway control-room conventions
- **Aesthetic principles:** Graphite operational canvas, signal-amber wayfinding, muted field-status colors, precise typography, low-noise surfaces
- **Taste document:** `DESIGN_SYSTEM.md`

## Decisions Log

| Date | Agent | Decision | Rationale |
|------|-------|----------|-----------|
| 2026-09-08 | design-review | Use the Review lane on the existing Next.js control center | The artefact exists and the user asked to apply Designpowers to it. |
| 2026-09-08 | design-review | Treat the review brief as inferred | Product documentation and code provide enough context to begin without a discovery cycle. |
| 2026-09-08 | design-lead | Replace blue-purple dashboard palette with graphite + signal amber | Removes generic AI SaaS cues while preserving high-salience operational wayfinding. |
| 2026-09-08 | Luna research | Retain MapLibre and deck.gl, add a dedicated MapLibre bridge, viewport-aware delivery, PMTiles/PostGIS/Martin path, and explicit provenance | Fits the existing stack while separating public OSM geometry from authorized railway operational data. |
| 2026-09-08 | implementation-orchestrator | Split map implementation into frontend, backend API, and ingestion workstreams with disjoint file ownership | Allows parallel work without overwriting the existing dirty worktree. |
| 2026-09-08 | implementation-planning | Use hosted OpenRailwayMap raster tiles plus seeded reports anchored to RailOS vector segments | Delivers nationwide visible track coverage now while preserving an API-compatible report contract and honest accuracy boundary. |

## Open Questions
- [x] Primary immediate workflow: show all-India railway tracks and simulated track-aligned reported areas on the Network map.

## Artefact Index

| Artefact | Path | Status |
|----------|------|--------|
| Product requirements | `RailOS Platform — Six Integrated Product Requirement Documents.md` | Existing |
| Design system | `DESIGN_SYSTEM.md` | Existing |
| Frontend | `apps/control-center` | In review |
| Railway map implementation plan | `docs/designpowers/plans/2026-09-08-railway-map-implementation-plan.md` | Approved for execution |
| Reported-area design brief | `docs/designpowers/briefs/2026-09-08-all-india-railway-map-reported-areas.md` | Approved |
| Reported-area design spec | `docs/superpowers/specs/2026-09-08-all-india-railway-map-reported-areas-design.md` | Approved |

## Design Debt Register

_Items: 4 | Critical: 1 | Oldest: 2026-09-08_

| ID | Date | Source | Severity | What | Who is affected | Suggested fix | Status | Notes |
|----|------|--------|----------|------|----------------|---------------|--------|-------|
| DP-001 | 2026-09-08 | design-review | Critical | Narrow view had no discoverable operational navigation | Mobile and situational users | Add labeled mobile view selector | Fixed | Verified in source; browser recheck limited by session usage cap |
| DP-002 | 2026-09-08 | design-review | Major | Task and block rows used non-semantic clickable divs | Keyboard and screen-reader users | Replace with focusable buttons and labels | Fixed | Command Center rows updated |
| DP-003 | 2026-09-08 | design-review | Major | Dense labels and fixed viewport math reduced readability | Low-vision and mobile users | Responsive type/layout tokens and `100dvh` | Fixed | Global shell and metrics updated |
| DP-004 | 2026-09-08 | design-review | Existing lint warnings remain in untouched components | Maintainers | Clean unused imports in a follow-up pass | Deferred | No build errors; warnings are non-blocking |

## Handoff Chain

_Assessment independence: degraded — the three reviewer slots were unavailable due account usage limits. Manual source review, live browser inspection, and deterministic detector evidence were used instead._

### 2026-09-08 design-review → design-builder
> "The shell is now responsive and the Command Center's risk and possession rows are real controls. Keep the dark operational canvas, but treat navigation, focus, and readable data as safety features—not polish." 

### 2026-09-08 Luna research → parallel implementation team
> "Keep MapLibre and deck.gl, but repair the lifecycle and use the MapLibre-specific bridge. Frontend owns rendering and selection, backend owns viewport contracts and geometry filtering, and ingestion owns source snapshots and reproducible railway normalization; never present OSM or synthetic geometry as official operational truth."
