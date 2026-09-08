# FRONTEND_LAYOUT.md

## Product
RailOS — Railway Maintenance Intelligence & Automatic Block Planning Platform

## Frontend Goal
Build a serious, high-density, role-based railway operations interface that allows planners, controllers, and departmental officers to understand network condition, review maintenance pressure, generate optimized block plans, approve them, monitor execution, and react to disruptions.

---

## 1. Product Character

RailOS should feel like:
- a railway control-room system
- a maintenance planning console
- an operational decision-support platform

RailOS should NOT feel like:
- a generic startup admin panel
- an AI chatbot with charts
- a consumer workflow tool

Design personality:
- industrial
- precise
- dark, calm, operational
- information-dense
- low decoration
- high trust

---

## 2. Information Architecture

The application should be structured into these primary areas:

1. Command Center
2. Network Map
3. Maintenance Intelligence
4. Block Planner
5. Calendar / Planning Horizons
6. Live Operations
7. Simulation / Replanning
8. Analytics
9. AI Copilot
10. Notifications
11. Administration

---

## 3. Global App Shell

### Desktop Shell

┌─────────────────────────────────────────────────────────────────────────────┐
│ Top Bar                                                                     │
├──────────────┬──────────────────────────────────────────────┬───────────────┤
│ Left Nav     │ Main Workspace                               │ Right Panel   │
│              │                                              │               │
│ Sections     │ Active Screen                                │ Alerts /      │
│              │                                              │ Context /     │
│              │                                              │ Details       │
├──────────────┴──────────────────────────────────────────────┴───────────────┤
│ Bottom Status Bar                                                           │
└─────────────────────────────────────────────────────────────────────────────┘

### Persistent Areas

#### Top Bar
- RailOS logo
- current territory selector
- date/time
- live status
- search
- user role
- quick notifications badge
- environment label (Demo / Live / Sandbox)

#### Left Navigation
- icon + label navigation
- collapsible
- support pinned views

#### Main Workspace
- screen content
- multi-panel layouts
- data tables
- network map
- timelines
- planner

#### Right Context Panel
- live alerts
- block details
- task detail drawer
- explanations
- approval drawer

#### Bottom Status Bar
- current plan version
- sync status
- optimization status
- last data refresh
- active incident status

---

## 4. Desktop Navigation

Primary left navigation:

- Command Center
- Network
- Maintenance
- Block Planner
- Calendar
- Live Operations
- Simulation
- Analytics
- AI Copilot
- Notifications
- Admin

Recommended behavior:
- one active section at a time
- each primary section can have sub-navigation
- preserve last screen state within each section

---

## 5. Command Center Screen

## Purpose
The default landing page for planners and control officers.

## Goal
Provide an immediate operational summary within 5 seconds.

## Layout

### Top KPI Strip
- Critical Defects
- Overdue Maintenance
- Planned Blocks Today
- Active Blocks
- Asset Availability Proxy
- Maintenance Debt
- Block Utilization
- Emergencies

### Main Row 1
Left:
- Regional / zonal maintenance pressure heat panel

Center:
- Railway network overview map

Right:
- Live alert/event panel

### Main Row 2
Left:
- Recommended actions panel

Center:
- Today’s maintenance block timeline

Right:
- Top risky assets / sections

### Main Row 3
- quick compare of manual vs RailOS plan metrics
- recent optimization runs
- unresolved conflicts

---

## 6. Network Screen

## Purpose
Explore the railway hierarchy and operational condition.

## Hierarchy
Railway-wide → Zone → Division → Corridor/Section → Track/Asset

## Layout

Left panel:
- hierarchical tree
  - All Zones
  - Division list under zone
  - Sections under division

Center:
- interactive railway schematic map

Right panel:
- selected node details

Bottom:
- selected region timeline / trend tabs

## Zone Card Data
Each zone card should show:
- total pending maintenance
- critical defects
- maintenance debt
- available windows
- asset availability
- active block count

## Drill-Down
Click Zone → filter map + analytics
Click Division → show divisional sections
Click Section → show detailed corridor state

---

## 7. Maintenance Intelligence Screen

## Purpose
Unified maintenance backlog and task intelligence center.

## Layout

Top filter ribbon:
- zone
- division
- department
- task type
- priority
- risk
- due date
- block required
- status

Main content:
- high-density data table

Right drawer:
- task details on selection

## Table Columns
- Task ID
- Department
- Asset
- Zone
- Division
- Section
- KM Start
- KM End
- Work Type
- Severity
- Risk
- Priority
- Due Date
- Overdue Days
- Duration
- Block Required
- Isolation Required
- Status

## Row Interaction
Click row:
- open details drawer
- show dependencies
- show related block suggestions
- show “why priority” explanation

---

## 8. Block Planner Screen

## Purpose
Core planning interface.

## Layout

Top planner controls:
- territory selector
- horizon selector (daily / weekly / monthly)
- objective mode
- constraints
- generate plan button

Main body split into 3 columns:

### Left
Planning Inputs
- selected zone/division/section
- pending tasks
- candidate windows
- constraint summary
- blocked tasks
- resource summary

### Center
Main operational timeline / scheduler
Rows:
- passenger trains
- goods trains
- available windows
- Engineering
- S&T
- Traction
- proposed block(s)

### Right
Candidate plan comparison
- Safety First
- Balanced
- Operations First

Each card shows:
- critical work completed
- disruption
- utilization
- maintenance debt reduction
- unassigned tasks

Bottom section:
- selected plan details
- approve / reject / re-optimize
- export / notify

---

## 9. Calendar Screen

## Purpose
Multi-horizon planning.

Tabs:
- Monthly
- Weekly
- Daily

### Monthly
Strategic maintenance capacity allocation.

### Weekly
Recommended block distribution across sections.

### Daily
Actual operational block schedule.

Key rule:
Monthly informs weekly; weekly informs daily; daily can trigger replanning upward.

---

## 10. Live Operations Screen

## Purpose
Monitor approved and active work.

## Layout
Top strip:
- active blocks count
- delayed tasks
- at-risk blocks
- nearing completion
- active emergencies

Main split:
Left:
- active block list

Center:
- live timeline of current operations

Right:
- field updates / notes / delay reports

Possible statuses:
- planned
- ready
- active
- delayed
- paused
- completed
- cancelled

---

## 11. Simulation / Replanning Screen

## Purpose
Test or respond to changing conditions.

Controls:
- inject emergency defect
- increase goods traffic
- delay train movement
- increase maintenance duration
- block cancellation
- crew unavailable

Output:
- before plan
- after plan
- tasks displaced
- train impact
- risk delta
- new plan version

Best layout:
two-column diff view

Left:
Current plan

Right:
Replanned version

Bottom:
summary of changes

---

## 12. Analytics Screen

## Purpose
Management and performance intelligence.

Tabs:
- Overview
- Zones
- Divisions
- Departments
- Blocks
- Maintenance Debt
- Reliability

Recommended visuals:
- maintenance debt trend
- block utilization trend
- coordination ratio
- corridor pressure ranking
- department completion rate
- planned vs actual duration
- emergency frequency

Avoid meaningless chart spam.

---

## 13. AI Copilot Screen

## Purpose
Natural-language interface over RailOS data and planner constraints.

Use cases:
- explain plan
- query sections at risk
- query why task excluded
- ask for alternate constraints
- ask for analytics summary

The copilot should sit beside the product, not replace the planner.

Layout:
Left: conversation
Right: contextual results cards / linked data

---

## 14. Notifications Screen

Grouped by:
- Critical
- Approval Required
- Warning
- Informational

Notification object must include:
- title
- severity
- source
- location
- related block/task
- timestamp
- CTA

---

## 15. Administration Screen

Low priority for hackathon.
Only include:
- users
- roles
- territory master data
- demo reset
- weights configuration
- notification thresholds

---

## 16. Mobile / PWA Layout

Mobile should not replicate desktop complexity.

### Mobile Nav
- Home
- Assignments
- Alerts
- Report Defect
- Profile

### Mobile Home
- next block
- assigned tasks
- urgent alerts
- quick actions

### Mobile Task Screen
- task details
- location
- time
- instructions
- start / delay / complete buttons

### Mobile Alert Screen
- critical notifications
- approval items
- plan changes

---

## 17. Role-based UX

### Control Officer
- command center
- block planner
- live operations
- approvals

### Divisional Planner
- maintenance
- planner
- calendar
- simulation

### Department Officer
- maintenance filters
- candidate tasks
- section details
- assigned blocks

### Field Supervisor
- PWA/mobile workflow
- assignment
- update
- defect reporting

### Management
- analytics
- overview
- reports

---

## 18. Frontend Build Priority

P0
- app shell
- command center
- network screen
- maintenance screen
- block planner
- timeline
- plan comparison
- explanation drawer
- simulation diff
- basic analytics

P1
- live operations
- notifications center
- AI Copilot

P2
- full admin
- advanced personalization