# RailOS Platform
## Integrated Product Requirement Document Suite

**Product:** RailOS  
**Category:** Railway Maintenance Planning & Operations Intelligence Platform  
**Primary Objective:** Automatically coordinate Engineering, Signal & Telecommunication (S&T), and Traction Distribution maintenance with train operations to maximize infrastructure availability, maintenance productivity, and operational reliability.

---

# 0. MASTER PLATFORM PRD

## 0.1 Product Vision

RailOS is a railway maintenance planning and operational intelligence platform that transforms independently maintained defect, maintenance, timetable, corridor, and block information into coordinated maintenance plans.

Instead of each department independently requesting blocks, RailOS continuously evaluates:

- infrastructure defects;
- preventive maintenance;
- overdue maintenance;
- asset criticality;
- corridor availability;
- passenger train timetable;
- goods train forecast;
- traction disconnection requirements;
- maintenance dependencies;
- workforce/resource constraints;
- existing blocks;
- emergency defects.

It then recommends coordinated maintenance blocks that minimize disruption to train operations while maximizing the amount and priority of maintenance completed during each possession window.

RailOS does **not** autonomously take control of railway operations.

It acts as a:

**Decision Intelligence + Optimization + Coordination Platform**

Final operational approval remains with authorized railway personnel.

---

# 0.2 Platform Components

RailOS consists of:

1. **Web Control Center**
2. **Progressive Web App**
3. **Android Field Application**
4. **RailOS Integration & API Platform**
5. **RailOS Notification & Escalation System**
6. **Railway-Wide Analytics & Intelligence Platform**

All six products operate on a common backend.

```text
                    RAILOS PLATFORM

 TMS ─────┐
 SMMS ────┤
 TDMS ────┤
 COA ─────┤
 BDMS ────┤
 Timetable│
 Forecast ┘
      │
      ▼
┌─────────────────────────────┐
│ Integration & API Platform  │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Unified Railway Data Model  │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ RailOS Intelligence Engine  │
│                             │
│ • Risk Engine               │
│ • Priority Engine           │
│ • Block Opportunity Engine  │
│ • Task Bundling Engine      │
│ • Constraint Optimizer      │
│ • Conflict Engine           │
│ • Replanning Engine         │
│ • Simulation Engine         │
└──────────────┬──────────────┘
               │
       ┌───────┼────────┬───────────┐
       ▼       ▼        ▼           ▼
      Web     PWA    Android    Notifications
       │       │        │
       └───────┴────────┘
               │
               ▼
        Railway Analytics
```

---

# 0.3 Primary Users

### Control Officer
Responsible for operational corridor and block decisions.

### Divisional Maintenance Planner
Coordinates maintenance requirements across departments.

### Engineering Officer
Handles track and civil infrastructure maintenance.

### S&T Officer
Handles signalling and telecommunications maintenance.

### Traction Distribution Officer
Handles OHE and traction infrastructure.

### Field Engineer / Supervisor
Executes assigned maintenance.

### Divisional Manager
Reviews operational and maintenance performance.

### Zonal Management
Views aggregated planning and performance.

### Railway Headquarters
Views railway-wide analytics.

### System Administrator
Controls users, integrations, policies and master data.

---

# 0.4 Core RailOS Intelligence Engines

## Maintenance Priority Engine

Every maintenance task receives a dynamic priority score.

Inputs may include:

- defect severity;
- safety criticality;
- overdue duration;
- statutory/inspection deadline;
- asset criticality;
- line traffic density;
- redundancy availability;
- consequence of failure;
- maintenance category;
- repeated defect history.

Illustrative calculation:

```text
Priority =
30% Safety Criticality
+ 20% Defect Severity
+ 15% Overdue Factor
+ 15% Asset Criticality
+ 10% Operational Impact
+ 10% Failure Risk
```

Weights must ultimately be configurable according to railway policy.

---

## Maintenance Risk Engine

Calculates the consequence of deferring work.

Outputs:

- Current Risk
- 24-hour Deferral Risk
- 72-hour Deferral Risk
- Risk Trend
- Recommended Maximum Deferral

---

## Block Opportunity Engine

Analyzes train movement and corridor availability to identify maintenance opportunities even when no department has manually requested a block.

Example:

```text
Opportunity OP-207

Section:
Ghaziabad – Aligarh

Window:
01:12 – 02:48

Available:
96 minutes

Traffic impact:
Low

Candidate maintenance:
7 tasks

Recommended bundle:
3 tasks
```

---

## Task Bundling Engine

Identifies tasks that can be completed during the same block.

Factors:

- geographical proximity;
- same track/section;
- work compatibility;
- isolation requirements;
- traction shutdown;
- task dependencies;
- crew availability;
- simultaneous execution ability.

---

## Constraint Optimization Engine

The optimizer evaluates thousands of possible combinations while respecting railway rules.

Objective:

```text
MAXIMIZE

Safety-critical work completed
+ Block utilization
+ Maintenance yield
+ Asset availability
+ Multi-department coordination

MINIMIZE

Passenger disruption
+ Goods disruption
+ Asset downtime
+ Maintenance debt
+ Unused possession time
+ Conflicting maintenance
```

Google OR-Tools CP-SAT is suitable for the prototype.

---

## Replanning Engine

Automatically recomputes plans when:

- emergency defect appears;
- train is delayed;
- goods forecast changes;
- maintenance takes longer than expected;
- workforce becomes unavailable;
- block is cancelled;
- weather restricts activity;
- an asset fails.

---

# 0.5 Core Platform KPIs

RailOS should calculate:

### Block Utilization

```text
Useful Maintenance Time
─────────────────────── × 100
Block Duration
```

### Maintenance Yield

```text
Weighted Maintenance Work Completed
────────────────────────────────────
Infrastructure Disruption Minutes
```

### Maintenance Debt

```text
Σ (Overdue Days × Task Risk × Asset Criticality)
```

### Asset Availability

Percentage of time an asset remains operationally available.

### Coordination Ratio

Percentage of blocks involving coordinated multi-department work.

### Critical Maintenance Completion Rate

### Planned vs Actual Block Duration

### Conflict Avoidance Count

### Train Disruption Minutes

### Emergency Replanning Response

---

# PRD 1 — RAILOS WEB CONTROL CENTER

# 1.1 Product Purpose

The Web Control Center is the primary RailOS command environment.

It is designed for:

- control offices;
- divisional planners;
- department officers;
- managers;
- administrators.

It should be optimized primarily for desktops and large control-room screens.

---

# 1.2 Main Goal

Allow authorized personnel to:

> Understand the network → identify risk → generate block plans → compare alternatives → approve plans → monitor execution → replan when disruption occurs.

---

# 1.3 Navigation

```text
RailOS
│
├── Command Center
├── Network
├── Block Planner
├── Maintenance
├── Live Operations
├── Calendar
├── Simulations
├── Analytics
├── AI Copilot
├── Notifications
└── Administration
```

---

# 1.4 Command Center

The landing screen should provide an operational overview.

### KPI Cards

- Critical Defects
- Overdue Maintenance
- Blocks Today
- Planned Maintenance Tasks
- Network Asset Availability
- Current Maintenance Debt
- Current Block Utilization
- Active Emergencies

### Network Condition

Sections represented using health status:

```text
Delhi ─ Ghaziabad ─ Aligarh ─ Tundla

 96%       83%         91%
           ⚠
```

### Today's Block Timeline

Shows:

- train paths;
- planned blocks;
- active maintenance;
- corridor windows;
- conflicts.

---

# 1.5 Network Digital Twin

Interactive simplified representation of railway corridors.

Each section displays:

- Track Health
- Signalling Health
- Traction Health
- Traffic Density
- Pending Maintenance
- Critical Defects
- Planned Blocks
- Next Available Window

Selecting a section opens its intelligence panel.

---

# 1.6 Maintenance Intelligence Center

Centralized maintenance data from TMS, SMMS and TDMS.

Columns:

- Task ID
- Department
- Asset
- Section
- KM
- Work Type
- Priority
- Severity
- Risk
- Due Date
- Overdue Days
- Duration
- Block Requirement
- Status

Filters:

- department;
- priority;
- corridor;
- risk;
- status;
- date;
- work type;
- block requirement.

---

# 1.7 Automatic Block Planner

The most important product screen.

User chooses:

- planning horizon;
- territory;
- planning objective;
- operational constraints.

Objectives:

### Safety First
Highest-risk maintenance receives maximum priority.

### Balanced
Balances maintenance and train operations.

### Operations First
Minimizes train disruption.

Then:

**Generate Plan**

The optimizer generates multiple alternatives.

---

# 1.8 Block Timeline

Example:

```text
             00:00  01:00  02:00  03:00

Train 12421  ███
Goods 83301                ███

ENG-104            █████████
SIG-220            ████
TRD-081               █████

BLOCK-028          █████████
```

Users can inspect every proposed block.

---

# 1.9 Block Detail Screen

Shows:

- block ID;
- location;
- track;
- start/end;
- duration;
- departments;
- tasks;
- traction isolation;
- staff;
- train impact;
- risk reduction;
- utilization;
- maintenance yield;
- optimization score.

Actions:

- Approve
- Reject
- Request Revision
- Lock
- Re-optimize
- Export
- Notify Departments

---

# 1.10 Why This Block?

Explainability panel.

Example:

```text
RECOMMENDATION SCORE: 91/100

+32 Critical defect
+21 Overdue maintenance
+18 Multi-department bundling
+16 Low train density
+10 Asset availability improvement
-06 Goods train interference
```

Natural-language explanation may be generated from structured solver output.

---

# 1.11 Weekly Planner

Displays 7-day maintenance plans.

Provides:

- section/day matrix;
- maintenance workload;
- train impact;
- unresolved maintenance;
- block utilization.

---

# 1.12 Monthly Planner

Provides strategic maintenance allocation.

Uses:

- known maintenance deadlines;
- recurring maintenance;
- possession requirements;
- planned engineering works;
- expected traffic.

Monthly plans become input constraints for weekly planning.

---

# 1.13 Emergency Replanning

Emergency defect can be injected manually or received through API.

System:

1. evaluates severity;
2. identifies affected section;
3. finds available windows;
4. checks trains;
5. identifies displaced work;
6. recomputes schedule;
7. proposes emergency block.

No change becomes operational until authorized.

---

# 1.14 Scenario Simulator

Controllers can simulate:

- goods traffic +20%;
- block cancellation;
- task duration +30 minutes;
- staff shortage;
- emergency defect;
- train delay;
- corridor closure.

System calculates downstream effects.

---

# 1.15 Three-Plan Comparison

Example:

| Metric | Safety | Balanced | Operations |
|---|---:|---:|---:|
| Critical Tasks Completed | 98% | 94% | 87% |
| Train Delay | 42 min | 18 min | 5 min |
| Block Utilization | 91% | 89% | 82% |
| Maintenance Debt Reduction | 32% | 27% | 18% |

---

# 1.16 AI Planning Copilot

Users can ask:

> What work should we prioritize tonight?

> Why wasn't ENG-144 scheduled?

> Generate a plan with zero passenger delays.

> What happens if goods traffic increases 30%?

Copilot must convert requests into structured system queries or optimization constraints.

LLM must not directly invent operational schedules.

---

# 1.17 User Roles

Role-based access controls.

### Controller
Plan approval and operations.

### Department Officer
Department maintenance management.

### Planner
Planning and optimization.

### Management
Read-only analytics and reports.

### Administrator
Configuration and permissions.

---

# 1.18 Hackathon MVP

MUST BUILD:

- Command Center
- Maintenance table
- Corridor view
- Block planner
- Block timeline
- Risk scoring
- Optimization
- Three-plan comparison
- Emergency replanning
- Explanation panel

DEFER:

- extremely granular administrative functionality;
- full GIS;
- real railway integration;
- enterprise SSO;
- production-grade audit infrastructure.

---

# PRD 2 — RAILOS PROGRESSIVE WEB APP

# 2.1 Purpose

Provide fast mobile/tablet access to RailOS without requiring application installation from an app store.

Target:

- supervisors;
- junior officers;
- controllers on the move;
- maintenance personnel;
- managers.

---

# 2.2 Product Principle

The PWA should not duplicate the entire Web Control Center.

It should support:

> View → Approve → Acknowledge → Report → Coordinate.

---

# 2.3 Key Features

### Today's Work

Displays:

- assigned blocks;
- assigned maintenance;
- start/end;
- location;
- work instructions;
- team.

---

### Block Details

```text
Block BLK-028

Ghaziabad – Aligarh
Down Main
01:15–02:45

Engineering
ENG-204 Rail Grinding

S&T
SIG-441 Track Circuit

Traction
TRD-119 OHE Inspection
```

---

### Approval Workflow

Authorized users receive:

```text
Block BLK-028 awaiting approval.

[View]
[Approve]
[Reject]
```

Critical approval actions require confirmation.

---

# 2.4 Report Defect

Form fields:

- department;
- asset;
- section;
- KM/location;
- defect category;
- severity;
- description;
- photographs;
- estimated work duration.

Submission immediately enters RailOS risk evaluation.

---

# 2.5 Offline Mode

PWA should cache:

- today's assignments;
- block instructions;
- safety information;
- task list.

Actions taken offline enter a local queue and synchronize after connectivity returns.

---

# 2.6 Push Notifications

Support:

- assignment;
- block approval;
- schedule change;
- emergency;
- cancellation;
- approaching start;
- approaching block end.

---

# 2.7 Quick Status Actions

```text
READY
WORK STARTED
WORK PAUSED
WORK COMPLETED
DELAYED
CANNOT COMPLETE
```

---

# 2.8 Mobile Block Timeline

Simplified timeline showing:

- active train windows;
- maintenance block;
- task progress.

No complex desktop planning controls.

---

# 2.9 PWA Authentication

Prototype:

- email/employee ID;
- password;
- role.

Production:

- railway identity provider;
- SSO;
- MFA;
- device/session controls.

---

# 2.10 Hackathon MVP

Build PWA from same Next.js application.

Implement:

- responsive layout;
- installable manifest;
- service worker;
- today's work;
- defect reporting;
- approval;
- push-style simulated notifications;
- offline demonstration.

Do not create another frontend codebase.

---

# PRD 3 — RAILOS ANDROID FIELD APPLICATION

# 3.1 Purpose

The Android Field Application is the dedicated execution interface for personnel working near railway infrastructure.

The app's function is:

> Execute the optimized plan safely and send real-world execution data back into RailOS.

---

# 3.2 Primary Users

- Permanent Way teams
- S&T maintainers
- TRD teams
- supervisors
- inspectors

---

# 3.3 Home Screen

```text
Good Evening

Tonight

2 Assigned Tasks
1 Maintenance Block
0 Emergencies

NEXT

Block BLK-028
01:15–02:45
Ghaziabad–Aligarh
```

---

# 3.4 Work Package

Every assignment contains:

- task number;
- asset;
- location;
- department;
- activity;
- planned duration;
- dependency;
- isolation requirement;
- block timing;
- work instructions;
- required completion evidence.

---

# 3.5 Start Work

Before enabling Start:

- correct block;
- task assigned;
- possession status;
- required safety acknowledgement.

Prototype can simulate checks.

---

# 3.6 Work Progress

Users update:

- started;
- 25%;
- 50%;
- 75%;
- completed;
- stopped;
- delayed.

The control center receives updates.

---

# 3.7 Delay Reporting

User selects:

- equipment failure;
- manpower shortage;
- work complexity;
- access delay;
- safety restriction;
- weather;
- other.

And enters:

```text
Estimated additional time:
+20 minutes
```

RailOS can evaluate whether the current block remains viable.

---

# 3.8 Emergency Defect Reporting

Field teams can report unexpected defects.

Inputs:

- photograph;
- department;
- severity;
- GPS/location where permitted;
- railway section;
- KM;
- text/voice description.

This triggers central evaluation.

---

# 3.9 Completion Evidence

Possible evidence:

- photo;
- checklist;
- measurements;
- inspection result;
- remarks;
- completion timestamp.

---

# 3.10 Offline-First Architecture

Critical field functionality must remain usable in poor connectivity.

Local SQLite/database stores:

- assignments;
- task information;
- cached maps/sections;
- queued updates.

Synchronize when network becomes available.

---

# 3.11 Safety Principle

The application must never independently authorize:

- possession;
- traction isolation;
- train movement;
- block extension.

It communicates authorized status received from RailOS/operations.

---

# 3.12 Hackathon Position

Do **not build the full Android application during the first hackathon unless the web system is already complete.**

Demonstrate the mobile workflow through the PWA first.

Android is Phase 2.

If time remains, produce:

- login;
- assignment list;
- work detail;
- progress update;
- defect reporting.

---

# PRD 4 — RAILOS API & INTEGRATION PLATFORM

# 4.1 Purpose

The Integration Platform is the backbone of RailOS.

Without this layer, RailOS is just another isolated application.

Its role is to normalize data from railway systems into one unified operational model.

---

# 4.2 Source Systems

Conceptual connectors:

### TMS
Track maintenance and defects.

### SMMS
Signalling maintenance and defects.

### TDMS
Traction distribution maintenance.

### COA
Operational train and corridor information.

### BDMS
Block demand / block management.

### Train Time Table
Scheduled passenger and other services.

### Goods Forecast
Projected freight movements.

---

# 4.3 Canonical Maintenance Model

```json
{
  "taskId": "ENG-1042",
  "department": "ENGINEERING",
  "assetId": "TRACK-442",
  "corridorId": "GZB-ALJN",
  "kmStart": 52.1,
  "kmEnd": 54.2,
  "taskType": "RAIL_REPLACEMENT",
  "severity": 9,
  "criticality": 10,
  "dueDate": "2026-09-09",
  "estimatedDuration": 90,
  "blockRequired": true,
  "tractionIsolationRequired": false,
  "status": "PENDING"
}
```

---

# 4.4 Train Movement Model

```json
{
  "trainId": "12421",
  "section": "GZB-ALJN",
  "entry": "01:03",
  "exit": "01:19",
  "trainClass": "PASSENGER",
  "priority": 10
}
```

---

# 4.5 Block Window Model

```json
{
  "windowId": "WIN-208",
  "section": "GZB-ALJN",
  "track": "DOWN",
  "start": "01:20",
  "end": "03:00",
  "availability": "AVAILABLE"
}
```

---

# 4.6 API Groups

```text
/api/auth

/api/assets
/api/corridors
/api/trains
/api/maintenance
/api/defects
/api/blocks

/api/optimization
/api/scenarios
/api/replanning

/api/notifications
/api/analytics

/api/integrations
```

---

# 4.7 Optimization API

Example:

```text
POST /optimization/generate
```

Request:

```json
{
  "section": "GZB-ALJN",
  "horizon": "WEEKLY",
  "objective": "BALANCED",
  "constraints": {
    "passengerDelay": 0
  }
}
```

Returns:

- generated plan;
- blocks;
- tasks;
- unresolved tasks;
- conflicts;
- metrics;
- explanation metadata.

---

# 4.8 Event Architecture

Important events:

```text
DEFECT_CREATED
TASK_UPDATED
BLOCK_PROPOSED
BLOCK_APPROVED
BLOCK_REJECTED
BLOCK_STARTED
BLOCK_ENDING
TASK_STARTED
TASK_DELAYED
TASK_COMPLETED
TRAIN_DELAY_CHANGED
EMERGENCY_CREATED
PLAN_REOPTIMIZED
```

These events drive notifications and analytics.

---

# 4.9 Integration Reliability

Production connectors need:

- schema validation;
- duplicate protection;
- idempotency;
- retries;
- timestamps;
- source identifiers;
- audit trails;
- reconciliation.

---

# 4.10 Hackathon Integration Strategy

Do not attempt real TMS/SMMS/TDMS integrations.

Create adapters such as:

```text
TMS Simulator
SMMS Simulator
TDMS Simulator
COA Simulator
```

Each exposes realistic synthetic data.

The RailOS core should not know whether data comes from:

```text
JSON
CSV
Mock API
or actual railway API
```

That is how you demonstrate integration readiness.

---

# PRD 5 — RAILOS NOTIFICATION & ESCALATION SYSTEM

# 5.1 Purpose

Scheduling is useless if the right person does not learn about a change quickly enough.

The Notification Engine converts RailOS events into actionable communication.

---

# 5.2 Notification Categories

### Informational
No response required.

### Action Required
Acknowledgement required.

### Approval Required
Authorized decision needed.

### Warning
Potential operational issue.

### Critical
Immediate intervention required.

---

# 5.3 Examples

```text
BLOCK APPROVAL REQUIRED

BLK-028
Ghaziabad–Aligarh
01:15–02:45

3 departments
4 maintenance tasks

Approval required before 23:30.
```

---

# 5.4 Emergency Alert

```text
CRITICAL DEFECT

Rail fracture detected
KM 172.4

Risk: 98/100

RailOS has generated Emergency Plan EP-04.

[Review Plan]
```

---

# 5.5 Notification Channels

Platform architecture should support:

- in-app;
- PWA push;
- Android push;
- email;
- SMS integration;
- enterprise messaging in future.

Hackathon:

Use in-app + browser notifications.

---

# 5.6 Intelligent Notification Routing

Notifications should depend on:

```text
Event
+
Location
+
Department
+
Severity
+
Role
+
Responsibility
```

A signalling defect should not notify every RailOS user.

---

# 5.7 Escalation Engine

Example:

```text
Block approval generated
        │
        ▼
Planner notified
        │
No response 10 minutes
        ▼
Control Officer notified
        │
No response
        ▼
Senior authority notified
```

Escalation timing must be configurable.

---

# 5.8 Notification Center

Tabs:

- All
- Action Required
- Critical
- Maintenance
- Blocks
- System

Each notification includes:

- timestamp;
- source;
- priority;
- related entity;
- acknowledgement status.

---

# 5.9 Quieting Noise

Avoid notification fatigue through:

- deduplication;
- grouping;
- severity thresholds;
- role filtering;
- acknowledgement tracking.

For example, 12 updates to the same block can become:

> BLK-028 has 12 updates.

instead of 12 individual alerts.

---

# PRD 6 — RAILWAY-WIDE ANALYTICS & INTELLIGENCE

# 6.1 Purpose

Operational planning solves today's problem.

Analytics should answer:

> Why do these problems keep happening?

This product transforms RailOS from a scheduler into a railway maintenance intelligence platform.

---

# 6.2 Management Levels

Analytics should support:

```text
Section
↓
Division
↓
Zone
↓
Railway
```

Users can drill downward.

---

# 6.3 Executive Dashboard

KPIs:

- Asset Availability
- Block Utilization
- Maintenance Yield
- Maintenance Debt
- Critical Defects
- Overdue Maintenance
- Planned vs Completed
- Train Disruption
- Emergency Blocks
- Coordination Ratio

---

# 6.4 Department Performance

Compare:

```text
Engineering
S&T
Traction
```

Metrics:

- tasks scheduled;
- tasks completed;
- overdue;
- average delay;
- block usage;
- completion efficiency;
- repeated defects.

Do not turn this automatically into employee performance scoring.

It is infrastructure/process analytics.

---

# 6.5 Maintenance Debt Heatmap

Example:

```text
Delhi             LOW
Ghaziabad         HIGH
Aligarh           MEDIUM
Tundla            CRITICAL
```

Helps management identify backlog concentration.

---

# 6.6 Asset Risk Analytics

Show:

```text
Top Assets by Risk

1. Track Segment 172A        96
2. Signal Relay SR-29        91
3. OHE Section OH-88         87
```

---

# 6.7 Block Efficiency Analytics

For every block:

```text
Allocated Duration
Actual Duration
Tasks Planned
Tasks Completed
Unused Time
Departments Coordinated
Maintenance Yield
```

Management can determine whether scarce possession time is being used effectively.

---

# 6.8 Planning Accuracy

Compare:

```text
PLANNED
vs
ACTUAL
```

For:

- duration;
- start time;
- task completion;
- resource requirements;
- train effect.

This historical data can eventually improve future estimates.

---

# 6.9 Conflict Analytics

Track:

- conflicts detected;
- conflicts avoided;
- causes;
- sections producing most conflicts;
- departments frequently competing for the same windows.

---

# 6.10 Corridor Analytics

Each corridor receives:

### Operational Load

### Maintenance Load

### Infrastructure Risk

### Block Scarcity

### Maintenance Debt

### Asset Availability

This produces a:

## Corridor Pressure Index

Example:

```text
Ghaziabad–Aligarh

Traffic Pressure       81
Maintenance Pressure   74
Infrastructure Risk    62
Block Scarcity         88

Corridor Pressure:
79 / 100
```

---

# 6.11 Predictive Intelligence — Future

Once historical real-world data exists:

### Maintenance Duration Prediction

Predict how long a maintenance activity is likely to take.

### Block Demand Forecast

Predict future demand for possession windows.

### Failure Risk Prediction

Estimate likelihood of asset deterioration/failure.

### Repeated Defect Detection

Identify assets repeatedly consuming maintenance resources.

### Seasonal Patterns

Analyze maintenance demand by weather/season.

These are true ML opportunities.

They should not be fabricated during the hackathon.

---

# 6.12 What-If Analytics

Management asks:

> What if we increase maintenance blocks by 10%?

RailOS simulation calculates:

- maintenance debt change;
- expected availability;
- train disruption;
- critical defect clearance;
- workload.

---

# 6.13 AI Analytics Assistant

Questions:

> Which division has the highest maintenance debt?

> Why did block utilization fall this month?

> Which sections repeatedly cause emergency maintenance?

> Show corridors where we can reduce maintenance debt without affecting passenger traffic.

The assistant should query RailOS analytics data rather than answer from general LLM knowledge.

---

# 6.14 Reporting

Generate:

### Daily Operations Report

### Weekly Block Efficiency Report

### Monthly Maintenance Performance Report

### Department Report

### Corridor Reliability Report

### Emergency Maintenance Report

### Executive Railway Availability Report

---

# SHARED SECURITY PRD

RailOS could eventually become critical railway infrastructure software.

Therefore production architecture should account for:

- role-based authorization;
- least privilege;
- MFA;
- audit trails;
- encrypted transport;
- encryption at rest;
- session controls;
- action logging;
- approval workflows;
- source provenance;
- API authentication;
- environment isolation;
- backups;
- disaster recovery.

---

# SHARED AUDIT SYSTEM

Every important action should produce:

```text
WHO
WHAT
WHEN
WHERE
WHY
OLD VALUE
NEW VALUE
```

Example:

```text
09:32:18

User:
CONTROL-104

Action:
Approved BLK-028

Plan Version:
17

Optimization Objective:
Balanced

Reason:
Accepted recommended plan.
```

Never silently overwrite approved operational plans.

Use versions.

---

# SHARED PLAN VERSIONING

Example:

```text
PLAN v1
Generated 22:03

PLAN v2
Goods forecast changed

PLAN v3
Emergency defect added

PLAN v4
Controller approved
```

This is important because optimization outputs can change throughout the day.

---

# COMPLETE USER FLOW

```text
TMS / SMMS / TDMS
        │
        ▼
Maintenance & Defects
        │
        ▼
Priority + Risk
        │
        ├──────── COA / Timetable / Goods Forecast
        │                          │
        └──────────────┬───────────┘
                       ▼
             Block Opportunities
                       │
                       ▼
                Task Bundling
                       │
                       ▼
               Optimization
                       │
          ┌────────────┼─────────────┐
          ▼            ▼             ▼
       Safety       Balanced      Operations
        Plan          Plan           Plan
          └────────────┬─────────────┘
                       ▼
              Controller Review
                       │
                       ▼
                    APPROVE
                       │
                       ▼
             Notify Departments
                       │
                       ▼
                  Field Work
                       │
                       ▼
                 Live Updates
                       │
              Delay / Emergency?
                    │       │
                   NO      YES
                    │       │
                    │       ▼
                    │   Reoptimizer
                    │       │
                    └───┬───┘
                        ▼
                 Work Completed
                        │
                        ▼
                    Analytics
```

---

# PLATFORM DATABASE DOMAINS

Recommended core entities:

```text
users
roles
permissions

zones
divisions
sections
corridors
tracks

assets
asset_types
asset_health

maintenance_tasks
maintenance_dependencies
defects
inspections

trains
train_movements
traffic_forecasts

block_windows
block_requests
block_plans
block_tasks
isolations

optimization_runs
optimization_candidates
plan_versions

work_assignments
work_updates
completion_reports

emergencies
incidents

notifications
acknowledgements

audit_logs
analytics_snapshots
```

---

# HACKATHON BUILD BOUNDARY

The major risk is attempting to build all six products in 36 hours.

Do **not**.

The architecture should describe all six.

The hackathon implementation should prove the core RailOS loop.

## Build Now

### Web Control Center — 80%

Build properly.

### PWA — 30%

Responsive field view inside same Next.js app.

### Android App — 0–10%

Only mockup or optional minimal prototype.

### APIs — 60%

Real APIs with mock source connectors.

### Notifications — 40%

Working in-app alerts.

### Analytics — 40%

Working dashboard based on generated plans.

---

# HACKATHON GOLDEN DEMO

## Step 1 — Data enters RailOS

```text
267 Maintenance Tasks
34 Defects
41 Train Movements
12 Available Windows
```

---

## Step 2 — RailOS detects maintenance pressure

```text
17 Critical Tasks
29 Overdue Tasks
Maintenance Debt: 841
```

---

## Step 3 — Block opportunity found

```text
01:05–02:35

Ghaziabad–Aligarh

Traffic Impact: LOW
```

---

## Step 4 — Three departments want maintenance

```text
Engineering
90 min

S&T
45 min

Traction
60 min
```

Manual approach:

```text
195 disruption minutes
```

RailOS:

```text
90-minute coordinated block
```

---

## Step 5 — Optimizer produces three plans

```text
SAFETY
BALANCED
OPERATIONS
```

Operator chooses Balanced.

---

## Step 6 — Explainability

RailOS shows:

```text
Why selected?

Critical maintenance
+ Multi-department compatibility
+ Low passenger density
+ 92% block utilization
```

---

## Step 7 — Plan approved

Mobile/PWA receives:

```text
BLK-028 ASSIGNED
```

---

## Step 8 — Field team starts maintenance

Control room sees status change in real time.

---

## Step 9 — Emergency

Inject:

```text
Critical rail defect
KM 72.4
```

---

## Step 10 — RailOS replans

Shows:

```text
4 blocks analyzed
2 tasks shifted
1 emergency block created
Passenger impact: 0 min
```

---

## Step 11 — Analytics

Show:

```text
Manual Simulation

Block Utilization       58%
Maintenance Yield       1.41
Maintenance Debt        841
Disruption              195 min


RailOS Simulation

Block Utilization       91%
Maintenance Yield       2.66
Maintenance Debt        612
Disruption               90 min
```

All figures should be labelled:

**Synthetic Hackathon Simulation**

That prevents you from making unsupported claims about actual railway performance.

---

# RECOMMENDED TECHNOLOGY

## Frontend

```text
Next.js
TypeScript
Tailwind CSS
shadcn/ui
Recharts
Framer Motion
```

---

## Backend

Either:

```text
FastAPI + Python
```

or:

```text
NestJS
```

Because OR-Tools works well with Python, FastAPI is the cleaner hackathon choice.

---

## Optimization

```text
Google OR-Tools
CP-SAT
```

---

## Database

```text
PostgreSQL
```

Supabase is acceptable for faster implementation.

---

## Realtime

```text
WebSockets
```

or Supabase Realtime.

---

## AI

Use LLM only for:

- natural language querying;
- plan explanation;
- converting instructions into optimizer constraints;
- analytics explanations.

Never make the LLM the scheduling engine.

---

# RECOMMENDED MONOREPO

```text
railos/
│
├── apps/
│   ├── control-center/
│   ├── field-pwa/
│   ├── android/
│   └── api/
│
├── packages/
│   ├── data-model/
│   ├── optimizer/
│   ├── risk-engine/
│   ├── opportunity-engine/
│   ├── bundling-engine/
│   ├── simulator/
│   ├── notification-engine/
│   ├── analytics-engine/
│   └── ai-copilot/
│
├── integrations/
│   ├── tms/
│   ├── smms/
│   ├── tdms/
│   ├── coa/
│   └── bdms/
│
├── datasets/
│   ├── assets/
│   ├── maintenance/
│   ├── timetable/
│   └── scenarios/
│
├── shared/
│   ├── types/
│   ├── validation/
│   └── config/
│
└── docs/
```

---

# AGENT OWNERSHIP

With Claude, Codex and Antigravity, do not allow all three to modify everything.

## Claude

Own:

```text
/docs
/packages/optimizer
/packages/risk-engine
/packages/opportunity-engine
/packages/bundling-engine
/packages/simulator
```

Use it for:

- architecture;
- mathematical model;
- constraints;
- scheduling logic;
- scenario design.

---

## Codex

Own:

```text
/apps/api
/packages/data-model
/integrations
/database
/tests
```

Use it for:

- implementation;
- endpoints;
- schemas;
- migrations;
- integration;
- tests;
- debugging.

---

## Antigravity

Own:

```text
/apps/control-center
/apps/field-pwa
```

Use it for:

- UI;
- dashboard;
- timeline;
- digital twin;
- animations;
- responsive views;
- visual polish.

---

# DEVELOPMENT PRIORITY

Build in this exact dependency order:

```text
1. Unified data schema

2. Synthetic dataset

3. Maintenance priority/risk

4. Corridor windows

5. Bundling

6. Optimization

7. Optimization API

8. Block planner UI

9. Timeline

10. Explainability

11. Emergency replan

12. PWA field workflow

13. Notifications

14. Analytics

15. AI Copilot

16. Visual polish
```

Do not start with the chatbot.

Do not start with Android.

Do not spend six hours building authentication.

The optimizer + visual proof of improvement is the product.

---

# FINAL PRODUCT POSITIONING

## RailOS

**Railway Maintenance Intelligence & Automatic Block Planning Platform**

> RailOS unifies infrastructure maintenance, defect, train movement and corridor availability data to automatically identify maintenance opportunities, coordinate multi-department work, generate optimized block plans, dynamically respond to operational disruptions, and provide railway-wide maintenance intelligence while keeping authorized railway personnel in control of operational decisions.

The six products then have very clear responsibilities:

```text
WEB CONTROL CENTER
Plan and control

PWA
Approve and coordinate

ANDROID
Execute in the field

API PLATFORM
Connect railway systems

NOTIFICATIONS
Communicate and escalate

ANALYTICS
Measure, learn and improve
```

That is the RailOS ecosystem.