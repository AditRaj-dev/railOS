# Design Critique: Possession Authority Chain

**Reviewed against:** `docs/designpowers/briefs/2026-09-08-possession-authority-chain.md`, `docs/designpowers/plans/2026-09-08-possession-authority-chain-plan.md`, `DESIGN.md`, and the source implementation plan.

**Date:** 2026-09-08

## Summary

The implementation now gives the API ownership of legal transitions and exposes the same state to Flutter and the desk. The successful Terra backend review found and drove fixes for reconnection, lead-in timing, clearance windows/conflicts, transactional sanction backfill, re-energisation, and browser WebSocket authentication. Manual desk review found and fixed a deleted map test plus missing WebGL2/matchMedia fallbacks.

## Findings

### Resolved critical/major
- T/351 could close without reconnection → added `reconnect-t351`, typed status, checklist gate, and regression tests.
- PTW/T/351 lead-in could be bypassed without a client timestamp → server-clock enforcement and timing-aware actions.
- Clearance could ignore day-of windows and active handback states → operating-window and occupancy gates.
- Browser WebSocket could not authenticate → normalized `user`/`role` query fallback while preserving headers.
- Existing geographic-map test was deleted and the fallback export was missing → test restored; `isWebGL2Supported` and safe `matchMedia` fallback added.

### Minor/deferred
- Full Next lint still reports legacy `any`/unused-state issues in untouched components; targeted lint for changed/new possession and map files passes.
- Flutter test execution is not evidenced on this host because the runner stalls and Dart telemetry cannot write its locked `%APPDATA%\\.dart-tool` session file. Static analysis reports no Dart errors.

## Accessibility Status

Desk possession/sanction views use semantic headings/tables, labeled controls, focus-visible styles, 44px targets, non-colour status text/icons, and a focus-contained dialog. Flutter screens use shared semantic widgets and 48dp controls. Automated browser checks beyond the existing Vitest coverage and physical-device/screen-reader checks remain environment follow-ups.

## Recommendation

Proceed with the documented environment caveats. Do not call the Flutter device demo or PostgreSQL restart validation complete until run on a host with an unlocked Flutter toolchain and scratch database.
