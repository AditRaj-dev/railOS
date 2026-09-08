# Design Brief: All-India Railway Map with Reported Areas

## Problem Statement

RailOS control officers and maintenance planners cannot rely on the geographic view unless it visibly renders railway tracks across India and places operational reports in an understandable position on those tracks. The first version must demonstrate this end to end without waiting for a production report API.

## Users

- Control officers monitoring a national network under time pressure.
- Maintenance planners locating a report before opening corridor or section planning.
- Users working with keyboard navigation, screen readers, low vision, colour-vision differences, motion sensitivity, or bright control-room displays.

## Design Direction

Use a hybrid map. MapLibre renders the hosted basemap and an OpenRailwayMap raster overlay for nationwide railway visibility. RailOS vector segments remain the placement surface for code-generated, track-aligned report triangles. A typed report-feed boundary lets a future API replace the simulator without changing map rendering.

## Constraints

- All of India must have visible railway coverage.
- Internet-hosted basemap and railway tile services are acceptable.
- The first version uses simulated reports; no report API or backend mutation is required.
- Simulation must be algorithmic and deterministic under a fixed seed, not a fixed coordinate sequence or decorative animation.
- A report is represented by a directional triangle centred on a track.
- The reported position carries approximately 2–3 metres of bidirectional uncertainty.
- Existing Next.js 16, React 19, MapLibre 6, deck.gl 9, TypeScript, and RailOS design-system patterns remain in place.
- Public and synthetic sources must be labelled honestly and attributed.

## Existing Design System

- `DESIGN_SYSTEM.md`
- `DESIGN.md`
- Existing control-center tokens in `apps/control-center/src/app/globals.css`

## Taste Direction (Early Signal)

Preserve the graphite operational canvas and restrained status colours. Railway infrastructure is geographic context; report triangles are the higher-salience operational layer. Status must remain understandable without colour alone.

## Success Criteria

- Opening the Network page produces a working hosted basemap and visible OpenRailwayMap tracks across India.
- Railway-layer loading, ready, and unavailable states are distinguishable from basemap state.
- With vector segments available, a seeded simulator creates typed reports over time by selecting a segment, interpolating a point, and deriving local bearing.
- Each report renders as a selectable triangle centred on its selected segment and exposes ID, severity, lifecycle status, timestamp, coordinates, section/segment, and uncertainty.
- Reports transition through `NEW`, `ACKNOWLEDGED`, and `CLEARED`; pause and reset make the demo repeatable.
- Keyboard users can select reports through the existing non-canvas feature browser, and reduced-motion users receive immediate state changes.
- React Strict Mode does not duplicate MapLibre sources, layers, timers, or report events.

## Out of Scope

- A real report ingestion API, WebSocket, or persistence.
- Survey-grade or safety-authoritative positioning.
- Full nationwide vector-track ingestion and nearest-line search.
- Offline or air-gapped tiles.
- Production PostGIS, Martin, or PMTiles infrastructure.
- Additional OpenRailwayMap thematic styles beyond the standard track layer.

