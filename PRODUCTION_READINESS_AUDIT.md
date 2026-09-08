# RailOS — PRD vs. Actual Implementation Audit & Production Readiness Roadmap
**Audit Date:** September 2026  
**Auditor:** RailOS System Architecture & Production Engineering Agent  
**Baseline Specs:** 
- `RailOS Platform — Six Integrated Product Requirement Documents.md` (Master Platform PRD 0 to 6)
- `RailOS Indian Railways Ground Reality Report.md`
- `RailOS_Live_Feeds_and_Scraping_Sources.md`
- `AGENTS.md` / `CODEX.md` / `ANTIGRAVITY.md` / `CLAUDE.md`

---

## EXECUTIVE SUMMARY

RailOS has built an end-to-end prototype and operational proof-of-concept:
1. **Frontend**: Next.js 15 App Router Control Center (`apps/control-center`) with rich operational views (`/command-center`, `/network`, `/maintenance`, `/planner`, `/timeline`, `/plans`, `/analytics`, `/field`), responsive Territory Selector, and Gemini Pro Digital Twin reasoning.
2. **Optimization Core**: Multi-department constraint satisfaction engine (Google OR-Tools CP-SAT in `packages/optimizer`) solving integrated track, S&T, and traction blocks under passenger headway constraints.
3. **Data Model & Backend**: Canonical schemas and event-driven FastAPI orchestrator (`apps/api`) with synthetic connectors for TMS, SMMS, TDMS, COA, and BDMS.

However, from an **actual Indian Railways production standpoint (CRIS, RDSO, Zonal Headquarters, and Divisional Control Offices)**, the system currently operates on **synthetic in-memory state, simulated protocols, and demo-tailored boundaries**.

This document outlines the **PRD vs. Actual Implementation Check Matrix**, gap analysis, and the **Production Readiness Roadmap** detailing what is required for commissioning into a live railway environment.

---

## 1. COMPREHENSIVE PRD VS. IMPLEMENTATION CHECK MATRIX

| Subsystem / PRD Module | PRD Specification & Requirements | Current Implementation State | Production Gap / Missing Elements |
|---|---|---|---|
| **0. Core Intelligence Engines** | - Multi-factor Priority Engine<br>- Risk Engine (24h/72h deferral)<br>- Block Opportunity Engine<br>- Task Bundling Engine<br>- OR-Tools CP-SAT Constraint Optimizer<br>- Dynamic Replanning Engine | **Implemented (Prototypes in `packages/`)**<br>`risk_engine`, `opportunity_engine`, `bundling_engine`, `optimizer`<br>57 unit tests passing | - **Dynamic Rerouting Solver**: Real trains can't simply be delayed; they must be looped or path-diverted across alternate tracks (e.g. 3rd/4th line or chord lines).<br>- **Rolling Stock & Machine Routing**: Does not solve tamping machine (CSM/BCM) depot transit times or crew duty hour limits (10-hr HOER regulations).<br>- **Dynamic Speed Restrictions (TSR)**: Does not model acceleration/deceleration curve losses per locomotive haulage tonnage. |
| **PRD 1: Web Control Center** | - Command Center 5-second situational awareness<br>- Interactive Schematic Network<br>- Maintenance Intelligence Grid<br>- Dual-Axis Timeline / Gantt<br>- 3-Candidate Trade-off Matrix<br>- Emergency Replan Workflow<br>- AI Copilot | **Implemented (`apps/control-center`)**<br>Next.js 15 App Router with full routing, responsive shell, territory selector, and Gemini Pro API route | - **Real GIS Coordinates**: Uses schematic track diagrams instead of spatial GIS / GeoJSON chainage coordinates.<br>- **High-Availability WebSockets**: Live telemetry currently polls or triggers via mock store instead of high-throughput Kafka/MQTT streaming.<br>- **Multi-User Lock & Conflict Arbitration**: If two controllers in different sections edit overlapping boundaries, no distributed mutex exists. |
| **PRD 2: Progressive Web App (PWA)** | - Supervisor mobile task management<br>- Work status progression (Ready/Start/Delay/Done)<br>- Defect reporting with GPS/photo<br>- Offline-first sync | **Partially Implemented**<br>`/field` responsive role view inside Control Center; local state actions | - **Offline ServiceWorker & IndexedDB**: No persistent offline queue when track gangs enter tunnels or deep cuttings with zero cellular reception.<br>- **Biometric / IR-eSign Authentication**: No integration with Indian Railways HRMS / biometric crew sign-on. |
| **PRD 3: Android Field Application** | - Native Kotlin/Android application<br>- Bluetooth/RFID asset tag scanning<br>- Camera USFD photo attachments<br>- Geofenced safety possession verification | **Deferred by Spec**<br>(Explicitly deferred during initial phases per PRD 3.12) | - **Entire Native App**: Must be engineered in Kotlin/Jetpack Compose with SQLite Room DB and background WorkManager sync. |
| **PRD 4: Integration Platform & Connectors** | - Canonical Data Model<br>- Adapters: TMS, SMMS, TDMS, COA, BDMS, NTES, FOIS<br>- Event bus (Kafka/RabbitMQ)<br>- Schema validation, deduplication, audit trail | **Partially Implemented (`apps/api` & `integrations/`)**<br>Synthetic adapters in `protocol.py`; SQLite/in-memory store; event dispatching in FastAPI | - **Zero Real Railway Protocols**: Real TMS uses Oracle/RDBMS, COA runs on CRIS proprietary APIs, and FOIS uses legacy terminal feeds.<br>- **No Message Broker**: Relies on Python in-memory queues instead of enterprise Apache Kafka / RabbitMQ cluster.<br>- **No Bi-directional Writeback**: RailOS cannot automatically lodge approved traffic blocks back into COA/BDMS. |
| **PRD 5: Notification & Escalation Engine** | - 5 Severity Categories (Info to Critical)<br>- Intelligent location/dept/role routing<br>- Hierarchical timer escalations (10 min -> 30 min)<br>- Multi-channel: In-app, Push, SMS, WhatsApp, Email | **Partially Implemented**<br>In-app alert banners & simulated emergency notifications | - **No Multi-Channel Providers**: No Twilio/Govt SMS Gateway (CDAC/NIC SMS portal) or WebPush service workers.<br>- **Escalation Daemon**: No persistent Celery/Temporal cron worker evaluating unacknowledged block timeouts. |
| **PRD 6: Railway Analytics & Intelligence** | - Executive KPI dashboards<br>- Maintenance debt reduction index<br>- Department efficiency comparisons<br>- Corridor Pressure Index<br>- Planned vs Actual duration variance | **Partially Implemented**<br>`/analytics` dashboard in Control Center with static/computed yield metrics | - **OLAP Data Warehouse**: Missing dedicated columnar store (ClickHouse / TimescaleDB / BigQuery) for aggregating multi-year history across 68 divisions.<br>- **Predictive Asset Deterioration**: Machine learning models (Weibull survival analysis) predicting rail fractures based on gross million tonnes (GMT) carried are not yet integrated. |

---

## 2. PRODUCTION GAP ANALYSIS (WHAT IS LEFT TO BE DONE)

### 2.1 Enterprise Data Ingestion & Live CRIS Feeds
* **CRIS/NTES Real-time Bridge**: Production deployment requires direct, high-throughput ingest of NTES train movement data (WebSocket/TCP sockets or authorized SOAP/REST CRIS gateways) instead of synthetic tables.
* **FOIS (Freight Operations Information System) Link**: In India, freight accounts for >65% of corridor revenue and absorbs massive line capacity. Freight paths are un-timetabled and dynamically created. Production RailOS must ingest FOIS rake loading, power (loco) availability, and crew call times.
* **Track Management System (TMS) & USFD Ultrasonic Data**: Raw ultrasonic rail flaw detector files (B-scan / A-scan telemetry) must be ingested directly to auto-generate IMR (Immediate Removal) and OBS (Observed) defect tickets without manual human data entry.

### 2.2 Distributed Infrastructure & Persistence Layer
* **PostgreSQL + PostGIS Clustering**: Replace in-memory dictionaries with production PostgreSQL equipped with PostGIS for spatial spatial corridor tracking (chainage km, track curves, bridge locations, level crossings).
* **Distributed Locking & Concurrency Control**: Multiple Section Controllers, Power Controllers (TPC), and Signal Controllers concurrently touch the same physical plant. Production requires Redis-backed distributed locks and optimistic concurrency versioning on `PlanVersion`.
* **Asynchronous Task Queue**: Long-running OR-Tools CP-SAT optimization passes (which take 30–90 seconds on complex 100-km multi-track networks) must run on asynchronous workers (Celery, Redis Queue, or Temporal) rather than inside the FastAPI synchronous request lifecycle.

### 2.3 Railway Operations Safety & Statutory Compliance
* **General & Subsidiary Rules (G&SR) Validation**: Every block possession on Indian Railways is governed by the Zonal General & Subsidiary Rules:
  - Absolute Block vs. Automatic Block signaling rules.
  - Caution Order Form T/409 and Authority to Pass Defective Signal Form T/369.
  - Engineering Disconnection Notice Form T/1518 and S&T Disconnection Form S&T (T/351).
  *Production RailOS must programmatically generate and digitally counter-sign these statutory paper-equivalent forms.*
* **Safety Envelope Validation (Track Isolation)**: OHE power blocks require elementary section isolations (isolator switches open, feeder breakers tripped, discharge rods placed). The production optimizer must mathematically enforce that adjacent tracks without 2m clearance are speed-restricted to 30 km/h or also possess power-cut protection.

### 2.4 Offline Native Field Architecture
* **Native Android App (Kotlin + SQLite/Room)**: Track gang supervisors work in remote rural sections with patchy 2G/zero connectivity. The field tool must be an offline-first native Android app with bi-directional conflict-free sync (CRDT or delta replay) upon reconnecting to divisional Wi-Fi or cellular networks.
* **Geofenced Block Protection**: Prevent maintenance gangs from stepping onto track without verified possession by utilizing GNSS geofencing and RTK-DGPS beacons.

### 2.5 Security, Role-Based Access & Audit Compliance
* **Railway Single Sign-On (SSO)**: Integration with Indian Railways HRMS and Railnet Active Directory via OAuth2 / SAML / OIDC.
* **Immutable Legal Audit Log**: In the event of an operational disruption, signal overshoot (SPAD), or rail defect incident, statutory safety commissioners (CRS — Commissioner of Railway Safety) require tamper-evident cryptographic audit logs recording every decision, override, timestamp, and user identity.

---

## 3. PRODUCTION READINESS ROADMAP & PHASING

```text
┌────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: DATA PIPELINE & CONNECTORS (Weeks 1 - 8)                               │
│ • Production PostgreSQL + PostGIS setup with Alembic migrations                │
│ • Real FOIS & NTES SOAP/REST CRIS API connectors                               │
│ • Kafka streaming bus for live train movements & defect telemetry             │
└──────────────────────────────────────┬─────────────────────────────────────────┘
                                       ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: OPTIMIZER HARDENING & SAFETY ENVELOPE (Weeks 9 - 16)                   │
│ • Celery/Temporal asynchronous optimization workers                            │
│ • Machine routing (CSM, BCM, Tower Wagon transit constraints)                   │
│ • Statutory G&SR rule validator & Digital T/351 Disconnection forms             │
└──────────────────────────────────────┬─────────────────────────────────────────┘
                                       ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: PRODUCTION CONTROL ROOM & MULTI-USER ARBITRATION (Weeks 17 - 24)       │
│ • Real-time WebSockets with multi-controller conflict resolution               │
│ • PostGIS-powered geographic corridor digital twin                             │
│ • HRMS/Railnet SSO and role-based access control (RBAC)                        │
└──────────────────────────────────────┬─────────────────────────────────────────┘
                                       ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 4: NATIVE ANDROID FIELD APPLICATION & PILOT COMMISSIONING (Weeks 25 - 36)│
│ • Kotlin native Android app with SQLite Room offline cache                      │
│ • Division-level pilot deployment (e.g. Prayagraj / Ghaziabad–Tundla section)    │
│ • Commissioner of Railway Safety (CRS) audit signoff                           │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. CONCLUSION

RailOS has completed the most difficult algorithmic hurdle: **mathematically demonstrating that Engineering, S&T, and Traction possessions can be bundled inside natural train headway gaps using multi-objective optimization**.

To transition this intellectual property from a software demonstrator into an enterprise railway command platform, engineering focus must now pivot toward **CRIS interface standardization, asynchronous distributed queueing, statutory railway rule enforcement, and offline field hardening**.
