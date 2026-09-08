# All-India Railway Map and Reported Areas Design

## Objective

Make the existing RailOS Network map visibly render railway tracks across India and demonstrate geolocated operational reports as track-aligned triangular markers. The demo uses algorithmic simulation behind a replaceable feed contract so a real API can be added later without redesigning the map.

## Chosen Approach

RailOS will use the approved hybrid approach:

1. MapLibre continues to render the hosted OpenFreeMap basemap.
2. A MapLibre raster source loads OpenRailwayMap `standard` tiles from its public `a`, `b`, and `c` tile hosts for nationwide railway visibility.
3. Existing RailOS vector segments provide deterministic simulation anchors.
4. A seeded simulator generates reports from those segments by interpolation rather than replaying hard-coded coordinates.
5. deck.gl renders each report as a directional triangle above the railway tiles and existing operational layers.

The raster overlay answers “where are the railways across India?” The RailOS vectors answer “where can this simulated report be placed and selected?” The UI does not imply that the generalized demo segments or ±2–3 metre uncertainty are survey-grade.

## Architecture and Boundaries

### Hosted railway overlay

`railwayOverlay.ts` owns OpenRailwayMap source and layer identifiers, tile templates, attribution, idempotent installation, visibility, and removal. `GeographicMap.tsx` invokes it only after a MapLibre style is available and invokes it again after a fallback style replaces the primary style.

The railway overlay has a runtime state separate from the basemap: `loading`, `ready`, or `error`. Failure does not remove local RailOS vectors or report markers.

### Report domain contract

`ReportedArea` contains:

- `reportId`
- `segmentId` and `sectionId`
- `[longitude, latitude]` coordinates
- `bearingDegrees`
- `uncertaintyMetersBefore` and `uncertaintyMetersAfter`
- `severity`: `INFO`, `WARNING`, or `CRITICAL`
- `status`: `NEW`, `ACKNOWLEDGED`, or `CLEARED`
- `reportedAt`
- `synthetic: true`

`NetworkFeatureProperties.entityType` gains `report` so reports use the same selection boundary as zones, divisions, sections, segments, and stations.

### Simulation engine

`reportSimulation.ts` is framework-independent. It owns a seeded pseudo-random generator, polyline length calculation, distance-weighted interpolation, local bearing calculation, report creation, and lifecycle reduction. It accepts segments as input and never embeds coordinates.

`useReportSimulation.ts` owns timers and exposes `reports`, `running`, `pause`, `resume`, `acknowledge`, and `reset`. It cleans up timers on unmount and starts only when at least one valid `LineString` segment exists. Resetting with the same seed produces the same event sequence.

### Rendering and interaction

`reportedAreaLayer.ts` creates a deck.gl `IconLayer` using a triangular SVG/icon atlas. Position comes from report coordinates, angle from `bearingDegrees`, and colour from severity. A selected report receives a larger outline or size in addition to colour.

Triangles remain a fixed readable pixel size while zooming. Mouse hover and click use the existing feature-adapter contract. The existing “Browse map features” disclosure includes reports as the keyboard-accessible alternative to canvas picking.

Selecting a report shows ID, severity, lifecycle status, age/timestamp, section and segment IDs, coordinates, and “Approx. ±2–3 m; simulated” text. Selecting a `NEW` report acknowledges it. Cleared reports leave the active layer after their lifecycle transition.

### Data flow

```text
Hosted OpenFreeMap style ───────────────┐
OpenRailwayMap raster tiles ────────────┼─> MapLibre geographic canvas
                                       │
RailOS network catalog -> segments ────┼─> deck.gl operational paths
                         │             │
                         └-> seeded simulator -> ReportedArea[]
                                                │
                                                └-> triangle IconLayer
```

A later API replaces the simulator at the report-feed boundary and supplies the same `ReportedArea` objects.

## States and Error Handling

- Basemap initializing: show the existing initializing status.
- Basemap unavailable: use the existing fallback background and keep local overlays active.
- Railway tiles loading: show “Loading railway tracks…” independently.
- Railway tiles unavailable: show “Railway track layer unavailable”; do not claim the map is fully ready.
- No valid vector segments: pause report generation and show “Simulation waiting for track geometry.”
- Simulator running: show active-report count and a Pause control.
- Simulator paused: retain current reports and offer Resume and Reset.
- Reduced motion: disable pulsing, fades, and animated layer transitions; status changes remain immediate and textual.

No error path creates an off-track fallback report.

## Accessibility

- The canvas retains its descriptive accessible name.
- Every report is duplicated in the keyboard feature browser as a real button.
- Report status and severity are written as text and reflected by shape/outline, not colour alone.
- Controls have visible focus, `aria-pressed` or clear button labels, and live status announcements.
- Triangle size remains visually legible without becoming the sole hit target; the keyboard list provides a reliable alternative.
- Report motion obeys `prefers-reduced-motion`.

## Verification Strategy

### Unit tests

- A fixed seed yields the same report sequence.
- Different seeds yield different selections or interpolation fractions.
- Generated coordinates lie on the chosen polyline.
- Bearing is normalized to `[0, 360)`.
- Uncertainty remains within 2–3 metres in both directions.
- Lifecycle transitions are valid and deterministic.
- Invalid or empty geometry produces no report.
- Railway source/layer installation is idempotent.

### Component tests

- Map style load installs the OpenRailwayMap source and layer once.
- A style replacement re-installs the overlay without duplication.
- Tile errors surface the railway-specific error state.
- Fake timers generate, acknowledge, clear, pause, resume, and reset reports.
- Report buttons expose complete accessible names and selection.
- Reduced motion disables report animation props.

### Project verification

- `npm test`
- `npm run lint`
- `npm run build`
- Browser inspection at India overview and a zoomed corridor.
- Network inspection confirms requests to OpenRailwayMap tile hosts.
- Browser inspection confirms triangle markers sit on their RailOS segment and remain distinguishable in every map mode.

## Scope Boundary

This increment makes nationwide railway infrastructure visible through hosted raster tiles and distributes simulated reports across the representative RailOS vectors already present around India. It does not create a nationwide vector rail database or claim metre-level operational accuracy. Those become separate ingestion and production GIS projects when real reporting is connected.

