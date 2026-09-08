# RailOS Production-Foundation Implementation Plan

## Summary

Evolve the existing synthetic control-center into an API-backed regional pilot with:

- A MapLibre geographic overview and React/SVG schematic operations view sharing one network model.
- Six clearly labelled synthetic zones, with Ghaziabad–Aligarh as the only fully planning-enabled corridor initially.
- PostgreSQL/PostGIS persistence, Martin vector-tile support, provider-neutral OIDC, and a containerized deployment.
- Existing command-center, maintenance, planner, comparison, analytics, emergency, and field workflows connected to canonical backend contracts.
- Preservation of the current baseline: 77 backend tests passing, frontend lint/build passing, and existing uncommitted UI work retained.

## Implementation Changes

### 1. Establish the canonical backend and data model

- Create a recoverable repository boundary before editing; exclude `node_modules`, `.next`, caches, generated schemas, and secrets while preserving current UI work.
- Replace the API’s independently generated 267-task seed with `railos_data.load_world("datasets")`; standardize corridor and section IDs across datasets, API responses, optimizer output, map features, and frontend URLs.
- Extend canonical Pydantic contracts with `RailwayZone`, `RailwayDivision`, `RailwaySection`, `RailwaySegment`, `Station`, summary metrics, geometry, planning-enabled status, and provenance.
- Seed six synthetic zones and their hierarchy, but mark only the canonical Ghaziabad–Aligarh corridor as planning-enabled. Other regions remain overview-only and must not expose a functioning Generate Plan action.
- Require every generated plan to pass the independent optimizer audit before being returned. Preserve infeasible results, warnings, unassigned tasks, safety margins, and solver provenance.
- Fix approval semantics: add `REJECTED`, invoke the canonical approval operation, record approver identity in plan provenance, and retain immutable versions.
- Run optimization outside repository locks; store each completed candidate set atomically afterward.
- Add the missing opportunities, bundles, risk, priority, and scenario endpoints using the existing engines rather than reimplementing calculations in the API.

### 2. Build the production data and event foundation

- Replace the JSONB snapshot as the production source with normalized PostgreSQL tables and PostGIS geometry in SRID 4326. Retain the in-memory adapter for tests and synthetic local mode.
- Add spatial entities for zones, divisions, sections, segments, stations, assets, defects, and block geometry; index hierarchy IDs, statuses, timestamps, and geometry.
- Assemble `ScenarioWorld` from the normalized repository before optimization so API, map, and solver use identical records.
- Persist domain events and audit records transactionally. Use PostgreSQL notification plus sequence-based replay for WebSocket fan-out and reconnection; do not add Redis for the regional pilot.
- Serve controlled GeoJSON in local/demo mode. In production mode, expose track and point layers through Martin vector tiles while keeping detail, search, metrics, and mutations in FastAPI.

### 3. Refactor the control-center application

- Declare all currently implicit dependencies and add MapLibre, focused deck.gl packages, Zustand, TanStack Query, D3 scale/shape utilities, OIDC support, and frontend test tooling.
- Convert screen selection into Next.js routes with a persistent shell and right context rail. Use URL parameters such as `zone`, `division`, `section`, `mode`, and `horizon` for shareable map-to-planner navigation.
- Generate TypeScript API types from OpenAPI/JSON Schema. Centralize API calls, authentication, error mapping, and conversion between horizon-relative minutes and display timestamps.
- Keep Zustand limited to UI state: current territory selection, map mode, viewport, visible layers, active drawer, and transient workflow state. Put server data and mutations in TanStack Query.
- Connect existing screens to API data and mutations, retaining fixtures only behind an explicit synthetic-data mode.
- Implement the design system as semantic Tailwind/CSS tokens for surfaces, typography, spacing, status, department, objective, focus, and elevation. Replace hardcoded status colors and ensure every critical state has text/icon redundancy.
- Complete the desktop shell’s territory selector, environment label, role-aware navigation, right context panel, and bottom synchronization/plan status bar.

### 4. Deliver the dual-map experience

- Geographic view: MapLibre supplies geographic context and hierarchy navigation; deck.gl supplies railway paths, risk/maintenance styling, defects, active blocks, and opportunities.
- Schematic view: React owns SVG components while D3 performs topology spacing, scales, and path calculations. Display stations, up/down tracks, blocks, assignments, trains, safety lead-in/handback margins, and dependencies.
- Implement hierarchy navigation from railway → zone → division → section, with breadcrumbs, tree selection, search, hover summaries, context details, and zoom-dependent layer visibility.
- Support Maintenance, Risk, Operations, and Opportunity modes. Availability metrics remain visible in context panels rather than becoming a separate renderer mode.
- Synchronize selection with maintenance filters, analytics, timelines, and planner deep links. “Plan for this Section” carries the canonical territory and horizon into the planner.
- Remove Gemini-generated operational recommendations from the map. “Why this plan?” must render optimizer factors, warnings, and objective breakdown. Any future copilot remains a read-only, source-linked explanation surface and cannot generate or approve schedules.
- Clearly display `Synthetic` provenance on map data and simulated trains. Do not present generalized demo lines as authoritative railway geometry.

## Public Interfaces

- Add read endpoints for the network hierarchy, section details, bounded GeoJSON features, and cross-entity search.
- Add engine-backed endpoints for opportunities, bundles, maintenance priority/risk, and simulator scenarios.
- Preserve the current optimization, approval, emergency, replanning, assignment, analytics, and event routes while aligning their responses to canonical schemas.
- Production requests use `Authorization: Bearer <OIDC JWT>` with claim-to-role mapping. Existing `X-RailOS-*` headers remain available only when the server explicitly runs in local synthetic mode.
- Map feature properties include canonical entity IDs, hierarchy IDs, summary metrics, `planningEnabled`, `synthetic`, and provenance.
- Martin exposes read-only vector-tile sources; no business mutation or authorization decision is performed through the tile service.

## Verification and Rollout

- Backend tests cover canonical dataset loading, ID joins, PostGIS queries, role enforcement, audit-before-return, infeasible plans, unassigned work, rejection/approval provenance, optimistic version conflicts, and event replay.
- Frontend tests cover schema mapping, minute/time conversion, semantic status rendering, hierarchy selection, layer visibility, context synchronization, planner deep links, and loading/error/empty states.
- End-to-end scenarios cover map-to-task navigation, section-to-plan generation, candidate comparison and approval, emergency replanning, field updates, WebSocket reconnection, and blocked planning for overview-only regions.
- Accessibility verification covers keyboard map alternatives, visible focus, contrast, labels beyond color, reduced motion, and responsive field workflows.
- Container integration tests start Next.js, FastAPI, PostGIS, and Martin; run migrations and seed import; verify health checks, OIDC configuration failure behavior, API access, tiles, and WebSockets.
- Release in stages: canonical contracts/API correctness, database and identity, API-backed existing screens, geographic map, schematic map and cross-screen linkage, then container hardening and pilot acceptance.
- Record ADRs for the dual-map architecture, Zustand versus TanStack Query ownership, PostGIS/Martin adoption, PostgreSQL-backed events, and provider-neutral OIDC.

## Assumptions

- Initial validation targets a regional pilot, not a national operational rollout.
- The six-zone dataset is synthetic and provenance-labelled; Ghaziabad–Aligarh is the sole end-to-end optimizer corridor in the first release.
- Deployment is cloud-neutral and containerized, with TLS termination and OIDC provider configuration supplied by the hosting environment.
- Full India GIS completeness, real train telemetry, advanced geospatial editing, and national-scale load certification remain later milestones.
