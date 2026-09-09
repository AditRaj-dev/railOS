# Design State: RailOS Control Center

_Last updated: 2026-09-09 by implementation-orchestrator_

## Brief
- **Problem:** ENGG, SNT, and TRD teams need one auditable intake that turns guided departmental requests into canonical Block Finder inputs and visible Operational Gantt demand.
- **Primary persona:** Department supervisors submitting work under pressure; Block Managers and Control Officers triage, plan, and track it.
- **Success metric:** Each department can submit a validated request, trace its linked task into Block Finder, and distinguish pending demand from generated or approved possession windows on the live Gantt.
- **Brief document:** `docs/designpowers/briefs/2026-09-09-department-ticket-dashboard.md`
- **Status:** Approved by the user on 2026-09-09.

## Personas
- Control officer — continuously monitors the corridor and coordinates operational response.
- Maintenance planner — balances possession windows, task dependencies, and train impact.
- Field supervisor — needs concise mobile assignments and unambiguous status updates.
- Inclusive spectrum — permanent, temporary, and situational visual, motor, cognitive, and motion needs are in scope.
- ENGG supervisor — submits Civil/P-Way work and verifies traffic-block constraints.
- SNT supervisor — submits signalling work and verifies disconnection/T-351 needs.
- TRD supervisor — submits OHE work and verifies power-block/isolation needs.
- Block Manager — triages cross-department demand and runs Block Finder without re-keying.

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
| 2026-09-08 | design-system-alignment | Align Flutter field app UI with Next.js control center design tokens and DESIGN.md | Unifies palette (graphite canvas, signal amber accent, muted semantic statuses, department badges) across desk and field, eliminates banned bright/neon cues, enforces min 48dp touch targets and WCAG AA contrast. |
| 2026-09-08 | possession-authority-orchestrator | Make the API the single source of truth for legal possession actions | Role-filtered `allowedActions`, structured errors, and checklist state keep desktop and mobile clients from duplicating safety logic. |
| 2026-09-08 | possession-authority-orchestrator | Execute three file-disjoint workstreams in Auto mode | The user explicitly requested parallel subagent completion; backend/model, Flutter, and Next.js ownership do not overlap. |
| 2026-09-08 | backend-luna | Require typed T/351 reconnection and OHE re-energisation before close | Terra review reproduced unsafe bypasses; server-owned gates now protect the statutory handback chain. |
| 2026-09-08 | desk-design-builder-luna | Use query-authenticated WebSocket invalidation plus TanStack Query cache invalidation | Native browser sockets cannot set custom headers; API remains the authoritative source. |
| 2026-09-08 | implementation-orchestrator | Restore geographic-map regression coverage and add WebGL2/matchMedia fallbacks | Existing test deletion masked a compatibility regression; fallback states must work in non-WebGL test/browser environments. |
| 2026-09-09 | user | Approve unified ticket hub plus embedded Gantt intake | The user explicitly replied “appeoved” to the recommended direction. |
| 2026-09-09 | design-discovery | Model tickets as canonical BlockRequests linked to MaintenanceTasks | Separates request lifecycle from executable work while keeping one optimizer task representation. |
| 2026-09-09 | design-strategist | Keep structured preview visible throughout guided intake | Safety-relevant fields cannot be hidden in or inferred silently from a chat transcript. |
| 2026-09-09 | design-strategist | Render pending requests in a separate patterned Gantt lane | Operational intent must not resemble an approved possession. |
| 2026-09-09 | Luna backend preflight | Implement ticket persistence in the main domain repository and migrate the existing minimal block_requests table | Evidence storage is unrelated; request/task creation must be atomic and Postgres-rehydratable. |
| 2026-09-09 | Luna backend preflight | Unify JWT and demo-header identity before ticket authorization | Current main API and real login use incompatible authentication paths. |
| 2026-09-09 | Terra frontend preflight | Add requested-window placement and task/request/plan lineage | Pending Gantt bars and Block Finder selection otherwise lack truthful semantics. |
| 2026-09-09 | Terra frontend preflight | Add repeatable browser E2E and truthful synthetic connection copy | The repository has no E2E runner and current LIVE labels contradict API provenance. |
| 2026-09-09 | user | Approve department ticket dashboard implementation plan | The user explicitly replied “approve plan”; implementation may proceed with Luna and Terra workstreams. |
| 2026-09-09 | implementation-orchestrator | Complete design powers plan across Control Center and Field App | Executed CC-1 (Shell drawers, Next.js Link routing, StatusBar layout), CC-2 (Standardized QueryState vocabulary across all view components), CC-3 (A11y labels and focus management on forms), CC-4 (Token hygiene, shadow removal, check_token_sync.py in CI), FA-1 (Field correctness, upload error non-pop, empty queue guard, action-keyed loading), FA-2 (Field 4-destination NavigationBar shell, persistent EmergencyAppBarAction on all screens, onGenerateRoute table), FA-3 (Field typography & theme scaling), and comprehensive T-1 test suites. |
| 2026-09-09 | implementation-orchestrator | Opportunistic Tailwind token consolidation & token sync CI | Cleaned 51 duplicate variables from globals.css; added python script check_token_sync.py in CI to enforce zero token drift between canonical packages/design-tokens, Next.js CSS, and Flutter Dart. |
| 2026-09-09 | implementation-orchestrator | Preserve uncommitted forms and isolate DigitalTwinView/schematic | Strict boundary preserved for user uncommitted files (TicketComposer, TicketDashboardView, Evidence views) and orphaned DigitalTwinView. |

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
| Reported-area implementation plan | `docs/superpowers/plans/2026-09-08-all-india-railway-map-reported-areas.md` | Ready for execution review |
| Possession authority brief | `docs/designpowers/briefs/2026-09-08-possession-authority-chain.md` | Approved via user-supplied goal |
| Possession authority personas | `docs/designpowers/personas/2026-09-08-possession-authority-chain-personas.md` | Complete |
| Possession authority implementation plan | `docs/designpowers/plans/2026-09-08-possession-authority-chain-plan.md` | Approved for execution |
| Possession authority critique | `docs/designpowers/critiques/2026-09-08-possession-authority-chain.md` | Complete |
| Possession authority verification | `docs/designpowers/verification/2026-09-08-possession-authority-chain.md` | Complete with environment caveats |
| Department ticket brief | `docs/designpowers/briefs/2026-09-09-department-ticket-dashboard.md` | Approved |
| Department ticket strategy | `docs/designpowers/strategy/2026-09-09-department-ticket-dashboard-strategy.md` | Complete |
| Department ticket plan | `docs/designpowers/plans/2026-09-09-department-ticket-dashboard-plan.md` | Approved for execution |

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

### 2026-09-08 possession-authority-orchestrator → Luna implementation team
> "The server owns legality: return role-filtered actions, explicit checklist state, rule citations, and structured recovery guidance. Backend/model, Flutter field, and Next.js desk work in separate trees; keep the graphite-and-signal-amber system, make every safety state legible without colour, and preserve the repository's existing dirty changes."

### 2026-09-08 backend-luna → Terra reviewer
> "T/351 reconnection, server-clock lead-ins, day-of clearance, occupancy conflicts, transactional sanctions, typed re-energisation, and browser query authentication are now covered. Focused authority/API tests pass; PostgreSQL restart evidence still needs infrastructure."

### 2026-09-08 desk-design-builder-luna → Terra reviewer
> "The desk workflow now has role-aware sanctioning, possession board/detail, block-burst analytics, and a read-only field monitor. All 71 tests, TypeScript, and targeted lint pass; the map fallback regression was restored and repaired during integration review."

### 2026-09-09 design-discovery → design-strategist
> "Preserve a single operational truth: ENGG, SNT, and TRD submit through one chat-assisted intake, but every conversational answer becomes a visible, editable structured field before submission. Pending requests must look different from approved possession bars, and synthetic/demo provenance must remain explicit everywhere."

### 2026-09-09 design-strategist → implementation team
> "Build the request lifecycle around canonical BlockRequest-to-MaintenanceTask linkage, not a frontend-only ticket model. The experience should feel like an operational checklist in conversational sequence: visible structure, explicit recovery, and no ambiguity between REQUESTED demand and authorized possession."

### 2026-09-09 Luna backend preflight → implementation team
> "Create the typed model and department/task mapping first, then implement the transactional API against the existing Repository/PostgresRepository; do not modify optimizer rules until request-to-task mapping is proven. Fix JWT-versus-demo authentication and assert the full request-to-event trace before frontend live testing."

### 2026-09-09 Terra frontend preflight → implementation team
> "Build the typed ticket layer first, then the composer/dashboard, pass selected linked task IDs into Block Finder, and render requests in a dedicated semantic Gantt lane. Treat synthetic provenance as a global operational state and add repeatable browser-E2E infrastructure before claiming the live flow is covered."

### 2026-09-09 implementation-orchestrator → verification
> "The reliability pass closed the evidence and ticket lifecycle gaps: file reads now gate submission, demo upload returns the typed evidence/manifest envelope, multipart completion verifies parts and hashes, and evidence access is scoped. Ticket queues now expose API-authorized accept/reject/cancel actions with mandatory reasons; authenticated event streams and query retries preserve live state."

## 2026-09-09 Reliability Review Findings

- Critical evidence contract mismatch fixed: demo upload now returns `{ evidence, manifest }`, imports its media/hash dependencies, validates JPEG/MP4 payloads, and rejects malformed base64.
- Critical upload integrity gap fixed: task/step ownership, media kind, idempotency scope, multipart completeness, declared size, and SHA-256 are checked before evidence enters verification.
- Major ticket workflow gap fixed: `PATCH /api/v1/block-requests/{request_id}/status` is role-gated, reason-required, emits an audit event, and returns `allowedActions`.
- Major auth/realtime gap fixed: expired sessions stay on Bearer identity until refresh fails; WebSocket accepts access tokens and invalidates evidence, task, ticket, plan, possession, and analytics caches for relevant events.
- Validation: 160 backend tests, 19 frontend test files / 98 tests, Next production build, and Python compileall pass. ESLint has 14 warnings and no errors.
