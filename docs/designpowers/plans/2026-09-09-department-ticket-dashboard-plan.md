# Design Plan: Department Ticket Dashboard and Block Finder Intake

> **For agentic workers:** REQUIRED: Use `designpowers-critique` to review completed work against this plan.

**Goal:** Deliver a tested three-department ticket workflow from guided user input through Block Finder and the Operational Gantt using the live RailOS API.

**Design Direction:** `docs/designpowers/briefs/2026-09-09-department-ticket-dashboard.md` and `docs/designpowers/strategy/2026-09-09-department-ticket-dashboard-strategy.md`

**Personas:** ENGG, SNT, and TRD supervisors; Block Manager/Planner; Control Officer; inclusive ability spectrum in the approved brief.

---

## Task 1: Canonical block-request contract

**Files:** `packages/railos_model/railos_model/models.py`, `packages/railos_model/railos_model/enums.py`, `packages/railos_model/railos_model/__init__.py`, model tests

- [ ] Add typed request status and `BlockRequest` lifecycle model with linked-task and provenance fields.
- [ ] Validate department-specific task types, durations, track, kilometre range, severity, and block type.
- [ ] Define one server-owned mapping for guided urgency/block-need answers and requested earliest/latest window fields.
- [ ] Export the canonical contract without duplicating `MaintenanceTask`.

**Accessibility check:** API validation returns field-specific, plain-language details usable by assistive UI.

**Verification:** Model validation tests cover valid ENGG/SNT/TRD requests and invalid boundary cases.

## Task 2: Auditable ticket API and task conversion

**Files:** `apps/api/railos_api/main.py`, `apps/api/railos_api/auth.py`, `apps/api/railos_api/evidence_routes.py`, `database/migrations/003_block_request_intake.sql`, `tests/test_api_tickets.py`, `apps/api/openapi.json`

- [ ] Add list/detail/create endpoints with department, status, and section filters.
- [ ] Atomically persist the request and linked canonical maintenance task.
- [ ] Emit `BLOCK_REQUEST_CREATED`, record actor/provenance, and expose stable structured errors.
- [ ] Include requests in deterministic demo reset/seed behavior.
- [ ] Reconcile the existing minimal `block_requests` table and register the completed model for Postgres snapshot rehydration.
- [ ] Unify JWT and demo-header authentication for ticket routes; enforce server-derived department scope and cross-role triage permissions.
- [ ] Make creation idempotency-aware and regenerate checked-in OpenAPI after routes stabilize.

**Accessibility check:** Error envelopes identify the field, reason, and recovery action; no generic 500s.

**Verification:** FastAPI tests prove JWT/header authorization, department isolation, filtering, atomic persistence, idempotency, event/audit emission, task linkage, Postgres rehydration shape, reset determinism, and optimizer visibility.

## Task 3: Typed frontend data layer

**Files:** `apps/control-center/src/lib/api.ts`, `apps/control-center/src/lib/queries.ts`, `apps/control-center/src/lib/useRailOSEventStream.ts`

- [ ] Add `BlockRequest`, create payload/response, and filter types.
- [ ] Add query keys, list/detail hooks, and create mutation with precise invalidation.
- [ ] Invalidate request/task/planning data on the new domain event.
- [ ] Mount realtime invalidation in ticket, planner, and timeline scope (or once globally) so those screens update without reload.

**Accessibility check:** API errors preserve messages, request IDs, and field details for form recovery.

**Verification:** Unit tests cover request serialization, error mapping, and cache invalidation.

## Task 4: Guided ticket composer

**Files:** `apps/control-center/src/components/TicketComposer.tsx`, `apps/control-center/src/components/__tests__/TicketComposer.test.tsx`

- [ ] Implement deterministic conversational steps for department, location, track, work type, urgency, duration, and block need.
- [ ] Keep an always-visible structured preview with edit actions and explicit progress.
- [ ] Implement review, submit, success, server-error, and retry states.

**Accessibility check:** Semantic form controls, visible labels/focus, announced step and submission status, error summary with focus management, 44px targets, and no time limit.

**Verification:** Tests complete valid flows for all three departments plus keyboard navigation and error recovery.

## Task 5: Three-department ticket dashboard

**Files:** `apps/control-center/src/components/TicketDashboardView.tsx`, `apps/control-center/src/app/(shell)/tickets/page.tsx`, `apps/control-center/src/components/shell/AppShell.tsx`, component tests

- [ ] Add role-aware navigation and a shared queue with ENGG, SNT, and TRD filters/counters.
- [ ] Show status, task linkage, Block Finder readiness, timestamps, and synthetic provenance.
- [ ] Add loading, empty, stale, and failure states with retry.
- [ ] Permit department roles to reach `/tickets`, while planner/control roles retain cross-department triage and planning access.
- [ ] Replace misleading `CRIS/NTES FEED LIVE` and `LIVE API` copy with accurate synthetic-connection status.

**Accessibility check:** Table/cards remain operable at 200% zoom and on narrow screens; status uses text and icon/pattern redundancy.

**Verification:** Component tests cover each role/department, responsive rendering, filters, and navigation into planning.

## Task 6: Block Finder input surface

**Files:** `apps/control-center/src/components/BlockPlannerView.tsx`, relevant adapters/tests

- [ ] Surface submitted ticket/task counts and a filterable input summary before optimization.
- [ ] Trace generated assignments/unassigned warnings back to request IDs.
- [ ] Preserve current approval and safety-auditor behavior.
- [ ] Add an explicit selected linked-task set for Block Finder; do not imply that a visual count filters optimizer input unless the API receives and honours those task IDs.

**Accessibility check:** Counts, warnings, and result relationships are programmatically labelled and do not rely on colour.

**Verification:** Tests prove submitted requests are visible, optimizer action retains warnings, and task/request traceability renders.

## Task 7: Operational Gantt request lane

**Files:** `apps/control-center/src/components/TimelineGanttView.tsx`, `apps/control-center/src/components/__tests__/TimelineGanttView.test.tsx`

- [ ] Fetch pending/accepted requests and render them in a separate demand lane.
- [ ] Use dashed/patterned request bars with department and `REQUESTED` text, distinct from possession blocks.
- [ ] Add accessible details and links to the ticket or planner without requiring hover/drag.
- [ ] Position pending bars from the canonical requested earliest/latest window and expose a text-equivalent list.
- [ ] Use semantic buttons/links for request and possession bars; repair any touched clickable `<div>` patterns.

**Accessibility check:** Timeline information has textual equivalents, keyboard-focusable bars, sufficient contrast, and usable horizontal overflow.

**Verification:** Tests cover empty/loading/data/error lanes and visual/status distinctions.

## Task 8: End-to-end live-data flow

**Files:** browser E2E configuration/script, `apps/control-center/e2e/ticket-flow.spec.ts` or repository-appropriate location, API integration tests

- [ ] Start the real FastAPI app and Next.js control center against deterministic demo data.
- [ ] Add a repeatable browser-E2E runner to dependencies/scripts if the repository has none; otherwise document CUA evidence as supplemental rather than CI proof.
- [ ] Submit one ENGG, one SNT, and one TRD request through the visual composer.
- [ ] Verify dashboard persistence, linked tasks, Block Finder inputs/results, and Gantt request/possession rendering.
- [ ] Exercise every linked screen, keyboard-only completion, reload persistence, failure recovery, and provenance labels.
- [ ] Submit using each departmental role, then switch to PLANNER/CONTROL_OFFICER for Block Finder and Gantt verification.

**Accessibility check:** Complete the primary flow without a pointer; verify focus, announcements, zoom/reflow, and reduced-motion behavior.

**Verification:** Browser artifacts/screenshots and API evidence prove the full live flow rather than mocked component behavior.

## Task 9: Review, fix round, and report

**Files:** `docs/designpowers/critiques/2026-09-09-department-ticket-dashboard.md`, `docs/designpowers/verification/2026-09-09-department-ticket-dashboard.md`, `docs/reports/2026-09-09-ticket-dashboard-live-flow.md`

- [ ] Run design critic, accessibility, heuristic, and synthetic-persona reviews; reconcile findings.
- [ ] Apply critical/major fixes and rerun affected checks.
- [ ] Run backend tests, frontend tests, TypeScript, lint, build, and live browser flow.
- [ ] Record exact commands, results, screen coverage, data provenance, limitations, and remaining design debt.

**Accessibility check:** No unresolved critical accessibility or task-completion barrier may ship.

**Verification:** Report links every requested outcome to authoritative file, test, API, or browser evidence.

## Approval

Prepared from the user-approved unified ticket-hub direction. Approved for execution by the user on 2026-09-09.

## Preflight Review

- **Luna backend/domain preflight:** complete; corrected repository ownership, auth convergence, migration, idempotency, mapping, and optimizer-boundary requirements.
- **Terra frontend/verification preflight:** complete; added realtime mounting, role navigation, requested-window/lineage, provenance-copy, semantic Gantt, and repeatable browser-E2E requirements.
