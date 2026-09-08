# INTERACTIVE_TRACK_MAP.md

## Goal
Define the architecture, UX, data model, and drill-down logic for the RailOS interactive railway track map.

---

## 1. Core Principle

The map should be:
- operational
- hierarchical
- filterable
- drillable
- integrated with planning and analytics

It should NOT start as a consumer geographic map.

---

## 2. Hierarchy Model

Level 1:
Indian Railways Overview

Level 2:
Zones / Regional Railways

Level 3:
Divisions

Level 4:
Corridors / Sections

Level 5:
Track / Asset / Block Window

Recommended navigation hierarchy:

Railway-wide
→ Zone
→ Division
→ Section
→ Block / Task

---

## 3. Suggested Regional Structure for UI

Do not invent fake regions.
Use official railway zones as the primary segmentation layer.

For MVP, create zone tiles such as:
- Northern Railway
- North Central Railway
- North Eastern Railway
- North Western Railway
- Central Railway
- Western Railway
- West Central Railway
- Eastern Railway
- East Central Railway
- East Coast Railway
- North Frontier Railway
- Southern Railway
- South Central Railway
- South Eastern Railway
- South East Central Railway
- South Western Railway

You can later extend with newly formed or refined zonal structures after data validation.

---

## 4. Why Zones Instead of “North/South/West” Buckets?

Because operators and administrators already work through zonal/divisional structures.
Your UI should mirror institutional structure, not founder shorthand.

If you want a simpler top-level overview, you can visually cluster zones into:
- North
- South
- East
- West
- Central / Northeast

But the selectable object should still be the actual railway zone.

---

## 5. Map Modes

The map should support multiple visualization modes.

### Mode A — Maintenance Pressure
Color by:
- pending task volume
- overdue work
- maintenance debt

### Mode B — Risk
Color by:
- critical defects
- asset risk
- failure pressure

### Mode C — Availability
Color by:
- current asset availability
- block scarcity
- train density

### Mode D — Active Operations
Show:
- active blocks
- live field work
- delayed work
- emergency incidents

### Mode E — Planning Opportunities
Show:
- candidate block windows
- compatible bundled work zones
- low-traffic opportunities

---

## 6. Interaction Model

### Railway-wide View
User sees zonal blocks/cards over a simplified India schematic.

Each zone card shows:
- critical defects
- overdue maintenance
- maintenance debt
- next major block opportunity
- active blocks

User actions:
- click a zone
- hover for quick summary
- filter by mode

### Zone View
Show divisions as grouped nodes or rail segments.

Each division shows:
- task count
- critical count
- active block count
- risk level

User actions:
- click division
- compare divisions
- filter to department

### Division View
Show sections/corridors as connected rail lines.

Each section shows:
- health state
- train pressure
- open windows
- candidate work

User actions:
- click section
- open planner with that section preselected
- open maintenance list filtered to that section

### Section View
Show tracks and active/proposed blocks.

May display:
- up/down track
- windows
- train movements
- maintenance tasks
- signals/traction dependencies

User actions:
- inspect block
- inspect tasks
- start planning
- inject scenario

---

## 7. Recommended Map Layout

Desktop layout:

┌────────────────────────────────────────────────────────────────────┐
│ Zone/Division Filters | View Mode | Search | Time Horizon         │
├──────────────┬───────────────────────────────────────┬─────────────┤
│ Left Tree    │ Main Schematic Track Map              │ Right Info  │
│              │                                       │             │
│ Zones        │  India / Zone / Division / Section    │ Selected    │
│ Divisions    │  depending on drill level             │ node        │
│ Sections     │                                       │ summary     │
├──────────────┴───────────────────────────────────────┴─────────────┤
│ Bottom linked insights: KPIs, trends, top tasks, open planner     │
└────────────────────────────────────────────────────────────────────┘

---

## 8. Schematic vs Geographic

### MVP Recommendation
Use a **schematic network map**.

Why:
- clearer
- faster to implement
- better for operations thinking
- easier to link with sections/corridors
- avoids fake precision

### Optional Layer 2
Add a geographic India basemap later if needed.

But the actual operational overlays should still be schematic rail structures.

---

## 9. Visual Encoding

### Color
Use color to encode pressure/risk states:
- low
- moderate
- elevated
- high
- severe

### Thickness
Use line thickness for:
- traffic density
- corridor significance
- asset volume

### Pattern
Use pattern for:
- active block
- delayed maintenance
- emergency restriction
- proposed opportunity

### Icons
Use small icons for:
- critical defect
- active work
- signal issue
- traction issue
- approval pending

---

## 10. Map Data Model

Each node should be representable by structured data.

### Zone
- id
- name
- divisions[]
- summary metrics

### Division
- id
- zoneId
- name
- sections[]
- summary metrics

### Section / Corridor
- id
- divisionId
- name
- fromStation
- toStation
- tracks[]
- summary metrics

### Track Segment
- id
- sectionId
- direction
- status
- active windows
- active blocks

### Summary Metrics
- pendingMaintenanceCount
- criticalDefectCount
- maintenanceDebt
- activeBlocks
- assetAvailability
- trafficPressure
- openOpportunityCount

---

## 11. Linked Behaviors

The map should not be isolated.

Selecting any node should:
- filter maintenance table
- filter analytics
- prefill planner
- update right panel
- update timeline context

This linkage is what makes the map useful.

---

## 12. Planner Integration

From any zone/division/section, user should be able to:
- View candidate tasks
- View candidate windows
- Generate plan
- Compare plans
- Review active block schedule

Best CTA:
[Plan for this Section]
[View Tasks]
[View Analytics]

---

## 13. Analytics Integration

When user selects a zone:
show:
- trend of maintenance debt
- block utilization
- coordination ratio
- top risky divisions

When user selects a division:
show:
- top risky sections
- overdue trend
- train disruption

When user selects a section:
show:
- open windows
- active maintenance
- block history
- repeated issues

---

## 14. Best Frontend Tech Approach

Recommended stack:
- React / Next.js
- SVG-based schematic network rendering for MVP
- D3 only if necessary for layout math
- Zustand or equivalent for shared selection/filter state

Do NOT begin with a full GIS stack unless you already have route geometry.

### MVP Implementation Path
1. static structured zone/division graph
2. clickable SVG map
3. linked state filters
4. detail side panel
5. section-level timeline linkage
6. planner deep-link

---

## 15. Initial Screen States

### State 1 — Railway Overview
All zones shown.

### State 2 — Zone Selected
Divisions appear; rest of UI filtered.

### State 3 — Division Selected
Corridor schematic shown.

### State 4 — Section Selected
Detailed local view + linked planner.

### State 5 — Planning Mode
Map remains as context while planner opens.

---

## 16. MVP Zone Dataset Strategy

For hackathon, create a curated demo dataset with:
- 5 to 8 zones fully represented
- 2 to 4 divisions per zone
- 3 to 6 sections per division

Do not try to model the whole of India in 36 hours.
Fake completeness is worse than focused realism.

Best demo set:
- Northern Railway
- North Central Railway
- Western Railway
- Central Railway
- South Central Railway
- Southern Railway

This gives geographic and operational diversity.

---

## 17. PWA Map Behavior

On mobile:
- do not show full giant map by default
- show region selector
- selected section card
- mini schematic
- quick drill-down
- “open planner on desktop” not needed, but avoid complexity

Mobile users need:
- awareness
- assignment context
- quick lookup
not full planning.

---

## 18. Future Enhancements

- real GIS route overlays
- live train overlays
- section animation
- predictive pressure layer
- weather impact overlay
- maintenance machine positioning
- kilometer chain display
- approval geography layer