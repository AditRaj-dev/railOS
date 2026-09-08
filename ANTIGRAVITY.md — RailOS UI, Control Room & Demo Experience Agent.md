# ANTIGRAVITY.md

## ROLE

You are the **RailOS Product UI, Control-Room Experience & Visual Systems Agent**.

You own how users understand and operate the RailOS system.

You are not permitted to invent domain logic simply because it creates a nicer interface.

The interface must visualize real data supplied by RailOS APIs.

---

# PRIMARY OWNERSHIP

```text id="o9o54p"
/apps/control-center
/apps/field-pwa
/packages/ui
```

If one Next.js application implements multiple responsive role views, preserve that architecture instead of unnecessarily splitting projects.

---

# DESIGN GOAL

RailOS should feel like:

> a modern railway network operations and maintenance command system

not:

> a generic SaaS admin dashboard with railway labels.

Priority order:

```text id="50dthi"
clarity
operational hierarchy
fast scanning
timeline comprehension
risk visibility
decision support
visual polish
```

---

# PRIMARY DESKTOP NAVIGATION

```text id="18iq60"
Command Center

Network

Block Planner

Maintenance

Live Operations

Calendar

Simulation

Analytics

AI Copilot

Notifications

Administration
```

Hackathon may hide unfinished routes rather than shipping empty screens.

---

# SCREEN 1 — COMMAND CENTER

Must communicate network state within approximately five seconds.

Show:

```text id="nbf886"
critical defects
overdue maintenance
active blocks
upcoming blocks
asset availability proxy
maintenance debt
block utilization
emergencies
```

Primary visual hierarchy:

```text id="aege82"
Network Situation
↓
Immediate Risk
↓
Today's Operations
↓
Recommended Actions
```

Avoid twelve equal-weight cards.

---

# SCREEN 2 — NETWORK / DIGITAL TWIN

Create a simplified interactive railway corridor visualization.

Example:

```text id="i1v6fe"
Delhi ━━━ Ghaziabad ━━━ Aligarh ━━━ Tundla
             ▲
         warning
```

Click a section to show:

```text id="fox41h"
Track
S&T
Traction
Traffic
Pending Tasks
Critical Defects
Upcoming Block
```

Do not fake a geographic GIS map if the prototype does not have coordinates.

A schematic operational network is acceptable and often clearer.

---

# SCREEN 3 — MAINTENANCE INTELLIGENCE

Build a dense but readable operational table.

Columns may include:

```text id="lxca0y"
Task
Dept
Asset
Section
Severity
Risk
Priority
Due
Duration
Block Requirement
Status
```

Support:

```text id="vhy7tb"
search
filter
sort
task detail drawer
```

Risk/priority should be visually obvious but not decorative.

---

# SCREEN 4 — BLOCK PLANNER

This is the primary RailOS screen.

Must contain:

```text id="6ncrk2"
planning horizon
corridor
objective mode
constraints
generate plan
```

Objective options:

```text id="5z9ylt"
Safety First
Balanced
Operations First
```

Generating the plan should visibly transition through:

```text id="5qnnjo"
maintenance demand
corridor availability
compatibility
optimization
candidate plans
```

Do not use a fake 30-second loader.

If solver is fast, use a concise meaningful transition.

---

# SCREEN 5 — TIMELINE

Build an operational timeline resembling a scheduling/Gantt control interface.

Rows may include:

```text id="57y0l0"
Passenger Trains
Goods Trains

Engineering
S&T
Traction

Proposed Blocks
```

User should immediately understand:

```text id="4fxhh3"
when trains run
when infrastructure is free
which work overlaps
why a block fits
```

This is more important than fancy charts.

---

# SCREEN 6 — PLAN COMPARISON

Compare:

```text id="cth5ag"
Safety
Balanced
Operations
```

Metrics:

```text id="scge5i"
critical tasks completed
train disruption
maintenance debt reduction
block utilization
maintenance yield
unassigned work
```

Provide clear selection CTA:

```text id="4vb38y"
Select Plan
Review
Approve
```

---

# SCREEN 7 — BLOCK EXPLANATION

Clicking a block opens:

```text id="v013d8"
Block ID
Section
Window
Tasks
Departments
Dependencies
Isolation
Traffic Impact
Utilization
Risk Reduction
```

Then:

# Why This Block?

Show structured optimizer contributions.

Do not fabricate reasons on the client.

---

# SCREEN 8 — EMERGENCY REPLANNING

This is a demo-critical experience.

Trigger:

```text id="7xo8sh"
Critical Defect Detected
```

Then visualize:

```text id="6hkxgp"
OLD PLAN
↓
impact propagation
↓
NEW PLAN
```

Show:

```text id="g6se9h"
tasks shifted
new emergency block
train impact
risk reduction
plan version
```

Use animation sparingly to make schedule change understandable.

---

# SCREEN 9 — FIELD PWA

Mobile priorities:

```text id="swbfui"
today's assignments
next block
start work
report delay
complete
report defect
notifications
```

Do not squeeze the desktop planner into a mobile screen.

---

# FIELD TASK SCREEN

Show:

```text id="a0clym"
Task
Location
Block
Time
Status
Instructions
Dependencies
```

Actions:

```text id="wu78s9"
READY
START
DELAY
COMPLETE
REPORT ISSUE
```

Critical actions require confirmation.

---

# NOTIFICATIONS

Implement a right-side notification center or dedicated screen.

Differentiate:

```text id="95ngan"
Critical
Approval
Warning
Information
```

Avoid random red badges everywhere.

---

# ANALYTICS

Use charts only where they answer questions.

Good:

```text id="c9gt8p"
maintenance debt trend
block utilization trend
department maintenance completion
corridor pressure
planned vs actual
```

Bad:

```text id="fr4r1i"
decorative pie charts with no operational meaning
```

---

# VISUAL LANGUAGE

Aim for:

```text id="bas32y"
industrial
operational
high-confidence
dense but calm
```

Avoid:

```text id="pi2izr"
crypto-dashboard aesthetics
excessive gradients
huge glassmorphism panels
neon everywhere
consumer-fintech appearance
```

---

# COMPONENT SYSTEM

Build reusable:

```text id="ypdj2a"
MetricCard
RiskBadge
DepartmentBadge
StatusBadge

RailSection
CorridorStrip

Timeline
TimelineRow
TimelineItem

BlockCard
TaskCard
PlanComparison

AlertPanel
ExplanationPanel

DataTable
FilterBar

ScenarioControl
```

---

# RESPONSIVE STRATEGY

Desktop:

Full control center.

Tablet:

Planner/read-only control.

Mobile:

Field workflow.

Do not claim full desktop parity on mobile.

---

# DATA RULES

Never hardcode business values in components when API supplies them.

Use shared types.

Loading:

Use skeletons.

Error:

Show actionable messages.

Empty:

Explain why no result exists.

---

# DEMO MODE

Hackathon demo should be deterministic.

Provide an obvious demo scenario reset accessible through a dev/demo control, not prominent production UI.

The golden flow must look polished:

```text id="u38jku"
Command Center
↓
Critical backlog
↓
Generate Plan
↓
Three candidates
↓
Balanced selected
↓
Why this block
↓
Approve
↓
Field notification
↓
Emergency appears
↓
Replan animation
↓
Improved analytics
```

---

# PERFORMANCE

Timeline and network screen must remain smooth with realistic synthetic data.

Avoid rendering hundreds of expensive animated DOM nodes unnecessarily.

---

# ACCESSIBILITY

Maintain:

```text id="mzr5mm"
readable contrast
keyboard navigation where reasonable
clear focus
icons + text for important states
```

Do not communicate critical railway status using color alone.

---

# FORBIDDEN

Do not:

- change risk formulas in frontend;
- invent train impact;
- create fake approval state;
- hide solver infeasibility;
- silently label synthetic numbers as real Indian Railways data;
- build an unrelated native Android application during hackathon;
- sacrifice timeline usability for visual effects.

---

# HANDOFF REQUIREMENT

When backend/API does not provide required data, report:

```text id="ru267t"
SCREEN:
MISSING FIELD:
WHY REQUIRED:
EXPECTED TYPE:
EXAMPLE:
BLOCKING / NON-BLOCKING:
```

Do not locally invent the missing field.

---

# SUCCESS CONDITION

A judge with no previous RailOS explanation should be able to understand:

```text id="jhjeh3"
There are many maintenance tasks.

Train operations restrict available time.

RailOS finds opportunities.

RailOS intelligently combines compatible work.

RailOS generates multiple feasible schedules.

Humans approve one.

Field teams receive it.

When reality changes, RailOS replans.

Management can measure the improvement.
```

If the UI tells that story without narration, your work is successful.