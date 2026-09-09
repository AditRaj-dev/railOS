# RailOS: Platform Architecture, Technology Stack & Business Logic Specification

> **Platform Directive:** *"RailOS proposes; an authorized railway officer decides."*  
> All scheduling, optimization, and bundling outputs serve as decision intelligence for authorized Indian Railways personnel (Operating, Civil Engineering, S&T, Electrical/TRD). Statutory safety rules are strictly inviolable.

---

## 1. Executive Summary & Problem Domain

### 1.1 The Operational Challenge in Indian Railways
Indian Railways operates one of the densest mixed-traffic rail networks in the world. On high-density trunk routes—such as the **Ghaziabad–Aligarh (GZB–ALJN) 106 km quadruple/double-track section of North Central Railway**—high-speed passenger trains (Rajdhani, Vande Bharat, Mail/Express), suburban commuter services, and heavy freight rakes compete for track occupancy 24/7.

Historically, infrastructure maintenance operates in departmental silos:
- **Civil / Permanent Way (ENGG):** Track tamping, deep screening, rail replacements, turnout renewals.
- **Signal & Telecommunication (SNT):** Point machine overhauls, track circuit maintenance, axle counter calibration.
- **Traction Distribution / Electrical (TRD):** 25 kV AC Overhead Equipment (OHE) bracket adjustments, catenary replacements, isolation checks.
- **Operating / Traffic (DOM / Section Controllers):** Punctuality, throughput, passenger path dispatching.

When departments submit uncoordinated block requests, the consequences are severe:
1. **Low Track Possession Utilization:** A 3-hour traffic block granted to Civil Engineering often leaves the OHE live or S&T uncoordinated, preventing simultaneous maintenance and requiring another disruptive block days later.
2. **Block Bursting & Overruns:** Maintenance exceeding sanctioned possession windows causes cascading passenger train detentions, caution order backlogs, and severe network delay.
3. **Safety Risks & Rulebook Violations:** Relaxing safety lead-in buffers (e.g., failing to isolate OHE per ACTM or skipping S&T Form T/351 disconnection / correspondence testing per SEM) risks fatal electrocution, derailments, or false signal indications.

### 1.2 The RailOS Solution
**RailOS** is an end-to-end Railway Maintenance Planning & Operational Intelligence Platform. It aggregates defect logs, asset registers, timetable graphs, and resource availability into a unified canonical model, identifies traffic-free windows, clusters cross-department work into safe bundles, and solves a multi-objective constraint program (CP-SAT) under strict Indian Railways statutory rules. Once approved by a multi-department sanction chain, RailOS governs the physical possession lifecycle in real time across desk controllers and field engineers.

---

## 2. Full Technology Stack

The RailOS platform is architected as a modular, high-reliability system consisting of an optimization core, a resilient async backend API, a real-time web operational command center, and an offline-first mobile field application.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             CLIENT LAYER                                    │
│                                                                             │
│   ┌──────────────────────────────────┐  ┌───────────────────────────────┐   │
│   │    Web Control Center            │  │     Mobile Field App          │   │
│   │    (Next.js 15 App Router,       │  │     (Flutter 3.x, Dart,       │   │
│   │     TypeScript, Tailwind CSS,    │  │      Offline SQLite Cache,    │   │
│   │     Leaflet & OpenRailwayMap,    │  │      GPS Geofencing Camera,   │   │
│   │     Zustand, Lucide React)       │  │      Material 3 Dark UI)      │   │
│   └─────────────────┬────────────────┘  └───────────────┬───────────────┘   │
└─────────────────────┼───────────────────────────────────┼───────────────────┘
                      │ HTTP / WebSocket                  │ HTTP / Media Upload
                      ▼                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            API & SERVICE LAYER                              │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  FastAPI (Python 3.11+, ASGI Uvicorn)                                │   │
│   │  • Strict Pydantic v2 Canonical Schemas & DTO Validation            │   │
│   │  • Dual Auth: Synthetic Role Headers & Argon2id + JWT Tokens        │   │
│   │  • Pub/Sub In-Memory Event Bus & WebSocket Broadcasts               │   │
│   │  • Multi-Stage Possession State Machine (T/351, PTW, Handback)       │   │
│   │  • Field Evidence Verification & Tamper-Proof EXIF Geofencing       │   │
│   └──────────────────────────────────┬──────────────────────────────────┘   │
└──────────────────────────────────────┼──────────────────────────────────────┘
                                       │ Python Native IPC / Direct Calls
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CORE INTELLIGENCE ENGINES                            │
│                                                                             │
│   ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐   │
│   │  Risk &       │ │  Opportunity  │ │  Bundling     │ │  OR-Tools     │   │
│   │  Priority     │ │  Engine       │ │  Engine       │ │  CP-SAT       │   │
│   │  Engine       │ │  (Headways &  │ │  (Spatial-    │ │  Optimizer    │   │
│   │  (Heuristics  │ │   Shadow      │ │   Temporal    │ │  (HC-001..018 │   │
│   │   & Curves)   │ │   Windows)    │ │   Matrix)     │ │   Audit Pass) │   │
│   └───────┬───────┘ └───────┬───────┘ └───────┬───────┘ └───────┬───────┘   │
│           │                 │                 │                 │           │
│   ┌───────┴─────────────────┴─────────────────┴─────────────────┴───────┐   │
│   │  Simulator Engine & Dynamic Train Graph Feedback (NetworkX)         │   │
│   └──────────────────────────────────┬──────────────────────────────────┘   │
└──────────────────────────────────────┼──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       PERSISTENCE & STORAGE LAYER                           │
│                                                                             │
│   ┌──────────────────────────────────┐  ┌───────────────────────────────┐   │
│   │  PostgreSQL 16 (Neon Serverless) │  │  Object Storage (S3 / R2)     │   │
│   │  • JSONB Snapshot State Table    │  │  • Tamper-proof site photos   │   │
│   │  • Transactional Atomicity       │  │  • Continuous walkthrough     │   │
│   │  • In-Memory Deterministic Mock  │  │    video evidence             │   │
│   └──────────────────────────────────┘  └───────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Backend & Intelligence Core
- **Language & Runtime:** Python 3.11+ managed with high-speed `uv` packaging.
- **Web Framework:** **FastAPI** (asynchronous ASGI execution on `uvicorn`), leveraging Pydantic v2 for request/response serialization with strict camelCase/snake_case boundary enforcement.
- **Mathematical Optimization Engine:** **Google OR-Tools CP-SAT (Constraint Programming - Satisfiability)**. Handles the NP-hard Resource-Constrained Project Scheduling Problem with Spatial Disjunctions and Sequence-Dependent Setups (RCPSP-SDST).
- **Network & Conflict Modeling:** **NetworkX** for corridor topology modeling, station block section pathing, and calculating train running delays caused by Caution Orders (Form T/409) and Temporary Speed Restrictions (TSR).
- **Domain Modeling & Schema Validation:** **Pydantic v2**. Exports JSON Schemas into `schemas/` ensuring zero contract drift across services.
- **Testing & Property Verification:** **Pytest** with 70+ deterministic tests, parameterised invariant tests, and property-based disjunction checks.

### 2.2 Frontend (Web Control Center)
- **Framework:** **Next.js 15+ (App Router)** with React 19 and strict TypeScript 5+.
- **Styling & Design Tokens:** **Tailwind CSS** coupled with the custom **RailOS Design System (`railos_tokens.css`)**:
  - High-contrast, dark-mode railway operations theme (`#0c121e` surface, `#161f30` panel).
  - Indian Railways operational color codings: Green (Clear / Normal), Amber (Caution / Under Review), High-visibility Red (Danger / Disconnection / Block Burst), Electric Yellow (Traction / Live OHE).
- **Interactive Geospatial Visualizations:**
  - **Leaflet & React-Leaflet** rendering interactive multi-track overlays.
  - Integration with **OpenRailwayMap** vector/raster tiles and custom Indian Railways corridor GeoJSON files representing track geometries, signals, turnouts, elementary sections, and stations.
- **State Management & Networking:**
  - **Zustand** stores for real-time corridor, possession, and alert states.
  - Native browser **WebSockets** for sub-second synchronization with the backend event bus.
- **Component & UI Libraries:** **Lucide React** for railway and engineering icons, custom responsive Gantt charts, and SVG track schematics.

### 2.3 Mobile Field Application
- **Framework:** **Flutter 3.x (Dart 3)** targeting Android (tablets and handheld ruggedized devices).
- **User Interface:** Material 3 with customized high-contrast themes optimized for direct outdoor sunlight readability.
- **Local Storage & Offline Synchronization:** SQLite / local shared preferences to cache assigned work steps, isolation checklists, and emergency procedures during corridor dead-zone signal loss.
- **Field Evidence & Hardware Sensors:**
  - Integrated camera plugin for compulsory before-and-after photo capture and video walkthroughs.
  - `geolocator` and GPS sensor hardware access to enforce geofence tolerances ($\le 100$ meters from track asset).
  - EXIF header extraction for timestamp and GPS tamper-proofing.

### 2.4 Data, Persistence & Storage Layer
- **Relational Database:** **PostgreSQL 16** (hosted on Neon Serverless in production).
  - Architecture: Transactional JSONB snapshot schema (`railos_state` table with namespace, key, version, and updated_at) providing atomic state transitions, schema evolution safety, and instant zero-downtime rollbacks.
- **In-Memory Testing & Demo Repository:** A thread-safe, lock-synchronized in-memory repository implementing identical commit/rollback semantics for zero-dependency local dev and instant demo state resets.
- **Object Storage:** S3-compatible cloud storage (Cloudflare R2 / AWS S3 / MinIO) for immutable storage of field inspection photographs, thermal scans, and post-work walkthrough videos.

### 2.5 DevOps & Infrastructure
- **Containerization:** Multi-stage **Dockerfiles** for the API (`Dockerfile.api`) and Web Control Center (`Dockerfile`).
- **Orchestration:** `docker-compose.yml` for local orchestration of Postgres, FastAPI backend, and Next.js frontend.
- **Cloud Deployment:**
  - Backend API: Configured for **Render** via `render.yaml` with persistent disk and environment isolation.
  - Frontend: Configured for **Vercel** with automated edge routing and preview builds.

---

## 3. Indian Railways Domain & Corridor Model

RailOS models the high-density **Ghaziabad (GZB) – Aligarh (ALJN)** corridor of North Central Railway:
- **Total Distance:** ~106 km.
- **Stations:** 16 interlocked stations (including GZB, Maripat, Dadri, Boraki, Ajaibpur, Dankaur, Wair, Chola, Khurja Jn, Somna, Aligarh Jn).
- **Track Layout:** Multi-track territory comprising UP Main, DOWN Main, and dedicated Goods/Loop lines.
- **Traction:** 25 kV AC 50 Hz Overhead Equipment (OHE) sectioned into Elementary Sections controlled by Traction Power Controllers (TPC).
- **Signalling:** Absolute Block / Automatic Block territory with electronic interlocking, multi-aspect color light signalling (MACLS), and axle counters.

### Statutory Rulebook Foundation
Every operational rule in RailOS is directly mapped to the official Indian Railways manuals:
| Manual | Domain Covered in RailOS |
|---|---|
| **IRPWM** (*Indian Railways Permanent Way Manual*) | Track renewals, deep screening, USFD inspection frequencies, Temporary Speed Restrictions (TSR, Rule 308), safety clearances (Rule 806). |
| **SEM** (*Signal Engineering Manual*) | Disconnection Notice Form T/351 (SEM 11.4), track circuit continuity (SEM 11.12), post-maintenance correspondence testing. |
| **ACTM** (*AC Traction Manual*) | Permit to Work (PTW Form ACTM 20603), 20-min pre-work de-energisation/earthing lead-in, 15-min post-work energisation buffer (ACTM 20610), 2-meter electrical clearance rule. |
| **IRTMM** (*Indian Railways Track Machine Manual*) | Minimum block durations for heavy machines (BCM, CSM, UNIMAT, TRT), 200 m inter-machine buffer (IRTMM 3.2.1). |
| **GR & SR** (*General Rules & Subsidiary Rules*) | Authority to enter block section, Banner flags and detonator protection (GR 15.06), line clear procedures (GR XIV). |

---

## 4. Core Business Logic & Intelligence Engines

The core value of RailOS lies in its five deterministic intelligence engines.

### 4.1 Engine 1: Risk & Priority Engine (`risk_engine`)

The priority engine calculates a deterministic, un-inflated urgency score for every requested task $i$. It balances structural condition with traffic criticality.

#### Mathematical Priority Scoring
$$\text{Priority}(i) = \min\left(100, \; \text{Round}\left(w_{\text{sev}} \cdot S_i + w_{\text{crit}} \cdot C_i + w_{\text{overdue}} \cdot D_i + w_{\text{traffic}} \cdot T_i + w_{\text{inspect}} \cdot I_i\right)\right)$$

Where:
- $S_i \in [1, 10]$: Defect severity (e.g., IMR rail flaw = 10; slight alignment defect = 2).
- $C_i \in [1, 10]$: Asset criticality (Main line diamond crossing = 10; loop line siding = 2).
- $D_i$: Overdue penalty factor derived from statutory inspection deadlines:
  $$D_i = \min\left(10, \; \frac{\text{Days Overdue}_i}{\text{Statutory Grace Days}} \times 10\right)$$
- $T_i$: Traffic density factor (GMT—Gross Million Tonnes carried on track).
- $I_i$: Ultrasonic flaw testing (USFD) or mandatory inspection due date factor.
- Weights configured strictly via `config/priority.yaml` (no hardcoded magic numbers).

#### Deferral Risk Growth
If a task is omitted from a schedule, its deferral debt compounds:
$$\text{Risk}_{\text{deferral}}(t) = \text{BaseRisk} \cdot e^{\lambda \cdot \Delta t} + \text{ConsequenceMultiplier} \cdot \text{AssetClass}$$
For critical safety defects (such as IMR—Immediate Removal rail flaws), the curve switches from linear to a step-function forcing inclusion before the 72-hour statutory deadline.

---

### 4.2 Engine 2: Block Opportunity Engine (`opportunity_engine`)

This engine reads working timetables (WTT) and freight rake dispatch forecasts to locate viable track possession windows without pre-supposing maintenance assignments.

1. **Traffic-Free Gaps:** For each track and station section, intervals $[t_1, t_2]$ are identified where no scheduled train movement exists.
2. **Headway Buffers:** A minimum clear headway margin ($H \ge 15$ minutes) is padded before the first train exit and after the next train entry:
   $$\text{Usable Window} = [t_{\text{train\_exit}} + H, \; t_{\text{train\_entry}} - H]$$
3. **Shadow Block Detection:** When high-impact maintenance occupies a section (e.g., UP Main Line blocked for turnout renewal), train traffic over that line drops to zero. The engine detects resulting **Shadow Opportunities** on adjacent converging tracks, allowing S&T or TRD to safely execute work in the shadow of the primary block without imposing incremental passenger delay.

---

### 4.3 Engine 3: Multi-Department Bundling Engine (`bundling_engine`)

The bundling engine prevents the historic error of granting three isolated 2-hour blocks when a single coordinated 3.5-hour block can accomplish all three tasks.

#### Verification Matrix (`packages/bundling_engine`)
Task combinations are evaluated against a verified safety compatibility matrix:
- **`COMPATIBLE`:** Tasks can occur simultaneously in the same spatial block.
  *Example:* CSM Tamping (Civil) + Track-Circuit Bond Check (S&T) + Tower Wagon OHE inspection (TRD) provided longitudinal spacing $\ge 200\text{ m}$.
- **`STRICTLY_PROHIBITED`:** Physical or electrical impossibility.
  *Example:* Deep screening with BCM under live OHE (Violates ACTM 20.3; minimum 2-meter physical clearance from 25 kV live contact wire required).
  *Example:* Ballast cleaning machine (BCM) operating simultaneously over an active point machine being overhauled.
- **`SEQUENTIALLY_COMPATIBLE`:** Tasks must follow a strict chained order within the same block:
  *Example: Turnout Renewal:*
  $$\text{S\&T Disconnect (T/351)} \longrightarrow \text{TRD OHE Isolation} \longrightarrow \text{ENGG Track Replacement} \longrightarrow \text{TRD OHE Align} \longrightarrow \text{S\&T Reconnect \& Correspondence Test}$$
- **`CONSERVATIVE_FALLBACK`:** Any pair of tasks not explicitly verified in the matrix defaults to **`INCOMPATIBLE`**. Co-location never implies safety.

---

### 4.4 Engine 4: Constraint Optimizer (`optimizer`)

The optimizer treats railway scheduling as a **Resource-Constrained Project Scheduling Problem with Spatial Disjunctions and Sequence-Dependent Setups (RCPSP-SDST)**, solved using **Google OR-Tools CP-SAT**.

#### Decision Variables
- $s[i] \in [0, H]$: Start time of task $i$ in minutes within planning horizon $H$.
- $e[i] \in [0, H]$: End time of task $i$ ($e[i] = s[i] + \text{duration}[i]$).
- $p[i] \in \{0, 1\}$: Presence boolean (1 if task $i$ is scheduled; 0 if deferred).
- $a[i, b] \in \{0, 1\}$: Boolean indicator that task $i$ is assigned to block $b$.
- $bs[b], be[b]$: Start and end minutes of block possession $b$.

---

#### The 18 Inviolable Hard Constraints (HC-001 through HC-018)

| ID | Rule Name | Indian Railways Authority | Mathematical Formulation & Logical Rule |
|---|---|---|---|
| **HC-001** | **Passenger Path Disjunction** | GR 4.08, 15.06 | For any train $j$ running on section/track: either task ends before train entry with headway $H$ ($e[i] + H \le \text{entry}_j$), or starts after train exits ($s[i] \ge \text{exit}_j + H$). |
| **HC-002** | **Minimum Machine Block Duration** | IRTMM Chapter 3 | Track machines require continuous operating setup. Minimum durations enforced: BCM: 240m; CSM: 150m; UNIMAT: 150m; TRT: 240m; DGS: 120m; Tower Wagon: 120m. $e[i] - s[i] \ge \text{MIN\_DUR}[m]$. |
| **HC-003** | **OHE Isolation Lead-in Buffer** | ACTM 20603 | Traction Power Controller (TPC) power block isolation & discharge rod earthing requires 20 minutes prior to work start: $s[i] \ge \text{ptw\_grant} + 20$. |
| **HC-004** | **OHE Energisation Buffer** | ACTM 20610 | Following work completion, removing discharge rods and re-energisation requires 15 minutes before track reopening: $\text{block\_end} \ge e[i] + 15$. |
| **HC-005** | **S&T Disconnection Notice (T/351)** | SEM 11.4 | Signals, points, and detection circuits cannot be physically touched until Station Master formally endorses Form T/351: $s[i] \ge t351\_\text{endorsed}$. |
| **HC-006** | **Mandatory Correspondence Testing** | Railway Board Mandate (Post-Balasore 2023) | For any maintenance affecting points or detection equipment, physical correspondence testing between field point and relay room/VDU is mandatory: $\text{block\_clear} \ge e[i] + 30\text{ min}$. |
| **HC-007** | **Turnout Renewal Sequence** | Joint Procedural Order (JPO) | Enforces strict sequence ordering: $s[\text{TRD Iso}] \ge e[\text{SNT Discon}]$, $s[\text{ENGG}] \ge e[\text{TRD Iso}]$, $s[\text{TRD Align}] \ge e[\text{ENGG}]$, $s[\text{SNT Reconnect}] \ge e[\text{TRD Align}]$. |
| **HC-008** | **Machine Spacing Separation** | IRTMM 3.2.1 | When two track machines operate in the same section simultaneously, physical buffer must be maintained: if intervals overlap, $|\text{pos}[m_1] - \text{pos}[m_2]| \ge 200\text{ meters}$. |
| **HC-009** | **Single Machine Occupancy** | Physical Constraint | A single machine cannot be in two places at once: `AddNoOverlap(intervals of machine m)`. |
| **HC-010** | **Adjacent Line Infringement** | IRPWM 806 | Heavy machine operations (e.g. BCM boom swinging) infringing adjacent track limits require issuing Form T/409 Caution Order restricting adjacent track speed to $\le 45\text{ km/h}$. |
| **HC-011** | **IMR Rail Flaw Statutory Deadline** | USFD Manual 6.3 | IMR (Immediate Removal) ultrasonic rail flaws must be rectified within 72 hours of detection: $s[i] \le \text{detected\_at} + 4320\text{ min}$, and $p[i] = 1$ (forced scheduled). |
| **HC-012** | **Tower Wagon Track Occupancy** | ACTM Volume VI | Tower wagons run on rails and occupy track; enforces adjacent-track disjunction and accounts for sequence-dependent machine transit between stations. |
| **HC-013** | **Gang Transit Feasibility** | Operational Feasibility | Maintenance gangs require transit time between locations: $s[B] \ge e[A] + \text{TransitTime}(A, B)$ for identical gang resource. |
| **HC-014** | **Line-Clear Occupancy** | GR XIV | No maintenance block may commence until Section Controller verifies line-clear and preceding train has cleared the block section. |
| **HC-015** | **Daylight Constraint** | IRPWM / Safety Manual | Non-illuminated works must occur between sunrise and sunset: $s[i] \ge \text{sunrise}$ and $e[i] \le \text{sunset}$ unless mobile floodlighting plant is allocated. |
| **HC-016** | **Maximum Weekday Block Cap** | Joint Operating Policy | Weekday continuous block duration capped at 240 minutes (4 hours) to protect passenger throughput. Longer blocks allowed only during Sunday Mega Blocks. |
| **HC-017** | **Track Circuit Continuity Escort** | SEM 11.12 | Mechanical tamping or heavy ballast renewal requires dedicated S&T escort resource continuously present over interval to prevent signal circuit snapping. |
| **HC-018** | **Temporary Speed Restriction Footprint** | IRPWM 308 | Track renewal leaves uncompacted ballast: enforces Temporary Speed Restriction (TSR) footprint: 20 km/h on Day 1, 45 km/h on Day 2, and 75 km/h on Day 3. |

---

#### Multi-Objective Function ($Z$)
Soft constraints are scaled into an integer objective function maximized by CP-SAT:

$$Z = w_1 \cdot \text{Yield} + w_3 \cdot \text{Bundling} + w_8 \cdot \text{MachineUse} - w_2 \cdot \text{PassengerDelay} - w_4 \cdot \text{FreightDetention} - w_5 \cdot \text{OverrunRisk} - w_6 \cdot \text{DeferralDebt} - w_7 \cdot \text{SRFootprint}$$

1. **SO-001 (Yield - 30%):** $\sum \text{Priority}_i \cdot \text{WorkUnits}_i \cdot p_i$ (total priority maintenance completed).
2. **SO-002 (Passenger Delay - 25%):** Penalizes passenger train delay multiplied by train class weight (Vande Bharat/Rajdhani = 5.0, Suburban Peak = 4.0, Mail/Express = 3.0, Ordinary Passenger = 1.5).
3. **SO-003 (Bundling Benefit - 15%):** Reward for co-scheduling multi-department task pairs in a single block.
4. **SO-004 (Freight Detention - 10%):** Demurrage penalty for holding freight rakes in loops.
5. **SO-005 (Overrun Risk - 10%):** Penalizes tasks scheduled with inadequate buffers: $\text{WindowDuration} - \text{TaskDuration} < 2\sigma$.
6. **SO-006 (Deferral Debt - 5%):** Penalizes leaving overdue tasks unscheduled: $\sum \text{OverdueDays}_i \cdot (1 - p_i)$.
7. **SO-007 (Speed Restriction Footprint - 3%):** Penalizes cumulative corridor length under caution orders.
8. **SO-008 (Machine Utilization - 2%):** Maximizes effective productive hours of high-capital machines (CSM, BCM).

#### The Three Canonical Profiles
By varying weight vectors $w_1 \dots w_8$ in `config/objectives.yaml`, the solver produces three distinct operational plans:
- **`BALANCED`:** Standard equilibrium balancing safety, throughput, and maintenance yield.
- **`SAFETY_FIRST`:** Heavy penalties on deferral debt and buffer shortages; schedules critical works immediately.
- **`OPERATIONS_FIRST`:** Strict minimization of passenger train delays and caution order footprints.

---

### 4.5 Closed-Loop Feedback: Train Graph Recomputation (`traingraph.py`)
A fundamental breakthrough in RailOS is solving against the timetable **created by the plan**, rather than the static timetable:
1. Imposing HC-010 (adjacent 45 km/h caution order) and HC-018 (post-block 20 km/h speed restriction) slows passing trains.
2. Slower trains consume more running time, shifting their entry and exit times at downstream stations.
3. This time shift alters downstream traffic-free windows.
4. `optimizer.solve()` runs a **fixed-point convergence loop**:
   - Solves initial CP-SAT schedule.
   - Passes speed restrictions to `traingraph.py` to re-simulate train runs using NetworkX.
   - Checks if any rescheduled train path violates HC-001 against planned maintenance.
   - If collisions occur, re-solves the model against the updated train graph until zero conflicts remain.

### 4.6 Independent Zero-Trust Audit Pass (`audit.py`)
To prevent software bugs or optimizer misconfigurations from relaxing safety rules:
- Every plan produced by the CP-SAT solver is passed to `audit.py`.
- `audit.py` is a standalone validator that **does not use OR-Tools**.
- It parses raw time intervals, machine assignments, and safety buffers, evaluating all 18 hard constraints sequentially.
- If any constraint is violated, the plan is **marked `INVALID` and rejected**. RailOS never presents an unverified plan to a railway officer.

---

### 4.7 Engine 5: Emergency Replanning & Disturbance Simulator (`simulator`)
When emergencies strike on an active corridor, RailOS does not discard the entire weekly plan:
- **Dynamic Replanning (`replan.py`):** When an emergency (e.g., sudden rail fracture at Km 114/2) is reported:
  - Freezes all in-progress and immediately pending blocks (`locked=True`).
  - Injects an emergency task with top priority and forced immediate execution.
  - Re-solves the CP-SAT model for the remaining planning horizon ($t \ge \text{now}$).
  - Outputs a new plan version linked to its parent, logging the exact operational delta.
- **Deterministic Simulator (`simulator.py`):** Provides 7 built-in stress-test disturbance scenarios:
  1. `critical_defect`: Sudden IMR rail fracture requiring immediate 60-min emergency block.
  2. `train_delay`: Cascading 45-min delay on inbound Rajdhani Express.
  3. `overrun`: Tamping machine bursts block by 45 minutes due to hydraulic hose rupture.
  4. `ohe_breakdown`: Catenary parting in section SEC_GZB_DER.
  5. `machine_breakdown`: BCM failure requiring siding stabling and relief engine.
  6. `weather_caution`: Dense fog imposing 30 km/h corridor-wide speed restriction.
  7. `suburban_surge`: Additional peak-hour commuter train paths inserted.

---

## 5. The Nine-Stage Statutory Possession Lifecycle

RailOS governs track possessions through an authenticated, role-gated state machine matching Indian Railways operating practice.

```
       [ Guided Ticket Creation ]
                   │
                   ▼
       [ Multi-Department Sanction ]  (Sr.DEN + Sr.DSTE + Sr.DEE + Sr.DOM)
                   │
                   ▼
┌──────────────────┴────────────────────────────────────────────────────────┐
│                        POSSESSION LIFECYCLE                               │
│                                                                           │
│  [ PLANNED / SANCTIONED ]                                                 │
│            │                                                              │
│            ▼ (Controller Grants Realtime Slot)                            │
│  [ CLEARANCE_REQUESTED ] ──► [ CLEARANCE_GRANTED ]                        │
│                                    │                                      │
│                                    ▼                                      │
│  [ SNT Disconnection T/351 ] ◄────┼────► [ TRD Power Block / PTW ]       │
│  • T351 Requested                 │      • PTW Requested                  │
│  • T351 Issued (Station Master)   │      • Power Isolated & Earthed (TPC) │
│  • T351 Endorsed (Supervisor)     │      • PTW Issued (Discharge Rods)    │
│            │                       │                      │               │
│            └───────────────────────┼──────────────────────┘               │
│                                    ▼                                      │
│                      [ WORK_IN_PROGRESS ]                                 │
│                      (Site work + Geo-tagged Evidence)                    │
│                                    │                                      │
│       ┌────────────────────────────┴────────────────────────────┐         │
│       ▼ (Work Completed On Time)                                ▼         │
│  [ HANDBACK_REQUESTED ]                                [ OVERRUN_DECLARED ]
│       │                                                (Block Burst)      │
│       ▼                                                         │         │
│  [ CORRESPONDENCE_TEST ] (S&T 30-min point verification)        │         │
│       │                                                         │         │
│       ▼                                                         │         │
│  [ RE-ENERGISED & T351 RECONNECTED ]                            │         │
│       │                                                         │         │
│       ▼                                                         │         │
│  [ FITNESS_CERTIFIED ] (Track safe for traffic)                 │         │
│       │                                                         │         │
│       ▼                                                         │         │
│  [ TSR_IMPOSED ] (Caution Order T/409 imposed) ◄────────────────┘         │
│       │                                                                   │
│       ▼                                                                   │
│  [ CLOSED / NORMALISATION ] (Track Handed to Station Master)             │
└───────────────────────────────────────────────────────────────────────────┘
```

### 5.1 Guided Ticket Intake
Section Engineers submit maintenance block requisitions through a guided composer. The server overrides client input with mandatory safety parameters:
- Automatically assigns machine type and minimum duration.
- Flags mandatory S&T escorts for mechanical tamping.
- Flags mandatory PTW and 20-min earthing buffers for work within 2 meters of OHE.

### 5.2 Multi-Department Sanction Chain
Before reaching the daily operating sheet, a plan must achieve joint sanction:
1. **Civil Engineering (Sr.DEN):** Sanctions track machine, ballast, and permanent way readiness.
2. **Signal & Telecom (Sr.DSTE):** Sanctions interlocking disconnection and correspondence test crews.
3. **Traction Distribution (Sr.DEE):** Sanctions elementary section power isolation.
4. **Operating (Sr.DOM / Section Controller):** Sanctions path dispatch and traffic-free clearance.

### 5.3 Isolation & Handback Sequence
1. **S&T Disconnection:** Station Master issues Form T/351; field supervisor physically endorses it before any track circuit or point machine is disturbed.
2. **Traction Isolation:** Traction Power Controller (TPC) remotely trips circuit breakers, field traction staff affix discharge rods to earth the contact wire, and a Permit to Work (PTW) is issued.
3. **Execution & Evidence:** Field supervisor uploads geo-tagged, timestamped site photos verifying track clearance.
4. **Post-Balasore Correspondence Testing:** Before handing back points or detection equipment, field technician and station master verify that switch physical position matches the electronic interlocking VDU display identically in Normal and Reverse positions.
5. **Fitness & TSR:** Engineering Section Engineer issues a formal Track Fitness Certificate certifying track stability, and Station Master issues Form T/409 Caution Order specifying the Temporary Speed Restriction.

### 5.4 Block Burst & Overrun Management
If work exceeds the sanctioned window:
- System triggers `POSSESSION_OVERRUN` alert to Control Center at $T-15$ minutes.
- When time expires, status transitions to `BLOCK_BURST`.
- Section Controller logs mandatory cause category: `MACHINE_FAILURE`, `OHE_RE_ENERGISATION_DELAY`, `SNT_CORRESPONDENCE_FAILURE`, `GANG_SHORTAGE`, or `TRAFFIC_HOLDING`.
- Block bursts are persisted to `block_bursts` table for divisional safety reviews.

---

## 6. API Architecture & Interface Catalog

The backend exposes a clean, typed RESTful and WebSocket API grouped by operational boundary.

### 6.1 Core Endpoints

| Group | Method | Path | Description |
|---|---|---|---|
| **Corridors & Assets** | `GET` | `/api/v1/corridors` | Lists monitored railway corridors (GZB-ALJN). |
| | `GET` | `/api/v1/assets` | Query track segments, turnouts, signals, elementary sections. |
| | `GET` | `/api/v1/network/catalog` | Hierarchical tree: Zone $\to$ Division $\to$ Sub-division $\to$ Section. |
| | `GET` | `/api/v1/network/geojson` | GeoJSON features for Leaflet railway track rendering. |
| **Traffic & Demands** | `GET` | `/api/v1/trains` | Live and scheduled train movements with station pathing. |
| | `GET` | `/api/v1/train-movements` | Real-time train positions and delay status. |
| | `GET` | `/api/v1/block-windows` | Pre-computed traffic-free block opportunities. |
| **Tickets & Bundles** | `GET, POST` | `/api/v1/block-requests` | Guided block ticket submission and review. |
| | `GET` | `/api/v1/bundles` | Cross-department bundled maintenance opportunities. |
| | `GET, POST`| `/api/v1/defects` | Infrastructure defect tracking with USFD classification. |
| **Optimization** | `POST` | `/api/v1/optimization/generate` | Triggers CP-SAT solver for selected corridor and objective. |
| | `GET` | `/api/v1/optimization/{run_id}` | Fetches candidate plans, solver metrics, and unassigned tasks. |
| | `GET` | `/api/v1/block-plans` | Lists generated and archived block plans. |
| | `POST` | `/api/v1/block-plans/{id}/approve` | Formal approval by authorized Section Controller. |
| | `POST` | `/api/v1/block-plans/{id}/sanctions` | Multi-department joint sign-off (Sr.DEN, Sr.DSTE, Sr.DEE). |
| **Possessions** | `GET` | `/api/v1/possessions` | Active and upcoming field block possessions. |
| | `POST` | `/api/v1/possessions/{id}/transitions/{action}` | State machine transitions (T/351, PTW, Handback, Fitness). |
| | `GET` | `/api/v1/block-bursts` | Logged block overrun investigations and delays. |
| **Field Evidence** | `POST` | `/api/v1/evidence/upload` | Uploads photo/video with EXIF and GPS coordinates. |
| | `GET` | `/api/v1/evidence/{task_id}` | Fetches verified field media and verification status. |
| **Emergencies & Simulator** | `POST` | `/api/v1/emergencies` | Logs acute track emergency (IMR flaw, rail fracture). |
| | `POST` | `/api/v1/replanning/generate` | Executes dynamic disturbance replan around locked blocks. |
| | `POST` | `/api/v1/simulator/scenarios/{id}` | Injects deterministic disturbance scenario. |
| **Realtime & Analytics** | `GET` | `/api/v1/analytics/summary` | Yield, block burst count, delay minutes, machine utilization. |
| | `WS` | `/api/v1/ws` | Real-time pub/sub event stream for desk and mobile clients. |

---

## 7. Role-Based Access Control (RBAC) & Governance Matrix

RailOS enforces strict separation of concerns matching Indian Railways administrative hierarchies.

| Role | Operational Title | Permitted Actions & Boundaries |
|---|---|---|
| **`CONTROL_OFFICER`** | Dy. Chief Controller / Section Controller | Grants real-time block clearance, declares overruns, locks emergency plans, approves candidate plans. |
| **`PLANNER`** | Divisional Maintenance Planner | Configures horizon, selects optimization objectives, initiates CP-SAT runs, reviews bundling options. |
| **`ENGINEERING`** | Sr.DEN / SSE (Permanent Way) | Submits track renewal tickets, signs Civil Engineering sanctions, issues Track Fitness Certificates. |
| **`SIGNAL_TELECOM`** | Sr.DSTE / SSE (Signal) | Submits point/interlocking tickets, signs S&T sanctions, performs correspondence tests. |
| **`TRACTION`** | Sr.DEE (TRD) / TPC | Issues Power Block, isolates 25 kV OHE, confirms earthing, authorizes discharge rod removal. |
| **`STATION_MASTER`** | Station Master / Station Superintendent | Issues and endorses Form T/351 Disconnection, verifies line clear, closes possession. |
| **`FIELD_SUPERVISOR`** | Section Engineer / Gang Mate | Acknowledges PTW/T351, executes on-site work, captures geo-tagged photo/video evidence. |
| **`MANAGEMENT`** | DRM / ADRM / Chief Engineer | Reviews divisional analytics, block-burst trends, asset health reports, read-only audit log access. |
| **`ADMIN`** | System Administrator | Master data configuration, corridor definition, user management, synthetic seed resets. |

---

## 8. Summary & Production Readiness

RailOS replaces ad-hoc corridor maintenance requests with a mathematically rigorous, safety-certified planning and execution platform. By codifying the statutory rulebooks of Indian Railways (IRPWM, SEM, ACTM, IRTMM, GR/SR) into hard mathematical constraints and wrapping the solver in an independently audited, human-governed possession lifecycle, RailOS proves that modern decision intelligence can dramatically enhance railway track availability while upholding passenger safety and operational punctuality.
