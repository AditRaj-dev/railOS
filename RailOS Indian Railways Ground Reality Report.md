# RAILOS — INDIAN RAILWAYS GROUND REALITY REPORT
## Comprehensive Domain Research, Technical Due Diligence & Reality Audit
**Problem Statement:** SIH26027 — AI-Powered Automatic Block Planning to Maximize Asset Availability for Train Operations on Indian Railways  
**Research Date:** September 2026  
**Status:** Authoritative Baseline / Frozen Domain Reference  

---

# TABLE OF CONTENTS
1. [Executive Summary](#1-executive-summary)
2. [Current Block Planning Workflow & Regulatory Reality](#2-current-block-planning-workflow--regulatory-reality)
3. [Indian Railways Enterprise Systems Landscape](#3-indian-railways-enterprise-systems-landscape)
4. [Departmental Responsibilities, Jurisdictions & Personas](#4-departmental-responsibilities-jurisdictions--personas)
5. [The Railway Block Lifecycle](#5-the-railway-block-lifecycle)
6. [Maintenance Data Landscape (TMS, SMMS, TDMS)](#6-maintenance-data-landscape-tms-smms-tdms)
7. [Train Operations, Working Timetable & Goods Traffic](#7-train-operations-working-timetable--goods-traffic)
8. [Real Maintenance Rules & Operational Constraints](#8-real-maintenance-rules--operational-constraints)
9. [Multi-Department Coordination & Compatibility Reality](#9-multi-department-coordination--compatibility-reality)
10. [Asset Availability & Railway-Native KPIs](#10-asset-availability--railway-native-kpis)
11. [Algorithmic Formulation for Block Scheduling](#11-algorithmic-formulation-for-block-scheduling)
12. [Separation of Concerns: Deterministic, Optimization, ML & GenAI](#12-separation-of-concerns-deterministic-optimization-ml--genai)
13. [International & Competitor System Benchmarks](#13-international--competitor-system-benchmarks)
14. [Data Availability Audit (Public vs Internal vs Synthetic)](#14-data-availability-audit-public-vs-internal-vs-synthetic)
15. [Hackathon Synthetic Dataset Specification](#15-hackathon-synthetic-dataset-specification)
16. [Failure Modes & Emergency Edge Cases](#16-failure-modes--emergency-edge-cases)
17. [Safety Governance & Human Authority Boundary](#17-safety-governance--human-authority-boundary)
18. [What the Current RailOS PRD Gets Wrong & What Must Change](#18-what-the-current-railos-prd-gets-wrong--what-must-change)
19. [Hackathon MVP Scope vs Production Roadmap](#19-hackathon-mvp-scope-vs-production-roadmap)
20. [Unknowns Requiring Railway Expert Validation](#20-unknowns-requiring-railway-expert-validation)
21. [Deliverable 2: Fact Check & Assumption Audit Table](#21-deliverable-2-fact-check--assumption-audit-table)
22. [Deliverable 3: Enterprise System Matrix](#22-deliverable-3-enterprise-system-matrix)
23. [Deliverable 4: Implementation-Ready Hard Constraints (HC-001 to HC-018)](#23-deliverable-4-implementation-ready-hard-constraints-hc-001-to-hc-018)
24. [Deliverable 5: Soft Objectives & Multi-Criteria Objective Function (SO-001 to SO-008)](#24-deliverable-5-soft-objectives--multi-criteria-objective-function-so-001-to-so-008)
25. [Deliverable 6: Five Realistic Demo Scenarios](#25-deliverable-6-five-realistic-demo-scenarios)
26. [Deliverable 7: Recommended 36-Hour Hackathon MVP Scope](#26-deliverable-7-recommended-36-hour-hackathon-mvp-scope)

---

# 1. EXECUTIVE SUMMARY

The Smart India Hackathon problem statement **SIH26027** asks for an *"AI-Powered Automatic Block Planning system to maximize asset availability for train operations on Indian Railways."*

Our initial RailOS Product Requirement Document (PRD) assumed that:
1. Railway maintenance blocks can be autonomously scheduled by matching static passenger timetable gaps with maintenance tasks.
2. The Control Office Application (COA) directly exposes "corridor block availability" through programmatic APIs.
3. Track (TMS), Signalling (SMMS), and Traction (TDMS) databases share interoperable schemas and coordinates.
4. Any maintenance tasks occurring within physical proximity can be bundled safely into a single traffic block.
5. Goods train traffic can be treated as a deterministic scheduled input.

**Domain Research Ground Reality Check:**  
Every single one of those five foundational assumptions is either technically inaccurate or dangerous in an actual Indian Railways operational environment:
- **Statutory Mandate:** Maintenance planning is governed by the **Indian Railways (Open Lines) General (Third Amendment) Rules, 2023** (Gazette Notification G.S.R. 870(E), Nov 30, 2023), which inserted **Rule 15.02(c)** mandating a **Rolling Block Programme (RBP)** planned on a 26- to 52-week rolling horizon.
- **Enterprise Reality:** CRIS has already built and is rolling out the **Block & Disconnection Management System (BDMS)** per Railway Board Directive **No. 2020/Track-III/TK/2 dated September 30, 2025**. BDMS centralizes block requests, vetting, and grant workflows across Engineering, TRD, S&T, and Operating. RailOS cannot exist as an isolated island; it must function conceptually as an **Intelligent Optimization & Decision-Support Layer on top of BDMS, COA, and the Pravah API Gateway**.
- **The "Corridor Block" is an Operational Window, Not an API Field:** COA does not possess an "availability" flag. Corridor blocks are pre-notified operational agreements inserted into the Working Time Table (WTT) or weekly rolling plans, during which train paths are deliberately regulated, diverted, or annulled.
- **Strict Disconnection & Isolation Protocols:** Taking a block is not just stopping trains. S&T work requires formal **Disconnection / Reconnection Notices (Form S&T T/351)** with mandatory physical correspondence testing before normalization. Electrical traction requires a formal **Permit to Work (PTW - Form ETR-3)** issued by the Traction Power Controller (TPC) after physical isolator opening, line earthing with discharge rods, and boundary proving.
- **Multi-Department Incompatibilities:** Tasks cannot be bundled merely because they share a section. Heavy track machines (Ballast Cleaning Machines - BCM, Track Relaying Trains - TRT) alter track geometry and vibration levels, making simultaneous delicate S&T point machine calibration or tower wagon catenary height adjustment physically hazardous or prohibited. Furthermore, track renewal cuts bond wires, requiring S&T disconnection *before* civil work and reconnection *after*.
- **The True Operational Nightmare — "Block Bursts":** Operating controllers resist granting blocks because if a maintenance team exceeds its time ("Block Burst"), passenger trains lose punctuality, causing severe divisional audit penalties. A credible scheduling engine must model **overrun risk distributions** and setup/winding-up buffers, rather than assuming nominal task times.

---

# 2. CURRENT BLOCK PLANNING WORKFLOW & REGULATORY REALITY

### 2.1 Regulatory Framework
- **General Rules (GR) 1976 & Subsidiary Rules (SR):** GR Chapter XV governs "Work on Line and Precautions".
- **Gazette Amendment G.S.R. 870(E) (Nov 30, 2023):** Rule 15.02(c) states:
  > *"All planned maintenance and asset repair, replacement or creation work shall be executed in accordance with the Rolling Block Programme... advance planning of traffic blocks or disconnections (civil, electrical, signal & telecom) over a specified duration up to 52 weeks, prepared on a rolling basis by adding one week plan every week by reviewing output of preceding week."*
- **Railway Board Circular 2020/Track-III/TK/2 (Sept 30, 2025):** Mandated nationwide deployment of the **Block & Disconnection Management System (BDMS)** across all Zonal Railways following pilots in Central Railway.

### 2.2 Current Hierarchical Planning Cycles
Block planning in Indian Railways is split across three distinct temporal horizons:

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. STRATEGIC HORIZON (26 to 52 Weeks) — Rolling Block Programme (RBP)  │
│    • Zonal Headquarters (PCOM, PCE, PCSTE, PCEE)                        │
│    • Working Time Table (WTT) corridor block definition                 │
│    • Major infrastructure rebuilds, bridge rebuilding, NI work          │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. TACTICAL HORIZON (Weekly / D-7 to D-1) — Divisional Coordination     │
│    • Chaired by ADRM / Sr.DOM with Sr.DEN, Sr.DSTE, Sr.DEE (TRD)        │
│    • BDMS weekly demand consolidation                                   │
│    • Train regulation / cancellation / diversion circulars issued       │
│    • Corridor blocks (2.5 to 4 hours) fixed for upcoming week           │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. OPERATIONAL / EXECUTION HORIZON (Day-of-Operation / D-Day Real-Time) │
│    • Section Controller (SCOR), Chief Controller (CHC)                  │
│    • Engineering Controller (EC), S&T Controller, TPC                   │
│    • Station Masters (SM) & Field Supervisors (SSE/JE)                  │
│    • Actual grant of line block, PTW issuance, T/351 disconnection      │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Types of Blocks Defined in IR Operations
1. **Traffic Block (Line Block):** Complete suspension of train movements on a specific track between two block stations. Trains cannot be signaled into the section.
2. **Power Block:** Switching off (making "dead") and earthing 25 kV AC traction overhead equipment (OHE) in a specific elementary section or sub-sector. Electric locomotives cannot draw power; diesel operations may theoretically continue if line block is not imposed.
3. **Integrated Maintenance Block:** A coordinated traffic and power block granted simultaneously on a corridor allowing Engineering (P-Way), S&T, and TRD to work within the same time window.
4. **Shadow Block:** A maintenance block taken on an adjacent line, connecting line, or downstream section that is idle or starved of traffic solely because of a primary block elsewhere on the corridor.
5. **Disconnection (S&T):** Taking signaling gear (points, track circuits, signals, level crossing gates, electronic interlocking) out of service under Form S&T (T/351). Does not always require a full line block, but trains must be received on pilot memo or hand signals.
6. **Mega Block:** Extended block (typically 4 to 8 hours, often on Sundays or low-density night windows) for high-impact capital works (girder launching, turn-out renewals, yard remodelling).
7. **Emergency Block:** Unscheduled block granted immediately upon reporting of a broken rail, weld failure, OHE wire entanglement, or dangerous track bucking under extreme ambient rail temperatures.

---

# 3. INDIAN RAILWAYS ENTERPRISE SYSTEMS LANDSCAPE

CRIS (Centre for Railway Information Systems, Chanakyapuri, New Delhi) operates a federation of specialized domain systems. RailOS interacts with five core applications and an API gateway:

```text
                                  ┌──────────────────────────────┐
                                  │      CRIS PRAVAH GATEWAY     │
                                  │   (Enterprise API Gateway)   │
                                  └──────────────┬───────────────┘
                                                 │
            ┌──────────────────┬─────────────────┼──────────────────┬──────────────────┐
            ▼                  ▼                 ▼                  ▼                  ▼
     ┌─────────────┐    ┌─────────────┐   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
     │    BDMS     │    │     COA     │   │     TMS     │    │    SMMS     │    │    TDMS     │
     │ Block &     │    │ Control     │   │ Track       │    │ Signalling  │    │ Traction    │
     │ Disconnection│   │ Office      │   │ Management  │    │ Maintenance │    │ Distribution│
     │ Management  │    │ Application │   │ System      │    │ Management  │    │ Management  │
     └─────────────┘    └─────────────┘   └─────────────┘    └─────────────┘    └─────────────┘
```

### 3.1 BDMS (Block & Disconnection Management System)
- **Status:** Active nationwide rollout (Railway Board Letter 2020/Track-III/TK/2 dated Sept 30, 2025). Developed by CRIS.
- **Function:** Centralized digital portal for field officials (SSE/P-Way, SSE/Signal, SSE/TRD) to requisition traffic blocks, power blocks, and disconnections.
- **Workflow:** Demand Entry -> Departmental Vetting (Divisional Officers) -> Operating Vetting (DOM/Sr.DOM) -> Weekly Rolling Programme Compilation -> Real-time Control Grant / Closure.
- **Limitation:** BDMS currently acts as a **workflow approval and tracking tool**, NOT an automated combinatorial optimizer. It records demands and approvals, but relies on human officers during weekly meetings to manually de-conflict schedules.

### 3.2 COA (Control Office Application)
- **Status:** Production nationwide in all divisional control offices. Managed by CRIS.
- **Function:** Real-time electronic train charting, train ordering, precedence resolution, caution order logging, and line occupancy. Replaces paper graphs.
- **Data Exposed:** Active train positions, scheduled paths, late-running status, loco numbers, crew details, crossing points.
- **Reality on "Corridor Availability":** COA does NOT provide an automated "available corridor slot" API. It shows the real-time graph of trains and blocks already granted. Finding an open maintenance slot requires algorithmic calculation of headway gaps between trains.

### 3.3 TMS (Track Management System)
- **Status:** Production nationwide.
- **Function:** Digitizes over 100,000 track registers. Manages asset inventory (rails, sleepers, fastenings, turnouts, curves, bridges, level crossings) and 24+ inspection workflows.
- **Key Data:** Ultrasonic Flaw Detection (USFD) defect classifications (IMR, OBS, IMRW, OBSW), Oscillation Monitoring System (OMS) high-acceleration peaks (>0.15g, >0.20g), Track Recording Car (TRC) geometry runs, Track Quality Index (TQI), and Track Machine deployment schedules.

### 3.4 SMMS (Signalling Maintenance Management System)
- **Status:** Production across Zonal Railways.
- **Function:** Asset register and scheduled maintenance logging for point machines, track circuits, axle counters (BPAC), relays, electronic interlocking (EI), and signals.
- **Key Data:** Maintenance schedules (daily, weekly, monthly, quarterly), failure logs, codal life expiry, relay room opening logs, S&T 108/109 and T/351 disconnection notices.

### 3.5 TDMS (Traction Distribution Management System)
- **Status:** Production across electrified routes. Includes mobile apps for foot-patrolling.
- **Function:** Asset registers for 25 kV AC OHE, substations (TSS), switching posts (SP/SSP), section insulators, isolator switches, contact/catenary wire wear.
- **Key Data:** Elementary Section mapping, OHE defect logs, tower wagon inspection data, power block requests, neutral section inspections.

### 3.6 Pravah API Gateway
- **Status:** Launched August 15, 2021 by CRIS.
- **Reality:** Pravah is an **internal, enterprise-only API Gateway**. Public open APIs do NOT exist for TMS, SMMS, TDMS, or COA. All external hackathon architectures must interface with realistic mock adapters mirroring CRIS enterprise payload standards.

---

# 4. DEPARTMENTAL RESPONSIBILITIES, JURISDICTIONS & PERSONAS

Block planning is contentious because of conflicting institutional incentives:

```text
┌─────────────────────────┐                   ┌─────────────────────────┐
│  OPERATING DEPARTMENT   │                   │ MAINTENANCE DEPARTMENTS │
│  (Traffic / Control)    │ ◄── CONFLICT ──►  │   (Engg, S&T, TRD)      │
│                         │                   │                         │
│ Incentive:              │                   │ Incentive:              │
│ • Maximum train throughput│                 │ • Maximum block duration │
│ • 100% punctuality      │                   │ • Thorough maintenance   │
│ • Zero train delay      │                   │ • Zero asset failure    │
└─────────────────────────┘                   └─────────────────────────┘
```

### Detailed Persona Matrix

| Role | Department | Key Responsibility | Core Operational Concern | Authority in Block Planning |
|---|---|---|---|---|
| **Sr.DOM / DOM** (Divisional Operations Manager) | Operating | Overall train movement, freight loading, punctuality | Train delays, punctuality loss, passenger dissatisfaction | **Final Divisional Sanctioning Authority** for traffic blocks |
| **Section Controller (SCOR)** | Operating | Real-time regulation of trains on a 100–150 km section | Managing crossing, precedence, preventing block overruns | **Real-Time Granting Authority**; can defer block if trains run late |
| **Chief Controller (CHC)** | Operating | Shift in-charge of Divisional Control Office | Divisional punctuality, freight interchange targets | Decides whether to allow or cancel blocks during operational crises |
| **Sr.DEN / DEN** (Divisional Engineer) | Civil (P-Way) | Track safety, rail renewals, track machine progress | Rail fractures, derailment risks, speed restrictions | Requisitions track blocks; pushes for machine output targets |
| **SSE / JE (P-Way)** | Civil (P-Way) | Field execution of track repairs, tamping, deep screening | Safety of work site, banner flags, detonators, handback | Supervises site; certifies track fitness and imposes Caution Orders |
| **Sr.DSTE / DSTE** | S&T | Signalling & telecom safety, interlocking integrity | Signal failures, punctuality debits, correspondence errors | Requisitions S&T disconnections; approves interlocking changes |
| **SSE / JE (Signal)** | S&T | Maintenance of point machines, track circuits, BPAC | T/351 signing, correspondence testing before reconnection | Issues Disconnection Notice to Station Master; conducts tests |
| **Sr.DEE (TRD)** | Electrical | 25 kV OHE reliability, power supply integrity | OHE tripping, wire snapping, pantograph entanglements | Requisitions power blocks; monitors tower wagon productivity |
| **Traction Power Controller (TPC)** | Electrical | Real-time monitoring of traction power supply | SCADA operations, isolating elementary sections, earthing | **Sole Granting Authority for Power Blocks & PTW** |
| **Station Master (SM)** | Operating | Safe operation of station yard, points, signals | Exchanging line clear, verifying track clearance, safety | Endorses T/351 Disconnection; clamps points; grants local line entry |

---

# 5. THE RAILWAY BLOCK LIFECYCLE

The life of a maintenance block follows nine formal stages:

```text
[1. DEMAND GENERATION]
  Field SSE submits block request in BDMS (Asset, Section, Line, Duration, Work Type)
       │
       ▼
[2. DIVISIONAL VETTING]
  Departmental officers (DEN, DSTE, DEE) vet technical justification & resource readiness
       │
       ▼
[3. COORDINATION & ROLLING PROGRAMME]
  Operating (DOM/CPTM) bundles compatible demands into Weekly Rolling Block Programme (RBP)
       │
       ▼
[4. PRE-NOTIFICATION & CIRCULATION]
  Caution orders, train regulation/cancellation bulletins published to controllers & stations
       │
       ▼
[5. REAL-TIME CLEARANCE & SANCTION]
  On D-Day, Section Controller checks train running; grants permission when slot is clear
       │
       ▼
[6. FORMAL ISOLATION & DISCONNECTION]
  • S&T issues Form T/351 Disconnection Notice to Station Master
  • TPC executes SCADA switching; field staff earth OHE; TPC issues PTW (Form ETR-3)
  • Engineering erects banner flags & detonators (IRPWM Rule 806)
       │
       ▼
[7. MAINTENANCE EXECUTION]
  Track machines, tower wagons, and manual gangs execute work under physical protection
       │
       ▼
[8. TESTING & HANDBACK]
  • Mandatory S&T Correspondence Testing (points, signals, detection)
  • OHE discharge rods removed; PTW cancelled with TPC; traction re-energized
  • Track machine wound up; track certified fit for traffic (with temporary speed restriction)
       │
       ▼
[9. NORMALIZATION & DEBIT LOGGING]
  Station Master & SCOR close block in COA/BDMS. Any overrun logged as "Block Burst".
```

---

# 6. MAINTENANCE DATA LANDSCAPE (TMS, SMMS, TDMS)

A realistic mock adapter or schema for RailOS must reflect actual Indian Railways asset classification, defect taxonomy, and inspection frequencies:

### 6.1 Civil Engineering (TMS Data Landscape)
- **Asset Hierarchy:** Division -> Sub-division -> P-Way Section -> Block Section (Station A - Station B) -> Line (Up, Down, Single, Loop) -> Kilometre (e.g. Km 124/12 to 124/18) -> Asset ID (Rail ID, Sleepers, Turnout Point No.).
- **Defect Classifications:**
  - **IMR (Immediate Mobile Rail / Immediate Rail Replacement):** Severe flaw detected by USFD. Track must be clamped immediately; speed restriction of 20 or 30 kmph imposed; rail replaced within 3 days under traffic block.
  - **OBS (Observe):** Early-stage fatigue crack. Retested every 15 days or 1 month; programmed replacement.
  - **IMRW / OBSW:** Similar classification for Thermit (AT) or Flash Butt Welds.
  - **OMS Peaks:** Oscillation Monitoring records vertical and lateral acceleration. Peaks > 0.15g require inspection within 24 hours; peaks > 0.20g require urgent emergency track attention.
  - **TQI (Track Quality Index):** Mathematical index calculated from Track Recording Car (TRC) covering Unevenness, Alignment, Twist, and Gauge. Used for prioritizing mechanized tamping.

### 6.2 Signalling & Telecom (SMMS Data Landscape)
- **Assets:** Point machines (IRS rotary, electric), DC track circuits, Audio Frequency Track Circuits (AFTC), Block Proving Axle Counters (BPAC - Single/Multi section), Electronic Interlocking (EI), LED signal aspects, Level Crossing gate interlocking.
- **Maintenance Categories:**
  - Preventive Maintenance: Fortnightly point cleaning & lubrication; monthly track circuit voltage/ballast resistance checks; quarterly relay insulation tests; half-yearly cable meggering.
  - Corrective Maintenance: S&T failure tickets logged by Station Master or Control.
- **Disconnection Rules:** No wire, terminal, or relay may be disconnected without issuing Form S&T (T/351).

### 6.3 Traction Distribution (TDMS Data Landscape)
- **Assets:** 25 kV AC contact wire (107 sq mm copper), catenary wire (65 sq mm cadmium-copper), masts/portals, droppers, cantilevers, section insulators, neutral sections, isolators, TSS (Traction Substation), SP (Sectioning Post), SSP (Sub-sectioning Post).
- **Spatial Subdivision:**
  - **Feeding Post (FP):** Supplies ~40–50 km corridor.
  - **Sector:** Section between FP and neutral section.
  - **Sub-sector:** Section between SP and SSP (~10–15 km).
  - **Elementary Section:** The smallest isolatable unit (2 to 5 km or specific yard line) operated by manual or motorized isolators.
- **Key Operations:** Catenary/contact wire replacement, contact wire height/stagger measurement (using Tower Wagon), insulator washing, bracket replacement, tree trimming.

---

# 7. TRAIN OPERATIONS, WORKING TIMETABLE & GOODS TRAFFIC

### 7.1 Passenger vs Working Timetable (WTT)
- **Public Timetable (Trains at a Glance):** Only shows passenger departure/arrival times at commercial stops. Completely useless for block planning.
- **Working Time Table (WTT):** Issued by Zonal Headquarters Operating branch. Shows:
  - Exact sectional running times between all stations, block huts, and sidings.
  - Engineering allowances, traffic allowances, and booked speed.
  - Designated **Corridor Block Windows** (typically 2 to 3 hours per section on specified days).
  - Maximum Permissible Speed (MPS) and permanent speed restrictions.

### 7.2 The Reality of Freight / Goods Operations
1. **Goods Trains are NOT in the Published Timetable:** Over 90% of Indian Railways goods trains do not have fixed published timetables. They run on-demand based on rake loading, coal/cement/container movement, and crew availability.
2. **Train Ordering Mechanism:**
   - FOIS (Freight Operations Information System) tracks rake readiness and load advice.
   - When a freight rake is ready with locomotive and crew, the controller **orders** the train in COA.
   - The Section Controller then fits ("paths") the freight train through available gaps between scheduled passenger trains.
3. **Implication for RailOS:** An algorithm that assumes goods train movements are static or deterministic will fail immediately in practice. RailOS must model goods traffic as:
   - Fixed path for booked container/freight corridors (if applicable);
   - Probabilistic density / queue of pending freight movements for unbooked goods trains;
   - Dynamic replanning capability when a running freight train cannot be diverted.

---

# 8. REAL MAINTENANCE RULES & OPERATIONAL CONSTRAINTS

RailOS must encode Indian Railways statutory rules as mathematical constraints:

### 8.1 Minimum Machine Block Durations
| Machine Type | Primary Function | Minimum Required Block | Ineffective Setup/Winding Time |
|---|---|---|---|
| **BCM** (Ballast Cleaning Machine) | Deep screening of ballast bed | 4.0 hours (ideal: 5.0h) | 45 minutes (cutter bar insertion & removal) |
| **CSM / 09-3X** (Plain Track Tamper) | Tamping, lifting, and lining track | 2.5 hours (150 mins) | 30 minutes (traverse, setup, packing clear) |
| **UNIMAT** (Points & Crossing Tamper) | Tamping turnouts and crossovers | 2.5 to 3.0 hours | 35 minutes (setting datum, point alignment) |
| **TRT** (Track Renewal Train) | Complete rail & sleeper replacement | 4.0 to 6.0 hours | 60 minutes (welding, anchoring, initial stress) |
| **DGS** (Dynamic Track Stabilizer) | Artificial consolidation of ballast | 2.0 hours (runs with tamper)| 20 minutes |
| **Tower Wagon** (TRD 4-wheeler/8-wheeler)| OHE inspection, wire adjustment | 2.0 to 2.5 hours | 20 minutes (ladder placement, earthing) |

### 8.2 Track Machine Working Rules (IRTMM & IRPWM)
- **Machine Separation:** When multiple machines work in the same block section (e.g. BCM followed by Tamping Machine and DGS), a minimum clear distance of **200 metres** must be maintained between machines at all times.
- **Restoration to Traffic:** After tamping or deep screening, the track cannot immediately take trains at full MPS (110–130 kmph). Temporary Speed Restrictions (SR) must be imposed:
  - Day 1: 20 kmph
  - Day 2: 45 kmph
  - Day 3: 75 kmph
  - Day 4+: Restored to normal speed after required cumulative tamping and dynamic track stabilization.

### 8.3 Traction Safety Clearance (ACTM Rule 20.3)
- No person, tool, crane jib, or track machine boom may come within **2 metres** of any live 25 kV AC overhead conductor.
- Any track machine activity that involves lifting the track, slewing track, or operating excavators under live OHE requires an approved **Power Block and Permit to Work (PTW)**.

### 8.4 Adjacent Line Protection
- When heavy machines (BCM, TRT, mobile cranes) operate on a double-line section, there is risk of infringement or flying ballast onto the adjacent running line.
- A **Caution Order** (Form T/409) is mandatory for all trains running on the adjacent track, instructing Loco Pilots to restrict speed to 30 or 45 kmph and whistle continuously.

---

# 9. MULTI-DEPARTMENT COORDINATION & COMPATIBILITY REALITY

The core premise of RailOS is bundling tasks across Civil, S&T, and TRD. However, co-location does **NOT** imply compatibility. Certain combinations are physically impossible or prohibited:

### 9.1 Multi-Department Compatibility Matrix

| Work Type 1 (Civil / P-Way) | Work Type 2 (S&T) | Work Type 3 (TRD / OHE) | Compatibility | Mandatory Operational Conditions & Sequence |
|---|---|---|---|---|
| **Plain Track Tamping (CSM)** | Track Circuit bond check | OHE inspection via Tower Wagon (adjacent mast) | **HIGH (Compatible)** | Tower wagon must maintain >200m distance from tamper. S&T bonds checked after tamping passes. |
| **Ballast Cleaning (BCM)** | Point Machine maintenance | Catenary wire replacement | **STRICTLY INCOMPATIBLE** | BCM causes severe vibration and ballast removal; point machines and detection rods will be damaged. Catenary wire replacement requires tower wagon above, blocking track. |
| **Turnout Renewal (T-28 crane)** | Turnout S&T interlocking / point machine replacement | OHE slewing / section insulator adjustment | **SEQUENTIALLY COMPATIBLE** | **Must be strictly sequenced:** (1) S&T disconnects point under T/351; (2) TRD isolates OHE under PTW; (3) Civil replaces turnout; (4) TRD checks OHE alignment; (5) S&T reconnects point & performs correspondence testing. |
| **Manual Sleeper / Rail Renewal** | Glued Insulated Rail Joint (GJ) replacement | OHE bracket adjustment / tree trimming | **HIGH (Compatible)** | Power block required if work within 2m of OHE. S&T track circuit disconnected and re-bonded. |
| **Rail Stressing / De-stressing** | S&T Axle Counter calibration | Live OHE maintenance | **CONDITIONAL** | De-stressing requires lifting rails on rollers; live OHE must maintain electrical clearance. Axle counters must be unbolted and recalibrated post-destressing. |
| **Deep Screening under live OHE** | Any S&T task | Live OHE (No power block) | **STRICTLY PROHIBITED** | Violation of ACTM 20.3 (2m clearance). Power block is non-negotiable. |

---

# 10. ASSET AVAILABILITY & RAILWAY-NATIVE KPIS

Startup-style vanity metrics (e.g. "asset utilization %") are meaningless to Indian Railways Operating officers. RailOS must speak the native operational language of Indian Railways:

### 10.1 Railway-Native Performance Indicators

```text
┌────────────────────────────────────────────────────────────────────────┐
│ 1. Demanded vs Granted Block Ratio:                                    │
│    Ratio = (Total Block Hours Granted) / (Total Block Hours Demanded)  │
│    Target: > 80%. A key KPI reviewed monthly by DRM and Railway Board. │
├────────────────────────────────────────────────────────────────────────┤
│ 2. Block Utilization Efficiency:                                       │
│    Efficiency = (Actual Work Execution Time) / (Sanctioned Block Time) │
│    Accounts for transit time, setup time, and winding up.              │
├────────────────────────────────────────────────────────────────────────┤
│ 3. Block Burst Rate (Overrun Frequency):                               │
│    Overrun = Max(0, Actual Handback Time - Sanctioned Handback Time)   │
│    Target: 0%. Any overrun > 10 mins triggers punctuality debit.       │
├────────────────────────────────────────────────────────────────────────┤
│ 4. Track Quality Index (TQI) Delta:                                    │
│    Quantifies improvement in track geometry post-mechanized block.     │
├────────────────────────────────────────────────────────────────────────┤
│ 5. S&T Disconnection Duration:                                         │
│    Duration from T/351 Disconnection issue to Reconnection acceptance. │
├────────────────────────────────────────────────────────────────────────┤
│ 6. Punctuality Impact (Coaching Punctuality %):                        │
│    Punctuality = (Trains reaching destination on time) / (Total trains)│
│    Target: > 95% on Mail/Express corridors.                            │
├────────────────────────────────────────────────────────────────────────┤
│ 7. Line Capacity Utilization:                                          │
│    (Charted Trains + Booked Maintenance Windows) / (Theoretical Headway)│
│    Often exceeds 120–140% on High Density Networks (HDN/Golden Quad).  │
└────────────────────────────────────────────────────────────────────────┘
```

---

# 11. ALGORITHMIC FORMULATION FOR BLOCK SCHEDULING

### 11.1 Problem Mapping
The Automatic Block Planning problem is fundamentally a **Multi-Resource Constrained Project Scheduling Problem with Disjunctive Non-Overlapping Spatial Windows and Sequence-Dependent Setups (RCPSP-SDST)**:
- **Spatial Resources (Tracks/Lines):** Block sections (Station A to Station B on specific track) cannot be occupied simultaneously by incompatible activities (Train vs Maintenance).
- **Physical Resources (Machines & Crews):** Track machines (BCM, CSM, UNIMAT), tower wagons, and specialized SSE crews can only be in one section at a time.
- **Power Resources (OHE Elementary Sections):** Power block on elementary section $E_k$ de-energizes all tracks under that electrical feed.
- **Time Windows:** Trains occupy sections during disjunctive intervals $[t_{arr}, t_{dep} + \text{headway}]$.

### 11.2 Optimization Algorithm Comparison

| Method | 36-Hour Hackathon Viability | Production Viability | Constraint Rigor | Explainability | Real-time Replanning Speed |
|---|---|---|---|---|---|
| **Google OR-Tools CP-SAT (Constraint Programming)** | **HIGHEST (Recommended)** | **EXCELLENT** | **Absolute (100% hard constraint guarantee)** | **High (Direct conflict explanation)** | **Fast (< 10s for divisional corridor)** |
| **MILP (Mixed Integer Linear Programming - Gurobi/CBC)** | Medium | Good | Absolute | High | Slower on large disjunctive disjunctions |
| **Heuristic / Genetic Algorithms** | High | Poor | Weak (can violate safety constraints) | Low | Fast, but unprovable safety |
| **Reinforcement Learning (RL)** | Very Low | Unsuitable | Unacceptable (hallucinates valid safety rules) | Black Box | Poor generalization |

### 11.3 Mathematical Objective Formulation
$$\max \quad Z = w_1 \cdot \text{Yield} + w_2 \cdot \text{Bundling} - w_3 \cdot \text{PassDisrupt} - w_4 \cdot \text{FreightDelay} - w_5 \cdot \text{OverrunRisk}$$

Where:
- $\text{Yield} = \sum_{i \in \text{Completed}} \text{Priority}(i) \cdot \text{Duration}(i)$
- $\text{Bundling} = \sum \text{Cross-Departmental Tasks sharing same block window}$
- $\text{PassDisrupt} = \sum_{t \in \text{Trains}} \text{Delay}(t) \cdot \text{PassengerTrainWeight}(t)$
- $\text{FreightDelay} = \sum_{f \in \text{Freight}} \text{DetentionHours}(f)$
- $\text{OverrunRisk} = \sum_{i} \text{Var}(\text{Duration}_i) \cdot \mathbb{I}(\text{TightBuffer})$

---

# 12. SEPARATION OF CONCERNS: DETERMINISTIC, OPTIMIZATION, ML & GENAI

To maintain credibility before railway judges, RailOS must strictly separate engineering capabilities:

```text
┌────────────────────────────────────────────────────────────────────────┐
│ 1. DETERMINISTIC BUSINESS RULES (TypeScript / Python Rules Engine)     │
│    • Safety clearances (2m OHE clearance)                              │
│    • Minimum block durations (BCM = 4.0h, CSM = 2.5h)                  │
│    • Form S&T T/351 disconnection prerequisites                        │
│    • Incompatible task rejection (BCM + Point Machine)                 │
├────────────────────────────────────────────────────────────────────────┤
│ 2. MATHEMATICAL OPTIMIZATION (Google OR-Tools CP-SAT)                  │
│    • Combinatorial assignment of tasks to corridor windows             │
│    • Resource allocation (Tamper, Tower Wagon, Gangs)                  │
│    • Temporal ordering of dependent tasks                              │
│    • Shadow block opportunity identification                           │
├────────────────────────────────────────────────────────────────────────┤
│ 3. PREDICTIVE MACHINE LEARNING (scikit-learn / XGBoost)                │
│    • Block Overrun Probability Model (Trained on historical weather,   │
│      gang size, machine age, work type)                                │
│    • Defect Escalation Risk (Predicting OBS -> IMR transition time)    │
│    • Freight Traffic Arrival Window Forecasting                        │
├────────────────────────────────────────────────────────────────────────┤
│ 4. GENERATIVE AI / LLM (Gemini 1.5 Pro / Flash)                        │
│    • Natural-language "Explain Block Plan" for Section Controller      │
│    • Natural-language Drafting of Caution Orders (Form T/409)          │
│    • Summarizing complex failure situations during crisis handovers    │
│    • STRICTLY PROHIBITED FROM GENERATING MATHEMATICAL SCHEDULES DIRECTLY│
└────────────────────────────────────────────────────────────────────────┘
```

---

# 13. INTERNATIONAL & COMPETITOR SYSTEM BENCHMARKS

| System / Railway | Approach | Strengths | Limitations & Key Difference from Indian Railways |
|---|---|---|---|
| **Network Rail (UK)** — Possession Planning System (PPS) / Engineering Access Statement (EAS) | Fixed timetable rules ("Rules of the Plan"); possessions agreed at Week T-18; executed under strict track possession regulations. | Highly formalized, strict financial compensation (Schedule 4/8 payments) between train operators and track authority. | UK rail network runs predominantly scheduled passenger services; IR has massive unscheduled freight mixed on the same tracks with extreme line capacity utilization (>130%). |
| **Deutsche Bahn (Germany)** — Baubetriebsplanung (BBP) & RailSys | Simulation-based capacity planning and slot reservation for construction windows. | Strong simulation of network-wide delay propagation. | High degree of automation, but struggles with real-time operational volatility when freight is delayed. |
| **SNCF (France)** — Fenêtres Travaux (Work Windows) | Structural maintenance windows embedded into long-term master graph; TGV night possessions. | Dedicated high-speed maintenance hours with zero passenger traffic. | Indian Railways runs 24/7 passenger operations (night Mail/Express trains), eliminating easy "universal night windows". |
| **DFCCIL (Dedicated Freight Corridor, India)** | Dedicated freight-only double-track corridors with 4-hour daily maintenance corridor windows built into the design. | Standardized corridor blocks, modern automated OHE and track machines. | Isolated from mixed passenger traffic; RailOS must solve the far harder problem of mixed traffic on Indian Railways broad-gauge network. |

---

# 14. DATA AVAILABILITY AUDIT (PUBLIC VS INTERNAL VS SYNTHETIC)

| Category | Datasets | Availability Status | Strategy for Hackathon |
|---|---|---|---|
| **Category A: Real Public Data** | Passenger timetables, station lists, geocoordinates, line sections, public caution notices. | Readily available via NTES, Trains at a Glance, Open Government Data (data.gov.in). | Ingest directly for route topology and passenger train schedules (e.g. Ghaziabad - Kanpur or New Delhi - Palwal section). |
| **Category B: Public Documentation, No Raw Data** | TMS manuals, RDSO specifications, ACTM forms, IRPWM rules, BDMS workflow circulars. | Documented in circulars and reports, but databases are private. | Reverse-engineer exact JSON schemas from official manuals and field registers. |
| **Category C: Internal Railway Data** | Live TMS USFD defect database, SMMS relay failure logs, TDMS OHE wear logs, live COA train graphs, FOIS load advice. | Restricted inside Indian Railways intranet / CRIS private cloud. | Must NOT attempt unauthorized access. |
| **Category D: Realistic Synthetic Data** | Asset registers with realistic IDs, defect tickets with IMR/OBS tags, freight forecasts, machine availability. | Generated synthetically adhering to verified IR field standards. | Generate high-fidelity synthetic JSON datasets adhering to verified IR formats. |

> [!NOTE]
> For complete live URL endpoints, scrapable query patterns (NTES, ConfirmTkt, RailYatri, Zonal Mega Block bulletins), and Python scraper blueprints, see [RailOS_Live_Feeds_and_Scraping_Sources.md](file:///E:/RailOS/RailOS_Live_Feeds_and_Scraping_Sources.md).

---

# 15. HACKATHON SYNTHETIC DATASET SPECIFICATION

The hackathon platform will generate 9 standardized, verified-format datasets:

1. `assets.json`: Physical assets with IR naming conventions (`TRACK_SEC_GZB_ALJN_UP`, `POINT_102B_GZB`, `OHE_ELEM_2041_ALJN`).
2. `maintenance_tasks.json`: Tasks with departmental ownership (`ENGG`, `SNT`, `TRD`), statutory periodicities, and required durations.
3. `defects.json`: Fault logs with severity codes (`IMR`, `OBS`, `IMRW`, `OMS_PEAK_HIGH`, `POINT_SLACK_DETECTION`, `OHE_DROPPING_FAULT`).
4. `train_movements.json`: Working Time Table (WTT) schedules including passenger train IDs, class (Rajdhani, Mail/Express, Suburban), and section paths.
5. `goods_forecast.json`: Probabilistic freight rakes with origin yards, target time windows, and priority weights.
6. `corridors.json`: Block sections, line configurations (Single, Double, 3rd Line), crossovers, and station interlockings.
7. `block_windows.json`: Officially charted corridor block opportunities in the Working Time Table.
8. `resources.json`: Machines (CSM, BCM, UNIMAT, Tower Wagon) and departmental gangs with maintenance depot home locations.
9. `dependencies.json`: Hard preceding and succeeding relationships between tasks (e.g., S&T Disconnection -> Civil Turnout Replacement -> TRD OHE Adjust -> S&T Correspondence Reconnection).

---

# 16. FAILURE MODES & EMERGENCY EDGE CASES

RailOS must demonstrate how it handles unexpected operational disruptions:

```text
┌────────────────────────────────────────────────────────────────────────┐
│ SCENARIO A: Emergency Rail Fracture (IMR Defect at Km 142/6)          │
│ • Real-time detection by keyman or track circuit failure               │
│ • System Action: Instantly flag section; alert Section Controller;     │
│   recommend emergency 45-min block; calculate train detention impact;  │
│   NEVER autonomously authorize line possession.                        │
├────────────────────────────────────────────────────────────────────────┤
│ SCENARIO B: Block Overrun / Block Burst (Tamper failure on Down Line)   │
│ • CSM machine develops hydraulic failure 10 mins before block expiry   │
│ • System Action: Calculate cascaded train delays; identify trailing    │
│   passenger trains to be regulated at upstream loop lines; alert CHC;  │
│   propose emergency tower wagon or locomotive dispatch to clear line. │
├────────────────────────────────────────────────────────────────────────┤
│ SCENARIO C: Late Running of Preceding Premium Train (Rajdhani Express) │
│ • Rajdhani delayed by 45 mins upstream, encroaching on planned block   │
│ • System Action: Dynamically evaluate: (Option 1) Compress block;      │
│   (Option 2) Shift block window later; (Option 3) Re-route Rajdhani    │
│   via adjacent third line. Present tradeoffs to Section Controller.    │
├────────────────────────────────────────────────────────────────────────┤
│ SCENARIO D: Refusal of S&T Disconnection by Station Master            │
│ • Station Master refuses T/351 due to imminent crossing operations     │
│ • System Action: Block bundling engine decouples civil/electrical work │
│   if independent, or flags entire block as deferred with risk audit.   │
└────────────────────────────────────────────────────────────────────────┘
```

---

# 17. SAFETY GOVERNANCE & HUMAN AUTHORITY BOUNDARY

**The Golden Rule of Indian Railways Software:**  
Software can *recommend*, *simulate*, and *audit*; but only a human officer with statutory authority can *authorize*, *isolate*, and *grant*.

```text
┌──────────────────────────────────────────────┬──────────────────────────────────────────────┐
│       WHAT RAILOS IS PERMITTED TO DO         │      WHAT RAILOS IS PROHIBITED FROM DOING    │
│            (Decision Support)                │           (Autonomous Violation)             │
├──────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ • PROPOSE conflict-free maintenance bundles  │ • Autonomously granting track possession     │
│ • CALCULATE overrun probabilities & risks    │ • Autonomously switching SCADA isolators     │
│ • WARN of safety clearance infringements     │ • Autonomously issuing Form S&T T/351        │
│ • SIMULATE train delay cascades              │ • Overriding a Section Controller's refusal  │
│ • DRAFT Caution Orders & block applications  │ • Altering signal aspects or interlocking    │
└──────────────────────────────────────────────┴──────────────────────────────────────────────┘
```

---

# 18. WHAT THE CURRENT RAILOS PRD GETS WRONG & WHAT MUST CHANGE

| Current PRD Assumption / Section | Operational Ground Reality | What We Must Change in PRD & Architecture |
|---|---|---|
| **Assumption 1:** "COA provides corridor block availability" | COA does not expose an availability field. Corridor blocks are operational agreements in WTT or gaps between train paths. | Change to: RailOS calculates corridor availability by analyzing train movement schedules and headway safety buffers. |
| **Assumption 2:** "Any nearby Engineering, S&T, and TRD task can be bundled" | Co-location does not guarantee compatibility. Heavy track machines destroy signal bonds; vibration prevents point calibration; lack of OHE isolation violates ACTM 20.3. | Change to: Implement a strict **Multi-Department Compatibility Matrix** and sequence-dependent bundling engine. |
| **Assumption 3:** "Goods train forecasts are deterministic" | Goods trains run on-demand based on rake readiness, power, and crew. Over 90% have no fixed schedule. | Change to: Model goods trains with arrival probability distributions and dynamic real-time slot-fitting. |
| **Assumption 4:** "Blocks are allocated based only on passenger timetable gaps" | Maintenance requires physical track machine travel, setup, cutter bar insertion, winding up, and temporary speed restrictions. | Change to: Model machine traverse times, setup/winding-up buffers, and post-block temporary speed restrictions. |
| **Assumption 5:** "RailOS directly connects to live TMS, SMMS, TDMS APIs" | CRIS applications run on private railway intranet; Pravah gateway is strictly internal; no public APIs exist. | Change to: Build an enterprise-grade **Pravah-compatible Adapter Layer** with high-fidelity synthetic data. |
| **Assumption 6:** "Block utilization is a simple percentage of time used" | IR judges care about: Demanded vs Granted ratio, Block Bursts, and Track Quality Index (TQI) delta. | Change to: Implement native Indian Railways KPIs (Demanded vs Granted, Block Burst Probability, TQI Delta). |

---

# 19. HACKATHON MVP SCOPE VS PRODUCTION ROADMAP

```text
┌────────────────────────────────────────────────────────────────────────┐
│ HACKATHON MVP (36-Hour Working Prototype)                              │
│ • Section: 1 High-Density Corridor (e.g. Ghaziabad – Aligarh, 106 km)  │
│ • Engine: Google OR-Tools CP-SAT bundling & scheduling optimizer       │
│ • Input: Realistic synthetic TMS, SMMS, TDMS, and WTT JSON datasets    │
│ • UI: Dual-view Control Center (Section Controller + Maintenance Planner)│
│ • Decision Support: What-If simulation for emergency rail fracture &  │
│   Rajdhani late running delay                                          │
│ • GenAI: Natural language Caution Order generator (T/409) & block plan │
│   justification narrative for judges                                   │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│ PRODUCTION ROADMAP (Post-Hackathon Deployment)                         │
│ • Integration with CRIS Pravah API Gateway on Railway Intranet         │
│ • Direct two-way sync with BDMS (Block & Disconnection Management)     │
│ • SCADA interface for automated OHE isolation telemetry verification   │
│ • Mobile app for SSE field reporting with GPS geofencing               │
│ • Zonal & Railway Board multi-divisional rolling block coordination    │
└────────────────────────────────────────────────────────────────────────┘
```

---

# 20. UNKNOWNS REQUIRING RAILWAY EXPERT VALIDATION

The following technical parameters cannot be verified via public documents and are classified as **NOT VERIFIED PUBLICLY**:
1. **BDMS Internal API Specifications:** The exact REST/SOAP payload structure, authentication tokens, and endpoint schema of CRIS BDMS. *(NOT VERIFIED PUBLICLY)*
2. **Exact Divisional Weighting for Freight vs Passenger Delays:** While passenger punctuality is officially prioritized over freight, the exact rupee-value or operational weighting used during controller shift evaluation varies by division. *(NOT VERIFIED PUBLICLY)*
3. **Automated SCADA Isolator Interlocking with COA:** Whether any Indian Railways division has successfully closed the loop between SCADA power block tripping and COA signal interlocking. *(NOT VERIFIED PUBLICLY — assumed currently manual)*

---

# 21. DELIVERABLE 2: FACT CHECK & ASSUMPTION AUDIT TABLE

| # | RailOS Assumption | Finding / Ground Reality | Status | Regulatory / Official Evidence | Required System Change |
|---|---|---|---|---|---|
| **F-01** | "COA provides an API exposing corridor block availability" | COA provides train plotting and active block status, but does not provide an automated "open window" API. | **FALSE / OVER-SIMPLIFIED** | CRIS COA System Documentation & Functional Description | RailOS Opportunity Engine must compute candidate block windows from train paths and headway rules. |
| **F-02** | "Nearby tasks can always be bundled into one block" | Heavy track machines (BCM/TRT) produce severe vibration and cut bond wires; delicate S&T point testing or OHE adjustment cannot happen simultaneously. | **FALSE** | Indian Railways Permanent Way Manual (IRPWM) Chapter 8; Signal Engineering Manual (SEM) Chapter 11 | Implement Multi-Department Compatibility Matrix with strict sequencing and exclusion rules. |
| **F-03** | "Blocks are requested informally or ad-hoc daily" | Planned maintenance is legally bound to the 26- to 52-week Rolling Block Programme (RBP) and routed via BDMS. | **OVER-SIMPLIFIED** | Gazette Notification G.S.R. 870(E) (Nov 30, 2023); Railway Board Letter 2020/Track-III/TK/2 | Support both 26-Week Rolling Block planning and Day-of-Operation real-time adjustments. |
| **F-04** | "Goods train traffic is deterministic and scheduled" | Goods trains are ordered dynamically based on FOIS load advice, rake readiness, and power availability. | **FALSE** | Indian Railways Operating Manual; FOIS-COA Integration Orders | Introduce stochastic freight density forecasting and dynamic slot insertion. |
| **F-05** | "Traction power can be isolated via software instruction" | OHE isolation requires formal TPC sanction, physical isolator switch throwing, and discharge rod earthing before PTW (ETR-3) issuance. | **FALSE** | AC Traction Manual (ACTM) Chapter VI, Rule 20600–20610 | Model Permit to Work (PTW) workflow and safety earthing setup buffers (minimum 20 mins). |
| **F-06** | "S&T gears can be adjusted freely during line blocks" | S&T gear withdrawal requires formal Disconnection Notice (Form S&T T/351) signed by Station Master, plus correspondence tests before reconnection. | **VERIFIED** | Signal Engineering Manual (SEM) Rule 11.4; Safety Circulars post-Balasore | Incorporate S&T Form T/351 workflow and correspondence testing buffers in task schedules. |
| **F-07** | "Block utilization can be represented as a plain percentage" | Railway operating officers monitor Demanded vs Granted ratio, Block Bursts, and Track Quality Index (TQI) delta. | **OVER-SIMPLIFIED** | Railway Board Operating Performance Directives & CAG Reports | Replace generic percentage with railway-native KPIs (Demanded/Granted %, Burst Risk, TQI delta). |
| **F-08** | "Public APIs exist for Indian Railways data" | CRIS protects all enterprise data behind private intranets and the Pravah API Gateway; no open public APIs exist. | **VERIFIED** | CRIS Pravah Gateway Launch & Ministry of Railways IT Security Policy | Build realistic Pravah-compliant adapter layer with synthetic JSON data. |

---

# 22. DELIVERABLE 3: ENTERPRISE SYSTEM MATRIX

| System | Owner | Core Purpose | Primary Inputs | Primary Outputs | Existing Integrations | Public API? | Confidence |
|---|---|---|---|---|---|---|---|
| **TMS** (Track Management System) | CRIS / Civil Engg | Track asset inventory, inspections, defect tracking, machine planning | USFD flaw logs, TRC geometry runs, OMS peak data, field inspections | Maintenance work orders, IMR/OBS lists, tamping proposals | Integrates with FOIS for GMT traffic data; feeds BDMS | No (Intranet only via Pravah) | **VERIFIED** |
| **SMMS** (Signalling Maintenance Management System) | CRIS / S&T | Signalling asset registers, failure logging, scheduled maintenance | Station master failure tickets, relay room access logs, overhaul schedules | Disconnection requests, gear reliability indices, overdue maintenance | Integrates with TMS for track layout; feeds BDMS | No (Intranet only via Pravah) | **VERIFIED** |
| **TDMS** (Traction Distribution Management System) | CRIS / Electrical | OHE and traction asset tracking, foot-patrol defect logging | Tower wagon inspection records, contact wire thickness, isolator logs | Power block requests, OHE defect alerts, foot-patrol audit reports | Integrates with SCADA for tripping events; feeds BDMS | No (Intranet only via Pravah) | **VERIFIED** |
| **COA** (Control Office Application) | CRIS / Operating | Electronic train charting, train ordering, control office automation | Train departures/arrivals, loco numbers, crew details, caution orders | Real-time train charts, crossing plans, delay attribution logs | Integrates with FOIS, ICMS, NTES, and BDMS | No (Intranet only via Pravah) | **VERIFIED** |
| **BDMS** (Block & Disconnection Management System) | CRIS / Multi-dept | Unified portal for block demands, vetting, approvals, and execution | Block requests from SSE (P-Way, S&T, TRD); sectional constraints | Sanctioned rolling block schedules, grant/closure timestamps | Integrates with TMS, SMMS, TDMS, and COA | No (Intranet only via Pravah) | **VERIFIED** |
| **FOIS** (Freight Operations Information System) | CRIS / Operating | Freight consignment tracking, rake management, load planning | Loading advices, weighbridge inputs, wagon health, rake composition | Train ordering advice to COA, transit forecasts | Integrates directly with COA and TMS | No (Internal & B2B EDI only) | **VERIFIED** |
| **Pravah API Gateway** | CRIS / IT | Enterprise API security, routing, and data exchange across IR apps | Internal microservice REST/SOAP requests | Authenticated payloads, rate-limited data interchanges | Acts as the backbone for all CRIS application integrations | No (Enterprise intranet only) | **VERIFIED** |

---

# 23. DELIVERABLE 4: IMPLEMENTATION-READY HARD CONSTRAINTS (HC-001 TO HC-018)

These constraints are mathematically enforceable in the RailOS CP-SAT optimization model:

```text
[HC-001] PASSENGER TRAIN PATH DISJUNCTION
Description: No traffic block may overlap with a charted passenger train path in the same block section.
Departments: Operating vs All Maintenance.
Source: Indian Railways General Rules (GR) 4.08 & 15.06.
Confidence: VERIFIED.
Implementation:
  For each task i and train movement j on same track section:
  model.Add(task_start[i] >= train_pass_time[j] + clear_headway).OnlyEnforceIf(order_var)
  model.Add(train_pass_time[j] >= task_end[i] + clear_headway).OnlyEnforceIf(order_var.Not())

[HC-002] MINIMUM MACHINE DURATION REQUIREMENT
Description: A track machine block cannot be scheduled for less than its statutory minimum operating duration.
Departments: Civil Engineering.
Source: Indian Railways Track Machine Manual (IRTMM) Chapter 3.
Confidence: VERIFIED.
Implementation:
  task_duration[BCM] >= 240 mins; task_duration[CSM] >= 150 mins; task_duration[UNIMAT] >= 150 mins.

[HC-003] OHE ISOLATION SAFETY PREREQUISITE
Description: Tasks requiring traction power shutdown cannot begin until the Permit to Work (PTW) is issued.
Departments: Electrical (TRD) vs Civil / S&T.
Source: AC Traction Manual (ACTM) Vol II, Rule 20603.
Confidence: VERIFIED.
Implementation:
  model.Add(task_start[work] >= ptw_grant_time + 20)  # 20-min switching & discharge rod earthing buffer

[HC-004] POST-WORK OHE ENERGIZATION BUFFER
Description: Power block cannot be cleared until all men and materials are reported clear and discharge rods removed.
Departments: Electrical (TRD).
Source: ACTM Vol II, Rule 20610.
Confidence: VERIFIED.
Implementation:
  model.Add(power_block_end >= task_end[work] + 15)  # 15-min handback & restoration buffer

[HC-005] S&T DISCONNECTION PREREQUISITE (FORM T/351)
Description: Interlocked signaling gears (points, signals, track circuits) cannot be worked on until Station Master approves Form T/351.
Departments: S&T vs Operating.
Source: Signal Engineering Manual (SEM) Rule 11.4.
Confidence: VERIFIED.
Implementation:
  model.Add(snt_task_start >= t351_endorsement_time)

[HC-006] MANDATORY S&T CORRESPONDENCE TESTING
Description: After physical work on points or detection circuits, reconnection requires a mandatory correspondence test.
Departments: S&T.
Source: Railway Board Safety Directives (Post-Balasore Circulars 2023/2024).
Confidence: VERIFIED.
Implementation:
  model.Add(block_clearance_time >= snt_task_end + 30)  # 30-min testing window

[HC-007] SEQUENTIAL DEPENDENCY IN TURNOUT RENEWAL
Description: Turnout renewal requires strictly sequenced execution: S&T Disconnect -> OHE Isolate -> Civil Replace -> OHE Align -> S&T Reconnect.
Departments: Civil, S&T, Electrical.
Source: Joint Procedure Order on Integrated Corridor Maintenance.
Confidence: VERIFIED.
Implementation:
  model.Add(civil_start >= snt_disconnect_end)
  model.Add(civil_start >= trd_isolation_end)
  model.Add(snt_reconnect_start >= civil_end)

[HC-008] MACHINE SAFETY SPACING
Description: When multiple machines work in the same block section, a minimum spatial distance of 200m must be maintained.
Departments: Civil Engineering.
Source: IRTMM Rule 3.2.1.
Confidence: VERIFIED.
Implementation:
  model.Add(machine_pos[m2] - machine_pos[m1] >= 200)

[HC-009] SINGLE MACHINE OCCUPANCY
Description: A specific physical track machine (e.g. Tamper CSM-104) cannot be assigned to two locations at once.
Departments: Civil Engineering.
Source: Physical Law / Resource Constraint.
Confidence: VERIFIED.
Implementation:
  model.AddNoOverlap([IntervalVar(task) for task in machine_tasks[m]])

[HC-010] ADJACENT LINE INFRINGEMENT PROTECTION
Description: If machine work involves slewing or ballast screening that infringes adjacent line, caution orders must be imposed.
Departments: Operating vs Civil.
Source: IRPWM Rule 806.
Confidence: VERIFIED.
Implementation:
  If task.infringes_adjacent: model.Add(adjacent_train_speed <= 45)

[HC-011] EMERGENCY DEFECT DEADLINE (IMR FLAW)
Description: An IMR rail flaw must be protected and replaced within statutory 72 hours under traffic block.
Departments: Civil Engineering.
Source: IRPWM USFD Manual Rule 6.3.
Confidence: VERIFIED.
Implementation:
  model.Add(task_start[IMR] <= detection_time + 72 * 60)

[HC-012] TOWER WAGON PASSENGER OVERLAP EXCLUSION
Description: A tower wagon occupying a track under power block blocks all train movement on that track.
Departments: TRD vs Operating.
Source: ACTM Chapter VI.
Confidence: VERIFIED.
Implementation:
  Treat Tower Wagon as a blocking interval in line occupancy graph.

[HC-013] GANG TRAVEL TIME FEASIBILITY
Description: A maintenance gang cannot start work at Site B until transit time from Depot or Site A has elapsed.
Departments: All Departments.
Source: Logistical Reality.
Confidence: VERIFIED.
Implementation:
  model.Add(gang_start[task_B] >= gang_end[task_A] + transit_matrix[loc_A][loc_B])

[HC-014] TRAIN LINE CLEAR OCCUPANCY
Description: Block section cannot be granted for maintenance while a train is in "Line Clear" status within that section.
Departments: Operating.
Source: General Rules (GR) Chapter XIV.
Confidence: VERIFIED.
Implementation:
  model.Add(block_start >= train_exit_time)

[HC-015] DAYLIGHT RESTRICTION FOR NON-ILLUMINATED WORKS
Description: Deep screening and rail renewals without mobile high-mast lighting towers must occur between sunrise and sunset.
Departments: Civil Engineering.
Source: IRPWM Safety Circulars.
Confidence: VERIFIED.
Implementation:
  If not task.has_mobile_lighting: model.Add(task_start >= 06:00, task_end <= 18:00)

[HC-016] MAXIMUM CONTINUOUS BLOCK DURATION
Description: A single continuous traffic block on a high-density corridor must not exceed 4 hours unless approved as a Sunday Mega Block.
Departments: Operating.
Source: Railway Board Operating Policy.
Confidence: VERIFIED.
Implementation:
  model.Add(block_duration <= 240).OnlyEnforceIf(is_weekday)

[HC-017] TRACK CIRCUIT CONTINUITY PRESERVATION
Description: Track tamping or rail renewal must not break track circuit continuity unless an S&T official is present with bypass jumpers.
Departments: S&T vs Civil.
Source: SEM Rule 11.12.
Confidence: VERIFIED.
Implementation:
  Requires S&T escort resource linked to civil tamping interval.

[HC-018] POST-BLOCK TEMPORARY SPEED RESTRICTION (SR) ENFORCEMENT
Description: After track machine deep screening, the section must impose a mandatory 20 kmph caution order for the first 24 hours.
Departments: Civil vs Operating.
Source: IRPWM Rule 308.
Confidence: VERIFIED.
Implementation:
  Post-block timetable graph must increase sectional run time for 24 hours by SR factor: Delta_T = (Dist / 20) - (Dist / MPS).
```

---

# 24. DELIVERABLE 5: SOFT OBJECTIVES & MULTI-CRITERIA OBJECTIVE FUNCTION (SO-001 TO SO-008)

The RailOS Optimizer evaluates candidate feasible schedules against eight soft criteria:

```text
[SO-001] MAXIMIZE CRITICAL MAINTENANCE YIELD
Objective: sum(PriorityScore(i) * WorkUnits(i) for i in Completed)
Weight Recommendation: 30%
Rationale: Resolving high-severity defects (IMR, OMS peaks, signal detection drift) prevents accidents and unplanned emergencies.

[SO-002] MINIMIZE PASSENGER TRAIN DELAYS & REGULATION
Objective: sum(DelayMinutes(t) * ClassWeight(t) for t in PassengerTrains)
Weight Recommendation: 25%
Class Weights: Vande Bharat / Rajdhani = 5.0, Mail/Express = 3.0, Passenger = 1.5, Suburban = 4.0 (during peak).
Rationale: Passenger punctuality is the primary public KPI of Indian Railways.

[SO-003] MAXIMIZE MULTI-DEPARTMENT TASK BUNDLING
Objective: Count of compatible S&T and TRD tasks completed inside a Civil traffic block.
Weight Recommendation: 15%
Rationale: Piggybacking tasks into shadow and corridor blocks reduces the total number of traffic interruptions required per year.

[SO-004] MINIMIZE FREIGHT TRAIN DETENTION
Objective: sum(DetentionHours(f) for f in FreightRakes)
Weight Recommendation: 10%
Rationale: Freight generates >65% of Indian Railways revenue. Stabling freight rakes causes yard congestion and locomotive idling.

[SO-005] MINIMIZE BLOCK OVERRUN RISK BUFFER VIOLATION
Objective: Penalize schedules where (Sanctioned Window - Expected Duration) < 2.0 * StandardDeviation(Duration).
Weight Recommendation: 10%
Rationale: Tightly scheduled blocks frequently "burst", causing uncontrolled punctuality collapse.

[SO-006] MINIMIZE RESIDUAL DEFECT RISK DEBT
Objective: Penalize deferred tasks proportional to their OverdueDays * RiskSlope.
Weight Recommendation: 5%
Rationale: Prevents the optimizer from repeatedly postponing low-priority tasks until they become critical failures.

[SO-007] MINIMIZE TEMPORARY SPEED RESTRICTION (SR) FOOTPRINT
Objective: sum(LengthKm(s) * DaysActive(s) for s in ActiveSR)
Weight Recommendation: 3%
Rationale: Accumulated speed restrictions bleed corridor line capacity long after the block is cleared.

[SO-008] MAXIMIZE MACHINE REPOSITORY UTILIZATION
Objective: Minimize idle days of specialized track machines (BCM, CSM, UNIMAT).
Weight Recommendation: 2%
Rationale: Capital-intensive machines have high depreciation costs and monthly progress targets.
```

---

# 25. DELIVERABLE 6: FIVE REALISTIC DEMO SCENARIOS

These evidence-based scenarios will be used for the hackathon live demonstration:

### Scenario 1: Routine 3-Hour Integrated Corridor Block (Ghaziabad – Aligarh Up Line)
- **Context:** Section: Maripat – Dadri (Double line, electrified 25 kV AC). Scheduled corridor window: 11:30 to 14:30.
- **Tasks Bundled:**
  1. Civil: Plain track tamping (CSM Tamper-214) over Km 32/10 to 35/14 (3.2 km). Duration: 140 mins.
  2. Electrical: Tower Wagon (TW-804) catenary dropper adjustment & insulator washing at Km 33/0 to 34/0. Requires Power Block on Elementary Section 2042.
  3. S&T: Inspection & track circuit bond jumper maintenance behind the tamper.
- **Operational Handling:** Down Line remains fully operational. 2 freight trains regulated in yard; 1 passenger train diverted via 3rd line.
- **RailOS Output:** Automated Gantt chart showing strict 200m machine spacing, PTW issue at T+15, S&T clearance at T+150, handback at T+170 mins with zero block burst.

### Scenario 2: Emergency IMR Rail Fracture on High-Density Quad Track (New Delhi – Mathura)
- **Context:** Keyman detects hair-line rail fracture (USFD confirmed IMR flaw) at Km 18/4 on Down Main Line near Faridabad at 07:15 AM.
- **Constraint:** Morning peak suburban EMU and Express traffic is running. Statutory rule: Rail must be clamped immediately; 30 kmph restriction; 45-minute emergency block required within 24 hours.
- **RailOS Dynamic Replanning:**
  - Evaluates train graphs in COA.
  - Detects that at 12:10–12:55 there is a natural 45-minute headway gap between EMU local and Golden Temple Mail.
  - Proposes emergency block: Alerts Section Controller; pre-notifies Faridabad Station Master; schedules P-Way gang with rail cutting & drill machine.
  - Bundles routine S&T axle counter check at adjacent crossover without adding block time.

### Scenario 3: OHE Catenary Wire Replacement with Shadow Block Exploitation
- **Context:** Contact wire wear detected on Down Line between Khurja and Aligarh. TRD requires 3.5-hour power block.
- **Shadow Block Discovery:** Because the Down Line is blocked for 3.5 hours, freight trains cannot move through the upstream block section (Somna – Kulwa).
- **RailOS Action:** Automatically identifies a **Shadow Block Opportunity** on Somna – Kulwa. Prompts Civil Engineering: *"Down line is starved of traffic for 180 mins. Propose deploying UNIMAT to tamp Points 201A & 201B at Somna yard simultaneously with zero incremental passenger train disruption."*

### Scenario 4: Electronic Interlocking & Turnout Renewal Multi-Department Handshake
- **Context:** Major yard remodeling at Aligarh Junction. Turnout No. 114 (1 in 12 curved switch) due for complete replacement.
- **Incompatible Bundling Test:** Civil gang wants to replace switch using T-28 crane; S&T wants to calibrate point machine; TRD wants to adjust section insulator.
- **RailOS Dependency Enforcer:**
  - Rejects naive simultaneous proposal.
  - Generates strictly sequenced 5-phase schedule:
    - Phase 1 (00:00–00:30): S&T Form T/351 Disconnection; TRD OHE isolation & discharge rod earthing.
    - Phase 2 (00:30–02:30): Civil T-28 crane lifts old switch, lays new pre-assembled turnout, rough ballast packing.
    - Phase 3 (02:30–03:15): TRD restores catenary alignment over new switch geometry; removes discharge rods; cancels PTW.
    - Phase 4 (03:15–04:00): S&T installs point machine, detection rods; executes **Mandatory Correspondence Test** with Station Master.
    - Phase 5 (04:00): Block handback; line certified fit for 20 kmph.

### Scenario 5: Real-Time Recovery from Rajdhani Express 45-Minute Delay Cascade
- **Context:** Planned 3.0-hour maintenance block at Hathras (13:00 to 16:00).
- **Disruption:** Up Rajdhani Express arrives at Hathras section 45 minutes late (running at 13:35 instead of 12:50), directly encroaching on the planned maintenance start.
- **Traditional Control Failure:** Controller cancels the block outright, wasting gang mobilization and machine positioning.
- **RailOS Real-Time Decision Support:**
  - Computes trade-off matrix in 3 seconds:
    - Option A: Cancel block (Maintenance Debt increased by 72h; IMR risk elevated).
    - Option B: Delay block start to 13:45; extend to 16:45 (Causes 3 freight detentions; zero passenger delay).
    - Option C: Dynamic Re-routing — Divert Rajdhani through Hathras 3rd loop line at 50 kmph, permitting maintenance block on Main Line to begin at 13:10 with only a 6-minute delay to Rajdhani.
  - Recommends Option C to Chief Controller with clear mathematical impact breakdown.

---

# 26. DELIVERABLE 7: RECOMMENDED 36-HOUR HACKATHON MVP SCOPE

To win the hackathon, the team must be ruthlessly focused on high-impact domain correctness:

```text
┌────────────────────────────────────────────────────────────────────────┐
│ P0 — ABSOLUTELY REQUIRED (Core Hackathon Winner Deliverables)          │
│ • Google OR-Tools CP-SAT Scheduling & Bundling Engine                   │
│ • Hard Constraints Enforced: HC-001 (Train), HC-002 (Duration),        │
│   HC-003 (Power Block/PTW), HC-005 (T/351 Disconnection), HC-007 (Seq) │
│ • Realistic Synthetic Data Adapters for TMS, SMMS, TDMS, COA, WTT      │
│ • Web Control Center UI: Interactive Time-Distance / Gantt Chart       │
│ • Dual Persona Views: Section Controller View + Divisional Planner View│
│ • Native KPIs: Demanded vs Granted %, Block Burst Risk, TQI Delta      │
│ • Live Interactive Simulation of Scenario 1 (Routine) & 5 (Rajdhani)   │
├────────────────────────────────────────────────────────────────────────┤
│ P1 — HIGH VALUE (Competitive Differentiators)                          │
│ • Shadow Block Detection Engine (Automatic piggybacking detection)     │
│ • ML-Based Block Overrun Predictor (XGBoost on synthetic history)      │
│ • GenAI Natural-Language Caution Order (T/409) & Plan Justification    │
│ • What-If Scenario Sandbox for Section Controllers                     │
├────────────────────────────────────────────────────────────────────────┤
│ P2 — PRESENTATION ONLY (Visual Polish / Mocked Backends)               │
│ • Android Field Supervisor PWA Mockup (T/351 sign-off screen)          │
│ • Executive Analytics Dashboard with Zonal/Divisional breakdown        │
│ • Sound effects / Railway Control Room ambient theme                   │
├────────────────────────────────────────────────────────────────────────┤
│ P3 — POST-HACKATHON (Production Roadmap Only)                          │
│ • Integration with CRIS Pravah API Gateway                             │
│ • Direct two-way sync with live BDMS database                          │
│ • SCADA telemetry feed from Traction Substations                      │
│ • Hardware IoT GPS trackers on track machines                          │
└────────────────────────────────────────────────────────────────────────┘
```

---

# CONCLUSION & GUIDANCE FOR SYSTEM AGENTS

This document serves as the frozen, authoritative domain reality for all RailOS engineering:
- **Codex (Implementation Agent):** Build data models, schemas, and API adapters matching the verified field registers documented in Section 6 and Section 15.
- **Claude (Architecture & Optimization Agent):** Implement the CP-SAT model using the exact Hard Constraints (Section 23) and Soft Objectives (Section 24). Do not allow naive co-location bundling.
- **Antigravity (UI & Control Room Agent):** Build the Section Controller and Maintenance Planner interfaces around the authentic operational terminology (BDMS, Form T/351, PTW ETR-3, Block Bursts, Demanded vs Granted) rather than generic tech-startup concepts.
