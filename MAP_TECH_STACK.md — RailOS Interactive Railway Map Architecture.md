# MAP_TECH_STACK.md

## Project
RailOS — Interactive Railway Network & Operations Map

## Purpose
Define the recommended technical stack, rendering architecture, data model, and scaling strategy for the RailOS interactive railway map.

The map must support:

- India-wide railway network overview
- Zone-level drill-down
- Division-level drill-down
- Section/corridor drill-down
- track-level detail
- maintenance risk overlays
- active block visualization
- maintenance opportunity visualization
- defects and asset markers
- live or simulated train movement
- integration with planner, maintenance table, and analytics
- future production-grade GIS scaling

---

# 1. Final Recommended Stack

## Frontend Framework

```text
Next.js
React
TypeScript
```

### Why

RailOS already needs:

- dashboard UI
- planner
- timeline
- network map
- responsive PWA
- role-based screens

Using one React/Next.js frontend avoids introducing a separate map-specific frontend architecture.

---

# 2. Geographic Map Engine

## Primary Recommendation

```text
MapLibre GL JS
```

Use MapLibre as the primary geographic rendering engine.

### Responsibilities

MapLibre should handle:

- base map
- geographic coordinate system
- zone boundaries
- division boundaries
- section/corridor geometry
- stations
- click/hover interactions
- viewport navigation
- zoom
- pan
- fit-to-section
- vector tile support
- data-driven styling

### Why MapLibre

Advantages:

- open source
- GPU/WebGL accelerated
- supports vector tiles
- data-driven map styling
- strong React ecosystem
- suitable for large networks
- avoids unnecessary vendor lock-in
- future-compatible with PostGIS/vector-tile architecture

### Package

```bash
npm install maplibre-gl
```

Optional React wrapper:

```bash
npm install react-map-gl
```

Use the MapLibre backend mode.

---

# 3. Operational Overlay Renderer

## Primary Recommendation

```text
deck.gl
```

MapLibre should be treated as the geographic map engine.

deck.gl should be used for complex and dynamic railway overlays.

### Responsibilities

deck.gl should render:

- railway corridors
- high-volume track segments
- maintenance pressure
- asset risk
- active maintenance blocks
- animated trains
- incident markers
- traffic pressure
- block opportunity overlays

### Why deck.gl

Advantages:

- GPU accelerated
- designed for large geospatial datasets
- efficient path rendering
- dynamic styling
- animation support
- integrates with MapLibre
- suitable for high-frequency visual state changes

### Package

```bash
npm install deck.gl
```

Relevant packages may include:

```bash
npm install @deck.gl/core
npm install @deck.gl/layers
npm install @deck.gl/geo-layers
npm install @deck.gl/mapbox
```

---

# 4. Primary deck.gl Layers

## PathLayer

Use for:

- railway lines
- corridors
- track segments
- highlighted routes
- active block paths
- risk overlays

Example conceptual input:

```ts
{
  id: "SEG-102",
  path: [
    [77.1025, 28.7041],
    [77.4538, 28.6692]
  ],
  riskScore: 82,
  trafficPressure: 71,
  activeBlock: false
}
```

---

## TripsLayer

Use for:

- animated train movement
- simulated passenger trains
- goods train forecasts
- maintenance vehicle movement

Each route should contain:

```text
coordinates
+
timestamps
```

Example:

```ts
{
  trainId: "12421",
  path: [
    [77.10, 28.70],
    [77.25, 28.69],
    [77.45, 28.67]
  ],
  timestamps: [
    0,
    600,
    1200
  ]
}
```

---

## ScatterplotLayer

Use for:

- stations
- incidents
- defects
- maintenance locations
- inspection points

At lower zoom levels, prefer aggregation or clustering.

---

## IconLayer

Use where distinct symbols are required for:

- critical defects
- signalling issues
- traction faults
- engineering alerts
- emergency events

---

# 5. Schematic Railway Operations Map

The RailOS geographic network view and the operational schematic view should be separate.

## Recommended Stack

```text
React
+
SVG
+
D3
```

### Purpose

Use the schematic view when geographic accuracy becomes less important than operational clarity.

Example:

```text
New Delhi
    │
    ▼
Ghaziabad
    │
    ▼
Aligarh
    │
    ▼
Tundla
```

or horizontally:

```text
NDLS ━━━━━ GZB ━━━━━ ALJN ━━━━━ TDL
```

---

# 6. D3 Responsibilities

Do not let D3 own the entire DOM.

React should remain responsible for component rendering.

Use D3 only for:

- coordinate calculation
- scales
- path generation
- route layout
- time scales
- topology spacing

Recommended D3 packages:

```bash
npm install d3-scale
npm install d3-shape
npm install d3-array
```

Avoid importing the entire D3 bundle unless needed.

---

# 7. Schematic Rendering Architecture

```text
Railway Network Data
        ↓
Topology Processor
        ↓
D3 Position Calculation
        ↓
React Components
        ↓
SVG Railway Diagram
```

Components:

```text
RailSchematic
StationNode
TrackSegment
JunctionNode
SignalMarker
MaintenanceMarker
BlockOverlay
TrainMarker
```

---

# 8. Recommended Dual-Map Architecture

```text
                    Railway Network Model
                             │
                    ┌────────┴────────┐
                    │                 │
                    ▼                 ▼
              Geographic View   Operations View
                    │                 │
              MapLibre GL JS      React + SVG
                    │                 │
                 deck.gl             D3
```

Both views must consume the same canonical railway network model.

Do not maintain two separate network databases.

---

# 9. Frontend State Management

## Recommendation

```text
Zustand
```

### Responsibilities

Store cross-screen UI state:

```text
selectedZone
selectedDivision
selectedSection
selectedTrack
selectedAsset
selectedBlock

mapMode
timeHorizon
departmentFilter
riskFilter

mapViewport
activeLayerSet
```

### Example

```ts
type RailMapState = {
  selectedZoneId?: string
  selectedDivisionId?: string
  selectedSectionId?: string
  mapMode: "RISK" | "MAINTENANCE" | "OPERATIONS" | "OPPORTUNITY"
}
```

Package:

```bash
npm install zustand
```

---

# 10. Server State / Data Fetching

## Recommendation

```text
TanStack Query
```

Use for:

- zone data
- division data
- track segments
- maintenance tasks
- active blocks
- defect overlays
- train movement
- analytics summaries

Package:

```bash
npm install @tanstack/react-query
```

Do not store server-cached data inside Zustand unless absolutely necessary.

---

# 11. Backend

## Recommendation

```text
FastAPI
Python
```

### Why

RailOS already benefits from Python because:

- OR-Tools
- scheduling
- optimization
- data processing
- GIS libraries
- future ML

FastAPI provides a clean API layer between the frontend and geographic/optimization systems.

---

# 12. Spatial Database

## Production Recommendation

```text
PostgreSQL
+
PostGIS
```

PostGIS should store:

- station points
- railway line geometry
- section geometry
- zone boundaries
- division boundaries
- assets
- incidents
- block locations

---

# 13. Core Geometry Types

## Station

```text
POINT
```

## Asset

```text
POINT
```

## Track Segment

```text
LINESTRING
```

## Corridor

```text
MULTILINESTRING
```

## Zone Boundary

```text
MULTIPOLYGON
```

## Division Boundary

```text
MULTIPOLYGON
```

---

# 14. Suggested Database Tables

```text
railway_zones
railway_divisions
railway_sections
railway_tracks
railway_segments
railway_stations

railway_assets
railway_defects
maintenance_tasks

block_windows
active_blocks

train_routes
train_movements
```

---

# 15. Track Segment Schema

Example:

```sql
railway_segments
----------------

id UUID
track_id UUID

zone_id UUID
division_id UUID
section_id UUID

name TEXT

from_station_id UUID
to_station_id UUID

direction TEXT

geometry GEOMETRY(LINESTRING, 4326)

traffic_pressure INTEGER
risk_score INTEGER
maintenance_pressure INTEGER

active_block BOOLEAN

created_at TIMESTAMP
updated_at TIMESTAMP
```

---

# 16. Hackathon Data Format

Do not build vector tile infrastructure during the hackathon.

Use:

```text
GeoJSON
```

Recommended files:

```text
data/
├── zones.geojson
├── divisions.geojson
├── railway-segments.geojson
├── stations.geojson
├── defects.geojson
├── active-blocks.geojson
└── train-routes.json
```

---

# 17. Example GeoJSON Railway Segment

```json
{
  "type": "Feature",
  "properties": {
    "segmentId": "SEG-102",
    "zoneId": "NR",
    "divisionId": "DLI",
    "sectionId": "GZB-ALJN",
    "riskScore": 81,
    "trafficPressure": 74,
    "maintenancePressure": 63
  },
  "geometry": {
    "type": "LineString",
    "coordinates": [
      [77.4538, 28.6692],
      [77.8750, 28.1000]
    ]
  }
}
```

---

# 18. Production Vector Tile Architecture

When the dataset becomes large, move away from large frontend GeoJSON files.

Recommended architecture:

```text
PostGIS
    ↓
Martin
    ↓
Vector Tiles
    ↓
MapLibre
```

---

# 19. Tile Server

## Recommendation

```text
Martin
```

Martin can expose PostGIS data as vector tiles.

Use when:

- track dataset becomes large
- many sections need rendering
- zone/division overlays become heavy
- network data changes frequently

---

# 20. Production Map Pipeline

```text
TMS / SMMS / TDMS / COA
            ↓
   Integration Layer
            ↓
 Railway Data Normalizer
            ↓
        PostGIS
            ↓
       Martin
            ↓
      Vector Tiles
            ↓
     MapLibre GL JS
            +
        deck.gl
```

---

# 21. Zoom Hierarchy

## Zoom Level 0–4

Show:

```text
India
Zones
Main railway corridors
National risk overview
```

Hide:

```text
individual stations
individual assets
minor sections
```

---

## Zoom Level 5–7

Show:

```text
Zones
Divisions
major stations
high-level corridor conditions
```

---

## Zoom Level 8–10

Show:

```text
Sections
stations
maintenance load
active blocks
candidate windows
```

---

## Zoom Level 11+

Show:

```text
individual track segments
signals
traction assets
defects
maintenance tasks
detailed train movements
```

---

# 22. Map Modes

RailOS must allow the same map to answer different operational questions.

## Maintenance Mode

Visualize:

```text
pending tasks
overdue work
maintenance debt
```

---

## Risk Mode

Visualize:

```text
asset risk
critical defects
high-risk sections
```

---

## Operations Mode

Visualize:

```text
active blocks
train movement
field work
emergencies
```

---

## Opportunity Mode

Visualize:

```text
candidate windows
low-traffic gaps
bundling opportunities
```

---

# 23. Layer Architecture

```text
Base Map

Zone Boundaries
Division Boundaries

Railway Corridors
Track Segments

Stations

Signals
Traction Assets
Engineering Assets

Maintenance Tasks
Defects

Available Block Windows
Active Blocks

Passenger Trains
Goods Trains

Emergency Events
```

All layers must be individually configurable.

---

# 24. Interaction Model

## Hover

Show lightweight tooltip:

```text
Ghaziabad–Aligarh

Risk: High
Pending Tasks: 17
Critical Defects: 3
Active Blocks: 1
```

---

## Click

Open contextual detail panel.

The selected entity should update:

```text
Map
Maintenance Table
Analytics
Block Planner
```

---

## Double Click / Open

Drill into:

```text
Zone
↓
Division
↓
Section
↓
Track
```

---

# 25. Map Search

Search should support:

```text
Zone
Division
Station
Section
Block ID
Task ID
Train Number
```

Selecting result should:

```text
zoom map
select object
open context panel
```

---

# 26. Map Performance Strategy

## Hackathon

Use:

```text
small GeoJSON
MapLibre
deck.gl
```

Keep dataset controlled.

---

## Medium Scale

Use:

```text
GeoJSON
clustering
simplified geometry
lazy-loaded layers
```

---

## Large Scale

Use:

```text
PostGIS
vector tiles
Martin
MapLibre
deck.gl
```

---

# 27. Avoid Rendering Everything

Never show:

```text
all stations
all signals
all defects
all track segments
all train labels
```

at national zoom.

Use zoom-based visibility.

This prevents visual noise and improves performance.

---

# 28. Geographic View → Operations View Transition

This is one of the key RailOS interactions.

Example:

```text
India
↓
Northern Railway
↓
Delhi Division
↓
Ghaziabad–Aligarh Section
↓
Open Operational View
```

Then transition from:

```text
Geographic Map
```

to:

```text
NDLS ━━━━━ GZB ━━━━━ ALJN ━━━━━ TDL
```

with operational tracks and block timeline.

---

# 29. Operational View Layout

```text
┌──────────────────────────────────────────────────────┐
│ SECTION: Ghaziabad → Aligarh                        │
├──────────────────────────────────────────────────────┤
│                                                      │
│ GZB ━━━━━━━ DKDE ━━━━━━━ KRJ ━━━━━━━ ALJN          │
│                                                      │
│ UP MAIN   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━         │
│ DOWN MAIN ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━         │
│                                                      │
├──────────────────────────────────────────────────────┤
│ Timeline                                             │
│                                                      │
│ Passenger █████                                      │
│ Goods                 █████                           │
│ ENG                  █████████                        │
│ S&T                  ████                             │
│ TRD                    █████                          │
│ BLOCK                █████████                        │
└──────────────────────────────────────────────────────┘
```

---

# 30. Planner Integration

From map:

```text
Select Section
↓
View Section Details
↓
Plan Maintenance
```

The Block Planner should receive:

```text
zoneId
divisionId
sectionId
timeHorizon
```

automatically.

---

# 31. Live Operations

Realtime updates may use:

```text
WebSockets
```

or:

```text
Supabase Realtime
```

Events:

```text
TRAIN_POSITION_UPDATED
BLOCK_STARTED
BLOCK_DELAYED
BLOCK_COMPLETED
DEFECT_CREATED
TASK_STARTED
TASK_COMPLETED
```

---

# 32. Train Animation

Recommended flow:

```text
Train Route
+
Timestamped Positions
        ↓
TripsLayer
        ↓
Animated Movement
```

For hackathon:

Use simulated positions.

Do not pretend they are live Indian Railways data.

---

# 33. Recommended Libraries

## Required

```text
next
react
typescript
maplibre-gl
deck.gl
zustand
@tanstack/react-query
```

## Schematic View

```text
d3-scale
d3-shape
d3-array
```

## Backend

```text
fastapi
uvicorn
pydantic
```

## GIS / Production

```text
PostgreSQL
PostGIS
Martin
```

---

# 34. Libraries Not Recommended as Primary Stack

## Leaflet

Good for:

- smaller basic maps
- simple marker applications

Not recommended as RailOS primary engine because RailOS may require:

- high-volume paths
- vector tiles
- GPU-heavy overlays
- animated movement
- dynamic network styling

---

## OpenLayers

Technically capable and very strong GIS library.

Consider if RailOS becomes primarily an advanced GIS/editor product.

Not first recommendation for the hackathon because:

```text
MapLibre + deck.gl
```

provides a cleaner fit for operational visualization.

---

## Plain D3

Do not build the full geographic map in plain D3.

Use D3 for:

```text
schematic diagrams
layout calculations
timeline scales
```

not as the primary nationwide geographic map engine.

---

# 35. Do Not Use One Renderer for Everything

Wrong:

```text
D3 for national map
D3 for trains
D3 for planner
D3 for everything
```

Better:

```text
MapLibre
→ geographic context

deck.gl
→ high-performance overlays

React + SVG + D3
→ schematic railway operations view
```

Each technology handles what it is best at.

---

# 36. Recommended Project Structure

```text
apps/
└── control-center/
    └── src/
        ├── features/
        │   └── railway-map/
        │       ├── components/
        │       ├── layers/
        │       ├── hooks/
        │       ├── stores/
        │       ├── utils/
        │       └── types/
        │
        └── features/
            └── schematic-map/

packages/
├── railway-network/
├── geo-types/
└── map-config/
```

---

# 37. Railway Map Feature Structure

```text
railway-map/
│
├── RailwayMap.tsx
├── MapControls.tsx
├── MapLegend.tsx
├── MapSearch.tsx
├── MapContextPanel.tsx
│
├── layers/
│   ├── ZoneLayer.ts
│   ├── DivisionLayer.ts
│   ├── RailwayPathLayer.ts
│   ├── StationLayer.ts
│   ├── DefectLayer.ts
│   ├── BlockLayer.ts
│   ├── TrainLayer.ts
│   └── OpportunityLayer.ts
│
├── stores/
│   └── railwayMapStore.ts
│
└── hooks/
    ├── useRailwayNetwork.ts
    ├── useMapSelection.ts
    └── useMapLayers.ts
```

---

# 38. Schematic Feature Structure

```text
schematic-map/
│
├── SchematicRailMap.tsx
├── StationNode.tsx
├── TrackSegment.tsx
├── JunctionNode.tsx
├── BlockOverlay.tsx
├── TrainMarker.tsx
└── DependencyLink.tsx
```

---

# 39. Hackathon Build Sequence

## Phase 1

Build:

```text
MapLibre map shell
```

---

## Phase 2

Load:

```text
sample railway GeoJSON
```

---

## Phase 3

Implement:

```text
Zone → Division → Section drill-down
```

---

## Phase 4

Add:

```text
PathLayer
station layer
risk styling
```

---

## Phase 5

Connect:

```text
maintenance table
planner filters
```

---

## Phase 6

Add:

```text
active blocks
defects
```

---

## Phase 7

Add:

```text
TripsLayer
animated demo trains
```

---

## Phase 8

Build:

```text
section schematic view
```

---

# 40. Hackathon Scope

Must build:

```text
MapLibre geographic map
railway line layer
zone/division/section drill-down
risk view
maintenance view
active block overlay
map → planner selection
section schematic
```

High-value optional:

```text
animated trains
opportunity mode
emergency map overlay
```

Defer:

```text
full India GIS completeness
production vector tile pipeline
real train tracking
all asset layers
advanced geospatial editing
```

---

# 41. Production Evolution

## Hackathon

```text
GeoJSON
↓
MapLibre
+
deck.gl
```

## V1

```text
PostGIS
↓
Martin
↓
MVT
↓
MapLibre
+
deck.gl
```

## Production Scale

```text
Railway Systems
↓
Integration + Validation
↓
Spatial Data Pipeline
↓
PostGIS
↓
Vector Tile Infrastructure
↓
MapLibre
+
deck.gl
↓
RailOS Control Center
```

---

# 42. Final Architectural Decision

Freeze the RailOS map stack as:

```text
Geographic Rendering
→ MapLibre GL JS

High-performance operational overlays
→ deck.gl

Railway schematic operations view
→ React + SVG + D3

Frontend framework
→ Next.js + React + TypeScript

UI state
→ Zustand

Server state
→ TanStack Query

Backend
→ FastAPI

Spatial database
→ PostgreSQL + PostGIS

Hackathon data transport
→ GeoJSON

Future tile server
→ Martin
```

## Final Rule

Do not choose between a GIS map and a railway schematic.

RailOS needs both.

The geographic map answers:

> Where is the operational pressure?

The schematic map answers:

> What exactly is happening on this section and how should the block be planned?

Both should operate on the same canonical railway network model.