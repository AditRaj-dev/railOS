# Design Plan: RailOS Railway Map Implementation

> **For agentic workers:** Review completed work against this plan before handoff.

**Goal:** Make the existing RailOS network map reliable with viewport-aware APIs, canonical feature picking, explicit data provenance, and an importable railway dataset path.

**Design Direction:** Preserve the graphite operational control-center language in `DESIGN_SYSTEM.md`; static geographic context stays quiet while operational risk, block, and train overlays remain prominent.

**Personas:** Control officers and maintenance planners on desktop; field supervisors and users with visual, motor, cognitive, or motion access needs.

---

## Task 1: Frontend map runtime and interaction

**Owner/files:** Frontend agent; `apps/control-center/package*.json`, `apps/control-center/src/components/map/**`, `apps/control-center/src/app/(shell)/network/page.tsx`, frontend map tests only.

- [ ] Replace the Mapbox-specific deck.gl bridge with the MapLibre integration.
- [ ] Use one map container ref and a stable create/remove lifecycle.
- [ ] Distinguish initialising, ready, basemap-error, API-error, empty, and synthetic-fallback states.
- [ ] Restore provider/OSM attribution and canonical selection objects.
- [ ] Keep operational status legible without relying on colour alone.

**Accessibility check:** Keyboard-accessible map-region alternative, visible focus, text for errors/provenance/status, reduced-motion-safe transitions.

**Verification:** Frontend tests, lint, typecheck/build; map component tests cover successful load and style failure.

---

## Task 2: Viewport-aware network API

**Owner/files:** Backend agent; `apps/api/**`, `packages/railos_model/**`, `packages/railos_data/**`, `tests/test_api_network.py`, `tests/test_api_backend.py` only.

- [ ] Validate `bbox`, `zoom`, and requested layers without breaking existing callers.
- [ ] Replace endpoint-only bbox filtering with real geometry/bbox intersection semantics.
- [ ] Return canonical GeoJSON properties for sections, segments, and stations.
- [ ] Add source snapshot/provenance fields compatibly.
- [ ] Add structured errors for invalid bbox, zoom, and layer values.

**Accessibility check:** Error payloads must support specific, actionable UI messages rather than generic failures.

**Verification:** Focused API tests plus the existing backend suite.

---

## Task 3: Reproducible railway-data ingestion

**Owner/files:** Data agent; new files under `integrations/geospatial/**`, `database/**`, `datasets/geospatial/**`, and focused ingestion tests/docs only. Do not modify frontend or API/model files.

- [ ] Implement a bounded OSM/Overpass or `.osm.pbf` ingestion path that does not require a live source during tests.
- [ ] Preserve immutable snapshot metadata, source references, licence, retrieval time, checksums, and synthetic flags.
- [ ] Normalize railway tracks and stations into deterministic RailOS GeoJSON seed output.
- [ ] Add a PostGIS-ready schema/migration with spatial and identifier indexes.
- [ ] Document attribution, production anti-scraping rules, and the distinction between community geometry and official operational data.

**Accessibility check:** Generated provenance labels must be concise enough for visible UI and descriptive enough for assistive technology.

**Verification:** Deterministic fixture-based ingestion tests; schema/migration syntax checks where supported.

---

## Task 4: Integration and shipping verification

**Owner/files:** Primary agent; cross-workstream review and minimal glue changes only after agents finish.

- [ ] Reconcile frontend types with backend serialization and imported seed output.
- [ ] Run formatter/lint, frontend tests/build, backend tests, and ingestion tests.
- [ ] Inspect the running network page at desktop and narrow viewport if local services can run.
- [ ] Record remaining legal/data limitations and design debt.

**Accessibility check:** Verify keyboard path, error announcements, 200% zoom resilience, and non-colour provenance/status cues.

**Verification:** Evidence-backed final report with commands and outcomes; no completion claim while critical checks fail.
