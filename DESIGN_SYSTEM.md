# DESIGN_SYSTEM.md

## Purpose
Define the visual language, interaction primitives, tokens, components, and usage rules for RailOS.

---

## 1. Design Philosophy

RailOS design principles:

1. Operational clarity over visual flair
2. Density without chaos
3. Graphite surfaces for control-room use
4. Strong semantic status system
5. Consistent hierarchy
6. Explain state changes clearly
7. Design for decision-making, not decoration

---

## 2. Visual Character

Keywords:
- industrial
- procedural
- precise
- trustworthy
- controlled
- systemic
- low-noise

Avoid:
- excessive gradients
- neon glow
- startup glass cards
- playful illustrations
- oversized rounded bubbles
- decorative motion

---

## 3. Color System

Use semantic tokens, not random hardcoded colors.

### Foundation

Background:
- bg-canvas: #121313
- bg-surface: #181917
- bg-elevated: #21201d
- bg-panel: #1c1c1a
- bg-overlay: #0a0703

Text:
- text-primary: #f3efe5
- text-secondary: #c1bbad
- text-muted: #918b80
- text-inverse

Border:
- border-default: #3a372f
- border-subtle: #292722
- border-strong: #554d3f

### Semantic Status

Neutral:
- status-neutral

Info:
- status-info (signal amber: #e8a317)

Success:
- status-success

Warning:
- status-warning

Critical:
- status-critical

Paused:
- status-paused

Maintenance Dept Identity:
- dept-engineering (oxidized amber)
- dept-snt (signal amber)
- dept-traction (muted sage)

Objective Identity:
- mode-safety
- mode-balanced
- mode-operations (neutral clay)

Rule:
Status colors must remain readable on graphite backgrounds and cannot rely on color alone; pair with labels/icons. Use signal amber as the sole branded accent; status colors stay desaturated and functional.

---

## 4. Typography

### Font Style
Use a highly readable sans-serif UI font.

### Type Scale

- Display Large
- Display Medium
- Heading 1
- Heading 2
- Heading 3
- Title
- Body
- Body Small
- Label
- Caption
- Numeric Mono

Use monospaced numerals for:
- timings
- train numbers
- block IDs
- KPI counters
- durations
- percentages

---

## 5. Spacing System

Use a strict spacing scale.

Tokens:
- space-2
- space-4
- space-6
- space-8
- space-12
- space-16
- space-20
- space-24
- space-32

Rules:
- compact tables use smaller rhythm
- planning panels use medium rhythm
- large screen layout uses consistent gutters
- avoid arbitrary padding values

---

## 6. Radius & Borders

RailOS should not look soft and bubbly.

Recommended:
- small radius for inputs, chips, panels
- medium radius for cards only
- strong border usage to separate dense panels

No giant rounded cards.

---

## 7. Elevation

Levels:
- base
- raised
- modal
- overlay

Use elevation sparingly.
Prefer borders and contrast over exaggerated shadows.

---

## 8. Iconography

Icons must be utilitarian and familiar.

Use icons for:
- alerts
- trains
- tracks
- blocks
- maintenance
- signals
- traction
- approvals
- delay
- completion

Never use icons alone for critical states.
Always pair with text or badge.

---

## 9. Status Semantics

### Task Status
- pending
- candidate
- scheduled
- assigned
- active
- delayed
- completed
- deferred
- cancelled

### Block Status
- proposed
- under_review
- approved
- active
- at_risk
- delayed
- completed
- cancelled
- superseded

### Severity
- low
- medium
- high
- critical

### Risk Bands
- low
- guarded
- elevated
- high
- severe

Render status consistently across:
- badges
- rows
- timeline items
- notifications
- side panels

---

## 10. Core Components

### Navigation
- SidebarNav
- SidebarGroup
- TopBar
- Breadcrumbs
- TerritorySelector

### Metrics
- MetricCard
- TrendMetric
- DeltaPill
- SparkMini

### Status
- StatusBadge
- SeverityBadge
- DepartmentBadge
- RiskIndicator
- ObjectiveBadge

### Tables
- DataTable
- DenseRow
- FilterBar
- SortMenu
- ColumnManager

### Panels
- SectionPanel
- DetailDrawer
- ContextRail
- AlertStack
- SplitPanel

### Planning
- Timeline
- TimelineRow
- TimelineItem
- WindowBand
- TrainPath
- BlockBar
- DependencyLink

### Network
- ZoneTile
- DivisionTile
- RailSectionNode
- TrackSegment
- SchematicMap
- MapLegend

### Workflow
- PlanCard
- PlanComparisonGrid
- ApprovalPanel
- ReplanDiffCard
- ScenarioControl

### Mobile
- AssignmentCard
- QuickActionBar
- DefectForm
- UpdateStepper

---

## 11. Table Design Rules

Data density is a feature here.

Rules:
- compact row height
- sticky headers
- sticky first column when useful
- hover reveal for row actions
- row selection state must be strong
- use drawers instead of navigating away
- allow export and filtering
- prioritize scannability over decorative empty space

---

## 12. Timeline Design Rules

This is one of the most important primitives.

Timeline must visually distinguish:
- train movement
- available windows
- maintenance tasks
- recommended blocks
- conflicts
- dependencies
- delays

Row colors and patterns should differ enough to read quickly.

Timeline interactions:
- hover for exact time
- click for details
- drag only if editable mode is enabled
- zoom by hour / half-day / full day

---

## 13. Map Design Rules

The map is schematic first, geographic second.

Rules:
- zones visible at overview
- divisions visible at next drill
- sections/corridors visible at detailed drill
- color reflects pressure/risk
- click to filter the rest of the UI
- support highlight by department, risk, or maintenance load

Do not overcomplicate with full GIS in MVP.

---

## 14. Motion

Use motion only for:
- panel transitions
- plan generation progress
- replan diff animation
- hover/selection feedback
- notification entrance

Do not use motion that slows control-room interaction.

---

## 15. Content Style

Labels should be short, operational, and clear.

Good:
- Generate Plan
- Review Block
- At Risk
- Replan
- Approve
- Delay Reported

Bad:
- Let AI optimize your maintenance workflow
- Seamlessly orchestrate mission outcomes

Don’t write marketing copy inside the product.

---

## 16. Accessibility

Required:
- strong contrast
- keyboard focus
- color + text redundancy
- readable type
- not relying only on motion
- support on large screens

---

## 17. Demo Data Labelling

Any synthetic or simulated metrics must be marked clearly:
- Demo
- Synthetic
- Simulated

Do not make fake operational numbers look real.

---

## 18. Design System Deliverables

Minimum implementation deliverables:
- token definitions
- color roles
- typography scale
- spacing scale
- component inventory
- page templates
- status mappings
- timeline pattern library
- map legend system
