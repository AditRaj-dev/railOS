# Design Plan: Possession Authority Chain

> **For agentic workers:** Review completed work against this plan and the source implementation plan at `C:\Users\study\.claude\plans\yeah-build-out-the-foamy-swing.md`.

**Goal:** Deliver the backend authority contract, Flutter field workflow, and Next.js control dashboard for the full possession lifecycle.

**Design Direction:** `docs/designpowers/briefs/2026-09-08-possession-authority-chain.md`

**Personas:** `docs/designpowers/personas/2026-09-08-possession-authority-chain-personas.md`

## Workstream 1: Backend and canonical model

**Files:** `apps/api`, `packages/railos_model`, backend tests

- Complete role normalization, sanction chains, possessions, notifications, replay safety, block bursts, persistence registration, and compatibility guards.
- Preserve plan/optimizer semantics and structured error conventions.

**Accessibility check:** APIs expose plain-language error messages, role-filtered `allowedActions`, checklist state, and rule citations so clients do not infer safety state.

**Verification:** Backend tests pass, including new authority/handback cases; PostgreSQL rehydration is attempted when infrastructure is available.

## Workstream 2: Flutter field surface

**Files:** `apps/field-app`

- Persist offline evidence, cached data, and sessions; flush replay-safe writes on reconnect.
- Add role-aware possession, isolation, work, and handback screens.
- Align theme, labels, form feedback, manifests, and evidence strip with the shared system.

**Accessibility check:** 48dp targets, text scaling, visible labels, semantic/non-colour states, bright-light contrast, and clear offline rejection reasons.

**Verification:** Flutter analysis/tests pass, including persistence and enqueue-policy coverage where feasible.

## Workstream 3: Next.js desk dashboard

**Files:** `apps/control-center`

- Make role selection real across navigation and API headers.
- Add sanction-chain, possession board/detail, block-burst analytics, and read-only field monitor views.
- Reuse status primitives and implement accessible dialog/table patterns where needed.

**Accessibility check:** Keyboard operation, focus visibility/trapping, semantic tables/headings, descriptive labels, live feedback, responsive reflow, and non-colour status cues.

**Verification:** Control-center tests, lint, and build/type checks pass; the possession board consumes WebSocket events and server-provided `allowedActions`.

## Integration and review

- Run a Terra review across the merged workstreams, prioritising contract mismatches, regressions, accessibility, and missing tests.
- Apply critical and major fixes in file-disjoint follow-up rounds.
- Run the strongest available backend, Flutter, and Next.js verification; clearly report any device/database/live-demo checks that require unavailable infrastructure.
