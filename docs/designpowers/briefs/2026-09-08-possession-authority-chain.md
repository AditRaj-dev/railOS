# Design Brief: Possession Authority Chain

## Problem Statement
Railway possession plans currently stop at abstract approval. Control-room and field staff need a shared, auditable authority chain from day-of clearance through isolation, live work, testing, handback, and block-burst normalisation.

## Users
- Section Controller working under time pressure on a keyboard-driven desktop.
- Station Master and TPC making statutory, online-only safety assertions.
- Engineering, S&T, and field supervisors working one-handed, in bright light, with intermittent connectivity and high cognitive load.
- Low-vision, colour-blind, limited-motor, screen-reader, and non-native-English users across those roles.

## Design Direction
Extend the existing graphite-and-signal-amber RailOS system. The server owns transition legality and returns role-filtered `allowedActions`; clients present that truth with explicit labels, rule citations, disabled reasons, and clear online/offline feedback.

## Constraints
- Preserve optimizer semantics and the two existing authentication mechanisms.
- Flutter remains the field surface; `/field` becomes read-only.
- All safety-authority actions require current online state; replay is limited to physical observations already performed.
- WCAG AA contrast, visible focus, non-colour status cues, 44px/48dp targets, semantic headings, and resilient text scaling are mandatory.

## Existing Design System
`DESIGN.md`, `DESIGN_SYSTEM.md`, `apps/control-center/src/components/tokens.ts`, and `apps/field-app/lib/theme/`.

## Taste Direction (Early Signal)
Controlled urgency and technical confidence: graphite canvas, signal amber wayfinding, muted semantic status colours, precise typography, and low-noise operational surfaces.

## Success Criteria
A power block can be sanctioned by the required authorities, deferred, isolated, protected, worked, tested, handed back, closed, and reflected in block-burst analytics without either client reimplementing transition rules.

## Out of Scope
Optimizer rule changes, auth-system unification, a Flutter router rewrite, and presenting synthetic or backfilled records as complete statutory evidence.
