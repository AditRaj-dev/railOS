# Live flow walkthrough — ticket → block plan → possession → evidence

Date: 2026-09-09 · API `uvicorn railos_api.main:app --app-dir apps/api --port 8000` (memory backend, synthetic auth) · UI `npm run dev` on :3000 · browser driven manually.

## Commands

```bash
cd E:\RailOS && .venv/Scripts/python.exe -m pytest -q
npx tsc --noEmit && npm run lint && npm test && npm run build
cd E:\RailOS && .venv/Scripts/python.exe -m uvicorn railos_api.main:app --app-dir apps/api --port 8000
cd E:\RailOS\apps\control-center && npm run dev
```

## Results

| Leg | Result |
|---|---|
| `pytest -q` | 156 passed (includes `test_e2e_ticket_api.py` 8 cases and `test_e2e_ticket_to_evidence.py`) |
| Frontend typecheck / lint / vitest / build | clean · 0 errors, 10 pre-existing unused-var warnings · 92 tests · build OK |
| ENGG ticket via composer | created, queued, linked task `TKT-REQ-31D468B3AD`, Block Finder "Ready" |
| SNT ticket (acting role Signal & Telecom) | `REQ-C276EF0EA5` · POINT MACHINE MAINT · queue updated live without reload |
| TRD ticket (acting role Traction) | `REQ-526CDE128E` · OHE INSPECTION · linked task appears in optimizer warnings (HC-012 tower wagon) |
| Reload persistence | all three tickets survive a hard reload; tabs read ALL (3) / ENGG (1) / SNT (1) / TRD (1) |
| Department scoping | SNT role sees only the SNT tab and queue; broad roles see all three plus All |
| Optimizer | Run Optimizer → 5 possession windows; ticket task `TKT-REQ-526CDE128E` scheduled into `BLK-RJ_SMQ-00001` |
| Sanction chain | Approve Plan (202, chain open) → sign as Sr. DOM, Section Controller, TPC → plan `APPROVED` v2, 5 possessions opened |
| Possession lifecycle | request-clearance (ENGG) → grant-clearance (Control) → start-isolation (ENGG) → confirm-earthing + issue-PTW (TPC) → plant-protection (ENGG) → `PROTECTED` |
| Field work + evidence | not driven through the browser — see limitations |

## Bugs found and fixed

1. `tests/test_e2e_ticket_to_evidence.py` failed at stage 4 (`CLEARANCE_WINDOW_EXPIRED`). The optimizer places maintenance in night windows, so any real-clock run produced a possession whose window had already closed. The test now re-anchors `state.horizon_start_iso` after plan selection so the chosen block straddles *now*; the day-of and window-expiry guards still run against a legitimately open window.
2. Possession detail showed only "No action is available to the current acting role at this stage" when a precondition (PTW lead-in, day-of gate) held the action back — indistinguishable from a broken screen. `build_possession_view` now returns `blockedActions: [{action, reason}]` and the detail view renders "Start Work is held: Permit to Work lead-in of 20 minutes has not elapsed". Verified in the live app.

## Gaps closed in this pass

All verified in the running app (API on :8000, dashboard on :3000).

1. **Planner ticket lane** — `/planner` now opens with a "Ticket-derived demand" panel: per-department counts, one checkbox row per open request showing `TKT-<requestId>`, department, task type and severity, and a link to the ticket hub. Checking rows scopes Run Optimizer to those `taskIds`; an empty selection keeps the old plan-everything behaviour.
2. **Gantt REQUESTED demand lane** — a dashed amber lane above the possession windows, one row per request so overlapping demands stay legible, each bar reading `<DEPT> · <TASK TYPE> · REQUESTED` in words, with a text-equivalent list below carrying request ID, window and linked task ID.
3. **Composer duration floor** — new `GET /api/v1/block-requests/task-types` serves each department's task types with their HC-002 minimum (derived from `TASK_REQUIREMENTS` + `MIN_MACHINE_BLOCK_MINUTES`), so the composer no longer hard-codes the list. The block-need step states "OHE INSPECTION needs a minimum block of 120 minutes (HC-002)", sets the input's `min`, and refuses a short value before it reaches the API.
4. **Raw pydantic error** — `TASK_CONSTRAINT_INVALID` now reads "Ohe Inspection needs at least 120 minutes under HC-002; you entered 90." with `details.minDurationMinutes`, instead of the model's internal validation dump. Server errors also jump the composer back to the offending step.
5. **Stale validation banner** — server-reported errors are held apart from client-side field errors and cleared on any edit, so correcting the value clears the banner.
6. **Silent 202 on Approve Plan** — the planner reports the outcome: "Your authority is recorded. Still outstanding: SANCTION. Continue on Plan Sanctions." (with a link), or "All required authorities have signed. Possessions are open." when the chain completes.
7. **Acting role reset** — the selector's role is kept in `sessionStorage` and restored after mount (not in the store's initial state, so the first paint still matches the server render). A reload as Traction stays Traction and lands on the TRD queue.
8. **Composer opened with no department** — the dashboard's active tab is now derived rather than a one-shot state initializer, so a role change under a mounted dashboard moves the tab with it and the composer opens pre-filled.

Tests added: `tests/test_e2e_ticket_api.py` covers the task-type catalogue and the prose 422; `src/components/__tests__/TicketComposer.test.tsx` covers the floor hint, the client-side refusal, and the banner clearing.

## Gaps still open

- No CI browser proof; plan task 8 stays open as design debt.

## Second pass: Gantt semantics and the asset picker

9. **Gantt possession bars are buttons (DP-002)** — each bar is a `<button type="button">` with a focus-visible ring and an accessible name carrying the whole window ("Possession BLK-ER_KRJ-00000, Dadri–Khurja, 00:00 to 02:30, 150 minutes. Open in Block Opportunity Planner."), because the visible label is clipped to the bar's width. Verified in the live app: the bars expose the button role with those names, take focus, and activate to `/planner`. Keyboard activation itself could not be exercised through the automation — the browser pane delivers no key events to the page at all (a window-level `keydown` listener recorded nothing), so that leg rests on native button behaviour plus the component spec rather than an observed keystroke.
10. **SNT asset picker** — `/api/v1/block-requests/task-types` now also reports the `assetType` that identifies each task type's work location, and the composer's work step offers the matching assets for the chosen section and track. One candidate is named and left to the server to resolve; several require a choice; none is refused up front — "No POINT asset is mapped on SEC_KRJ_SMQ DOWN. Choose another section, track, or work type." — instead of `ASSET_REQUIRED` after six steps. Changing section, track or work type clears a stale choice. Verified live: point-machine work on SEC_KRJ_SMQ DOWN is caught at the work step, and the same request on UP resolves to `POINT_102B_KRJ` and submits (`REQ-063CAF789A`).

Tests: `TimelineGanttView.test.tsx` asserts the bar's button role and accessible name and the REQUESTED wording; `TicketComposer.test.tsx` covers the multi-candidate choice and the lone-candidate pass-through; `test_e2e_ticket_api.py` asserts the `assetType` in the catalogue.

## Limitations

- Evidence upload and control-officer review were exercised only by `tests/test_e2e_ticket_to_evidence.py` (stages 5–9, real JWT for `EMP901`), not through the browser: reaching `LIVE` in the UI requires waiting out the 20-minute PTW lead-in.
- The API runs the memory backend, so restarting it clears tickets, plans and possessions. The possession used for the blocked-action check was re-driven through the API after the restart.
- No CI browser proof; plan task 8 stays open as design debt.
