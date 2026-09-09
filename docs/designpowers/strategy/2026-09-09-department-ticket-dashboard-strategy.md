# Design Strategy: Department Ticket Dashboard and Block Finder Intake

## Design Principles

### Conversation with visible structure
**The principle:** Guided questions reduce form burden only when the resulting operational record is always visible.
**In practice:** Show the current question beside a structured ticket preview; let users edit any captured field before submission.
**We will not:** Hide critical constraints inside a chat transcript or infer safety fields silently.

### Intent is not authority
**The principle:** A submitted work request must never look like an approved possession.
**In practice:** Pending requests use a dedicated Gantt lane, dashed/patterned treatment, explicit `REQUESTED` text, and provenance; approved blocks retain the solid possession treatment.
**We will not:** Reuse green approved-block styling for unplanned departmental demand.

### One canonical route to planning
**The principle:** Department input is captured once and transformed through typed, auditable domain contracts.
**In practice:** Persist a `BlockRequest`, create a linked `MaintenanceTask`, and let the existing optimizer consume that task.
**We will not:** Keep a frontend-only ticket store or duplicate optimizer task logic.

### Recovery over rejection
**The principle:** Validation must tell operational users exactly what is wrong and how to continue.
**In practice:** Preserve entered values, focus the invalid field, pair codes with plain-language guidance, and expose API request IDs.
**We will not:** Clear the conversation or return generic failure messages.

### Dense, legible, and non-colour-dependent
**The principle:** High information density is valuable only when keyboard, zoom, screen-reader, and colour-vision users can complete the same task.
**In practice:** Semantic controls, visible focus, minimum target sizes, text labels, patterns/icons, live-region status, and responsive stacking.
**We will not:** Rely on colour, hover, drag, or animation for required meaning.

## Competitive Position

The experience differentiates from generic help-desk dashboards by treating each request as operational planning intent with railway-specific constraints and traceability. It differentiates from traditional dense maintenance forms by using progressive questioning without sacrificing the complete structured record. Accessibility and provenance are safety features, not optional polish.

## Experience Map

| Moment | User experience | Emotional state | Inclusive requirement |
|---|---|---|---|
| Enter dashboard | See three department queues, counts, live/synthetic source status, and one clear “New ticket” action | Oriented | Page landmark, meaningful heading order, no colour-only counts |
| Start intake | Choose department and receive the first concise operational question | Focused | Keyboard-first radio controls and announced progress |
| Provide details | Answer location, track, work type, severity, duration, and block requirements | Deliberate | Visible structured preview, edit access, error recovery, no timed steps |
| Review | Confirm all values and understand what will feed Block Finder | Accountable | Summary semantics, explicit missing fields, provenance statement |
| Submit | Receive ticket ID, linked task ID, status, and next action | Confident | Live-region confirmation and persistent success state |
| Triage | Block Manager filters requests and sees readiness or validation blockers | In control | Dense table remains navigable at 200% zoom |
| Plan | Run Block Finder using the live linked task set | Cautious | Warnings preserved; no automatic approval |
| Track | See request lane and generated possession relationship on Gantt | Aware | Dashed/patterned request bars plus text status and accessible descriptions |

## Success Metrics

| Metric | Target | Evidence |
|---|---|---|
| Guided intake completion | 100% for valid ENGG, SNT, and TRD scenarios | Component/E2E scenarios |
| Request-to-task integrity | Every accepted request has one linked canonical task | API integration tests |
| Optimizer visibility | Submitted task is present in optimizer input/result or explicit unassigned warnings | Live API flow |
| Timeline traceability | Request and resulting block can be followed by IDs | Gantt UI + tests |
| Keyboard completion | Primary flow completed without pointer | Browser E2E walkthrough |
| Accessibility | No critical axe/manual WCAG issue; all status meaning has text redundancy | Automated and manual report |
| Regression safety | Existing suites remain green | Backend/frontend CI commands |

## Constraints and Trade-offs

- Deterministic guided prompts are chosen over free-form AI parsing for reliability and testability.
- The first release targets one shared desktop dashboard and responsive stacking rather than bespoke department pages.
- Pending requests are visible on the timeline, but remain non-draggable and cannot grant authority.
- Synthetic live data is exercised through the running applications; it is not claimed as production railway data.
- Shell and status copy must say `Synthetic API connected` or equivalent; existing `CRIS/NTES FEED LIVE` and generic `LIVE API` claims are removed until a real connector exists.
