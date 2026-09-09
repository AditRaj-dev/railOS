# Design Brief: Department Ticket Dashboard and Block Finder Intake

## Problem Statement

Engineering (Civil/P-Way), Signal & Telecommunication, and Traction Distribution teams currently have maintenance tasks and defects in RailOS, but no shared operational intake that lets a departmental user describe required work, verify the structured block constraints, and send it to the Block Manager. The Block Manager needs those submissions to become valid optimizer inputs without re-keying data, while planners need to see both pending demand and generated possession windows on the Operational Gantt.

## Users

- **Department supervisors (ENGG, SNT, TRD):** submit and track work requests, often under time pressure and sometimes from low-resolution or bright-control-room displays.
- **Block Manager / Planner:** triages requests, sees validation and provenance, and runs Block Finder against linked canonical maintenance tasks.
- **Control Officer:** reads pending requests and approved possessions together without confusing intent with authority.
- **Ability spectrum:** keyboard-only and screen-reader users, low-vision and colour-blind users, users with limited motor control, and staff working under high cognitive load or in a second language.

## Design Direction

Use a unified ticket hub with three department views and a chat-assisted intake. The conversation progressively asks for operational fields, while a structured preview remains visible and editable. Submission persists a canonical `BlockRequest` and creates a linked `MaintenanceTask`; the existing optimizer consumes that task. The Operational Gantt adds a clearly labelled pending-request lane with patterned/dashed bars, visually distinct from generated or approved possession windows.

## Constraints

- Preserve RailOS canonical models and optimizer semantics; do not duplicate maintenance-task representations.
- Reuse the existing FastAPI repository, typed Next.js API layer, TanStack Query cache, event stream, and RailOS design tokens.
- Unify authenticated identity for ticket routes so real JWT sessions and deterministic demo headers reach the same role/department authorization policy.
- Use only ENGG, SNT, and TRD as submitting departments.
- Important mutations require actor, timestamps, provenance, status, and audit/event records.
- Demo data remains deterministic and labelled `synthetic: true` / `Synthetic Hackathon Simulation`.
- WCAG 2.2 AA contrast, keyboard access, visible focus, text/error redundancy, and non-colour timeline distinctions are required.
- Test against the running API and control-center application in addition to unit/integration tests.

## Existing Design System

`DESIGN_SYSTEM.md`, `packages/design-tokens/tokens.json`, and `apps/control-center/src/app/railos_tokens.css`.

## Taste Direction (Early Signal)

Controlled urgency and technical confidence: graphite operational surfaces, signal amber as the branded accent, compact high-density layout, monospaced operational values, and no decorative chat bubbles or startup-style glass effects.

## Success Criteria

1. A user can select ENGG, SNT, or TRD and complete the chat-assisted ticket flow using pointer or keyboard.
2. Before submission, every answer is represented in an editable structured preview with validation and plain-language recovery guidance.
3. The API persists the block request, links a canonical maintenance task, emits an event, and returns explicit synthetic provenance.
4. The new task is visible to Block Finder and participates in a real optimizer run.
5. Pending requests appear in a distinct Operational Gantt lane; planned requests can be traced to their generated possession block.
6. The dashboard, Block Planner, Operational Gantt, and linked navigation are exercised against the running API with deterministic data.
7. Backend tests, frontend tests, type checking, lint/build checks, keyboard/accessibility checks, and a live-flow report all provide evidence.

## Out of Scope

- Natural-language AI extraction or external LLM calls; the chat interaction is deterministic guided intake.
- Connecting to production Indian Railways systems or representing synthetic data as official data.
- Changing optimizer objective semantics, automatic operational approval, or bypassing the existing sanction chain.
- Native mobile application changes.

## Operational Mapping

- The guided **department** answer selects one of the existing canonical values `ENGG`, `SNT`, or `TRD` and constrains the valid task-type choices.
- **Location** is captured as corridor, section, track, kilometre start/end, and either an explicit asset or a server-resolved asset within those bounds.
- **Urgency** maps through a documented server-owned table to integer severity/criticality and `dueMinute`; the client never invents optimizer scores.
- **Block need** captures requested traffic/power/disconnection intent and statutory flags, but the optimizer remains authoritative for the eventual block type.
- **Requested window** captures earliest start and latest finish. Pending Gantt demand uses that requested interval; if absent, the server returns a validation error rather than placing a misleading bar.
- Every plan assignment/unassigned result exposes the linked `requestId` through the canonical `taskId` lineage.

## Approval

Approved by the user on 2026-09-09 in response to the recommended unified ticket hub and embedded Operational Gantt direction.
