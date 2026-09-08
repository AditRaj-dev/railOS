# RailOS — Full System Walkthrough

A guided tour of every user-facing part of RailOS: the web Control Center, the
backend API, and the Flutter field app. Written after an end-to-end pass that
actually drove each layer against a live Postgres + object-storage backend —
not just read the code — so the flows described here are verified, not
aspirational.

> RailOS proposes; an authorized railway officer decides. All possession data
> in this repo's seed dataset is synthetic — no output here is a real
> operating authorization.

---

## 1. What RailOS is

RailOS coordinates the nine-stage Indian Railways block (possession) lifecycle
across three cooperating apps:

| Stage | What happens | Who's involved |
|---|---|---|
| 1–4 | Risk scoring, opportunity detection, bundling, CP-SAT optimization | Planner, the optimizer core |
| 5 | Real-time clearance | Section Controller |
| 6 | Isolation & disconnection (T/351, PTW) | Station Master, TPC, S&T |
| 7 | Execution | Field Supervisor / Engineering |
| 8 | Testing & handback | S&T, TPC, Engineering (SSE) |
| 9 | Normalisation & block-burst accounting | Station Master, Section Controller |

Stages 1–4 (the optimization core: risk engine, opportunity detection,
bundling, CP-SAT solve, independent audit) are a separate, already-hardened
layer this walkthrough treats as a black box. This document is about the
**human authority layer** on top of it — the desk dashboard and field
screens that make stages 5–9 real, and the API that ties them together.

## 2. Architecture at a glance

```
apps/control-center/   Next.js 16 web dashboard  → Vercel
apps/api/              FastAPI backend           → Render
apps/field-app/        Flutter Android app        → APK, side-loaded or Play
packages/               optimizer, risk engine, domain models (shared)
```

- **Database**: Postgres (Neon in production) — a single JSONB snapshot row,
  committed transactionally on every write.
- **Object storage**: S3-compatible (Neon Object Storage in production,
  MinIO or an in-memory mock in local dev) — evidence photo/video bytes live
  here, addressed only by a storage key; the metadata pointing at them lives
  in Postgres.
- **Two authentication mechanisms coexist by design**: a synthetic
  `X-RailOS-User`/`X-RailOS-Role` header pair (no credential, just declares
  who you're acting as) that every endpoint in `main.py` understands, and a
  real Argon2+JWT login (`evidence_routes.py`) that the web dashboard and
  field app can both use for a verified identity. See §8 for what each
  actually protects today.

---

## 3. Getting started locally

```bash
# Postgres (or point RAILOS_STORAGE_BACKEND=memory to skip this)
docker run -d --name railos-postgres -e POSTGRES_USER=railos \
  -e POSTGRES_PASSWORD=railos -e POSTGRES_DB=railos -p 5432:5432 postgres:16

# Backend API
cd apps/api
RAILOS_STORAGE_BACKEND=postgres DATABASE_URL=postgresql://railos:railos@localhost:5432/railos \
  uvicorn railos_api.main:app --host 0.0.0.0 --port 8000
# Swagger UI: http://localhost:8000/docs

# Web dashboard
cd apps/control-center
npm install && npm run dev
# http://localhost:3000

# Field app (emulator)
cd apps/field-app
flutter pub get && flutter run --dart-define=RAILOS_API_BASE=http://10.0.2.2:8000
```

Seed accounts (created automatically on first run):

| Employee ID | Password | Role | Department | Use for |
|---|---|---|---|---|
| `EMP001` | `Admin@123` | ADMIN | — | supervisor administration, everything |
| `EMP901` | `Field@123` | SUPERVISOR | ENGG (Permanent Way) | field app login, track/civil evidence |
| `EMP902` | `Field@123` | SUPERVISOR | SNT (Signal & Telecom) | field app login, signalling evidence |
| `EMP903` | `Field@123` | SUPERVISOR | TRD (Traction) | field app login, OHE/traction evidence |

`/api/v1/work/assignments/mine` scopes each supervisor's assigned tasks to their own department — an ENGG supervisor never sees SNT or TRD maintenance tasks, matching how field staff are actually organised.

---

## 4. Web Control Center — screen by screen

Every screen lives under `apps/control-center/src/app/(shell)/*` with a
matching component in `src/components/`. The shell (`AppShell.tsx`) filters
the left nav by acting role — a role you either pick from a dropdown
("synthetic mode") or arrive at automatically by logging in for real.

### Sign-in
Top-right of the header. Two ways to establish "who you are acting as":

- **Acting role dropdown** — pick a role (Section Controller, Sr. DOM,
  Station Master, TPC, …). No credentials; the app trusts you. This is what
  every screenshot and demo of this app has run on so far.
- **Log in** — a real employee ID + password against the JWT backend. On
  success, the dropdown is replaced with your verified name and role, and a
  sign-out control. The session persists across a browser reload (a 30-day
  refresh token in `localStorage`; the access token itself is never
  persisted, only held in memory and silently refreshed every ~14 minutes).

Logging in drives *both* mechanisms at once: the real Bearer token is sent to
endpoints that understand it, and your verified role is pushed into the same
store the dropdown uses, so screens that only know the synthetic header
still see the right role.

### Command Center (`/command-center`)
The 5-second situation view. Six metric tiles (critical defects, overdue
backlog, active/planned blocks, corridor pressure, maintenance debt, open
tasks) pull from live tasks and the currently-active plan — no fixture data.
Three columns below: the top 3 highest-risk open tasks, the active plan's
possession blocks, and the active plan's solver warnings. An "Inject
Emergency Defect" button records a real `IMR`-severity emergency against the
API and hands you straight to the planner to replan around it.

### Network Digital Twin (`/network`)
A schematic of the corridor's sections, colour-coded by derived status
(critical defect count → restricted; pending maintenance → caution).
Clicking a section shows its live metrics (pending maintenance, critical
defects, traffic pressure, asset availability), the section's open tasks
broken down by department, and any possession blocks from the active plan
that touch it.

### Maintenance Intelligence (`/maintenance`)
A dense, filterable table of every open maintenance task (search, department,
severity), each row showing risk score, block requirement, and status. The
detail drawer on the right shows the selected task's full technical
picture — asset, section, track, crew/machinery, and whether OHE/S&T
isolation is required. Backed entirely by `/api/v1/maintenance/tasks`.

### Block Opportunity Planner (`/planner`)
Where a plan is born. Three objective-mode buttons (Balanced, Safety First,
Operations First) select which of the optimizer's three candidate plans
you're looking at; "Run Optimizer" calls `/api/v1/optimization/generate` for
real and the UI renders whichever candidate is selected once it lands. The
possession-window list on the left is the plan's real blocks; the right
panel shows the solver's own metrics and warnings for the selected block —
no invented "why this block" narrative, just what the optimizer actually
reported. If an emergency was just injected from the Command Center, a
banner here lets you execute a real dynamic replan around it.

### Operational Gantt (`/timeline`)
A dual-axis timeline: real train movements plotted against the real
possession blocks of the active plan, both read straight from the API.
Clicking a block jumps to the planner with that block selected.

### Plan Sanctions (`/plans`)
Lists every API-backed plan and, for the selected one, the full
**sanction chain panel**: the ordered list of statutory authorities required
for that specific plan (derived from its blocks — Section Control always,
+Sanction for mega/multi-department plans, +Traction Power for power blocks,
+Station/S&T for disconnections), who has signed each one, with what reason
and form reference, and — if the chain isn't complete — a sign/refuse form
that's only enabled if the *authority* matches your acting role. A 202
response (partial chain) renders as visible progress, not an error. When the
final required signature lands, the plan flips to APPROVED and its
possessions open automatically — this is the seam between planning and the
day-of authority layer.

### Possession Board (`/possessions`)
The Section Controller's day-of desk: every open possession, its state, its
planned window, a live overrun clock, and inline Grant/Defer/Cancel/Close
buttons — but only the ones the API actually returned as allowed for your
role and the possession's current state. Subscribes to the live event stream
rather than polling.

### Possession Detail (`/possessions/[id]`)
The nine-stage lifecycle rendered as a progress spine, the Form T/351 and
Permit-to-Work artefacts (form numbers, who issued/endorsed, earthing
status), the handback checklist as a real satisfied/outstanding list, and
the complete transition timeline — every action, actor, role, and rule
citation, in order. Every action button here comes from the API's own
`allowedActions` for the possession; there's no client-side guess at what's
legal.

### Railway Analytics (`/analytics`)
The loop the original audit found never closed: planned-vs-actual close time
for every completed possession, with overrun minutes broken down by
department and cause category. This is where a block burst — the audit
trail's record of *why* a possession ran long — surfaces for the first time.

### Field Evidence (`/evidence`)
A table-based triage queue: flagged exceptions requiring a Control Officer's
accept/reject decision, a full audit timeline of every evidence item's
status and signature, and supervisor account administration (create
accounts, edit assigned sections). The review dialog shows the captured
media, geospatial verification (distance to target, GPS accuracy, verdict),
and cryptographic integrity (SHA-256 hashes, Ed25519 signature status).

### Evidence Media Gallery (`/evidence-media`)
A visual, media-first companion to the page above: every photo/video as a
grid tile (thumbnail or muted video preview), filterable by kind and status,
with the same verification dialog on click. Built specifically because a
table of IDs is a poor way to *look at* photos.

### Field Monitor (`/field`)
A deliberately read-only mirror of what the field app sees — possession
windows, state, handback readiness — for control-room staff who want
visibility without a phone in hand. Per the platform's own design decision,
the Flutter app is the real field surface; this screen never offers an
action button.

---

## 5. Backend API — domain by domain

Base URL locally: `http://localhost:8000`. Full interactive reference:
`/docs` (Swagger UI, auto-generated from the FastAPI schema).

### Auth (`/api/v1/auth/*`, `/api/v1/me`)
`POST /login` (employee ID + password) → 15-minute access JWT + 30-day
rotating refresh token. `POST /refresh` rotates the refresh token — reusing
an already-rotated one fails with 401. `POST /logout` revokes it. Every
other endpoint also accepts the synthetic `X-RailOS-User`/`X-RailOS-Role`
header pair with no credential at all — see §8 for what that means in
practice.

### Network (`/api/v1/network/*`)
Zones → divisions → sections → segments → stations, plus a combined
`/catalog`, a `/geojson` export (with bbox filtering), and free-text
`/search`. Read-only, no auth beyond "some role."

### Maintenance & defects (`/api/v1/maintenance/*`, `/api/v1/defects`)
List/get tasks, list defects, and `POST /defects` (ENGINEERING/SIGNAL_TELECOM/
TRACTION only) to log a new one. `/api/v1/maintenance/priority` and `/risk`
proxy the risk-scoring engine when it's importable, 503 otherwise — the API
never fakes a score if the engine is unavailable.

### Planning & optimization (`/api/v1/optimization/generate`, `/api/v1/block-plans/*`)
Generates three candidate plans (Safety First / Balanced / Operations First)
via the CP-SAT optimizer, independently re-audits each for genuine hard-
constraint violations, and rejects generation only if *every* candidate
fails that audit — not if a candidate merely carries an advisory note like
"needs a Permit to Work" (that's expected paperwork the possession chain
handles next, not a violation; conflating the two was a real bug fixed this
session — see §9). `Idempotency-Key` on generation prevents duplicate runs
from a retried request.

### Sanctions (`/api/v1/block-plans/{id}/sanctions`)
`GET` returns the chain (required authorities, signatures so far, complete/
refused). `POST` records one authority's decision; the final `GRANTED`
signature that completes the chain bumps the plan to APPROVED, materialises
its assignments, and opens its possessions in the same transaction. A version
bump or replan invalidates every previously-collected signature — a Sr. DOM
sanctioned *that* plan, not whatever it becomes after a recompute.

### Possessions (`/api/v1/possessions/*`)
28 statutory transitions across stages 5–9, table-driven — any action not
legal for the possession's current state returns 409 `ILLEGAL_TRANSITION`
with the actual list of what *is* allowed. Selected guarantees actually
verified this session:

- **HC-014**: `grant-clearance` fails if another possession is live on the
  same section+track.
- **HC-003/HC-005**: `start-work` checks real elapsed lead-in time since PTW
  issuance (20 min) or T/351 issuance (10 min) against either the server
  clock or a supplied `clientEventAtUtc` for offline field acts.
- **HC-006**: `record-correspondence-test` rejects any duration under 30
  minutes with 422 `TEST_TOO_SHORT`.
- **Offline replay**: every possession POST is idempotent via
  `Idempotency-Key`; a same-target-state replay returns 200 with
  `"replayed": true` instead of 409. Actions that assert something is true
  *right now* (`issue-ptw`, `grant-clearance`, `certify-fitness`, `close`,
  …) are explicitly never replayable and 409 if a client tries.
- **Block burst**: overrun is derived on read and persisted exactly once at
  `close`, with a deterministic `burstId` so a replay can't double-record it.

### Evidence & bucket storage (`/api/v1/evidence/*`)
Metadata (task/step linkage, geo verdict, review notes, hashes, Ed25519
signature) lives in Postgres, in the same repository as tasks and
possessions — durable across restarts. The actual photo/video bytes never
touch the API process: `initiate`/`presign`/`complete` drive a real
multipart upload straight to the S3-compatible bucket via presigned URLs,
and `GET` responses hand back a presigned *download* URL the same way. A
capture outside its target radius still uploads — it lands as
`FLAGGED_REVIEW` for a Control Officer to accept-with-reason or reject, not
silently dropped.

### Analytics (`/api/v1/analytics/summary`, `/api/v1/block-bursts`)
Aggregate maintenance/defect/traffic numbers and the full block-burst ledger
(planned vs. actual close, overrun minutes, cause category) that the
Analytics screen renders.

### Emergency & replanning (`/api/v1/emergencies`, `/api/v1/replanning/generate`)
`POST /emergencies` inserts a real high-severity task into the world model
and returns an emergency ID; `POST /replanning/generate` re-solves around it
and returns a diff (added/removed/moved/displaced tasks) against the parent
plan, which is preserved rather than overwritten.

### Admin & supervisors (`/api/v1/admin/supervisors/*`)
Create a field-app account, list accounts, update a supervisor's assigned
section codes. ADMIN-only by `require_role` — but see §8 for the caveat on
what actually enforces that today.

---

## 6. Flutter field app — screen by screen

`apps/field-app`, imperative `Navigator.push` (no router — five screens
doesn't need one). Every possession action button is driven by the same
`allowedActions` array the web dashboard reads, so the phone and the desk
can never disagree about what's legal right now.

### Login
Employee ID + password against the same JWT backend the web dashboard's
"Log in" button uses. Ships with a language toggle (English/Hindi) and a
visible note that the 24-hour offline entitlement is already active —
this app is built to keep working on a train with no signal.

### Dashboard
The supervisor's shift view: assigned tasks (with a step-completion count
per task), any active possessions they can jump straight into, an emergency
hazard-report button, and an offline-sync indicator that shows exactly how
many captures are queued and lets the supervisor force a flush.

### Task Detail
A task's ordered macro-steps, each showing its title/description and a
capture button — camera icon for a photo step, video icon for the ≤90-second
completion video every task ends with. A step already verified shows a
"Retake Proof" option instead.

### Capture
The evidence pipeline's front door. Live GPS fix (age and accuracy shown as
a pill), haversine distance to the step's target coordinates, and a visible
in-radius/out-of-radius indicator *before* the shutter fires. Capturing
outside the radius forces a mandatory exception-reason prompt — the
supervisor can't silently submit an out-of-radius photo without explaining
why. After capture, the media is watermarked with task/step ID, GPS,
distance, and a SHA-256 prefix, queued locally, and only then uploaded — if
the upload fails, it stays safely in the offline queue rather than being
lost.

### Emergency Report
A standalone hazard-reporting form (section code, KM post, severity,
hazard classification, free-text description) that transmits directly to
divisional control. The screen carries an explicit, permanent notice: this
form never authorizes a possession, isolation, train movement, or block
extension by itself — it's a report, not an action.

### Possession (hub)
Opened from the dashboard's active-possessions list. A live countdown
against the planned window, the possession's current state, and buttons for
every currently-allowed action — routing to Isolation, Work, or Handback as
the state progresses. An offline action is visibly marked "saved offline,
will replay when online" rather than silently queued.

### Isolation
Role-branched by design: a Station Master sees T/351 issue + endorse, a TPC
sees the isolator list, earthing confirmation, and PTW issue, an SSE sees
the protection checklist with detonator count. Each artefact card shows its
form number and statutory rule citation, matching the desk dashboard's
possession-detail view exactly.

### Work
The execution-stage screen: a live clock against the block's planned end
time, an amber-to-critical overrun banner once that time passes, and the
work-status progression (Ready → Start → Delay → Cannot Complete → Done)
layered over the same task steps from Task Detail — work now hangs off a
possession instead of floating free of one.

### Handback
The stage-8/9 screen: the handback checklist as a real list, correspondence-
test entry with the 30-minute floor enforced client-side (not just
server-side — the supervisor sees the rejection before wasting a round
trip), discharge-rod removal, PTW cancellation, and fitness certification
with the 20/45/75 km/h TSR speed ladder.

### Offline queue, under the hood
Backed by `sqflite` (not memory) — a queued transition survives a full app
restart, verified by an actual test. A `connectivity_plus` listener flushes
the queue on reconnect with exponential backoff. Actions that assert
something is true *right now* (issuing a PTW, granting clearance, certifying
fitness, closing a possession) are rejected at the moment of queueing with a
clear message, rather than queued and silently failed later — a permit to
work asserted five minutes after the line was actually re-energised isn't
a permit to work.

---

## 7. Deployment

| Component | Host | Notes |
|---|---|---|
| Control Center | Vercel | `NEXT_PUBLIC_RAILOS_API_URL` points at the Render API |
| API | Render (free tier, Docker) | `RAILOS_STORAGE_BACKEND=postgres`, `DATABASE_URL` from Neon |
| Database | Neon Postgres | single JSONB snapshot table, `railos_state` |
| Object storage | Neon Object Storage (S3-compatible) | `AWS_ENDPOINT_URL_S3` + credentials |
| Field app | Android APK | now defaults to `https://railos-api.onrender.com`; override with `--dart-define=RAILOS_API_BASE=...` for local/staging builds |

Full step-by-step in `DEPLOYMENT.md` and `DEPLOYMENT_NEON_RENDER_VERCEL.md`.

---

## 8. Known limitations (found and fixed, or found and flagged, this session)

**Fixed, verified against real infrastructure:**
- Postgres writes were silently never committed (an unclosed implicit
  transaction from `PostgresRepository`'s startup read) — every write since
  process start was invisible to any other connection and would vanish on
  restart. Fixed; verified a restart now correctly rehydrates persisted state.
- Evidence metadata (`work_steps`, `evidence_items`, `upload_sessions`) lived
  in a plain in-memory dict, disconnected from the durable repository above —
  same restart-loses-everything problem, specifically for evidence. Fixed;
  moved into the same Postgres-backed repository.
- Plan generation rejected almost every realistic plan: it conflated the
  optimizer's own advisory obligations ("needs a Permit to Work") with actual
  audit violations, since both happened to share an "HC-" prefix. Fixed;
  the two are now tracked separately.
- `S3ObjectStore` hardcoded virtual-hosted-style addressing, which fails
  against MinIO and most self-hosted S3-compatible endpoints (including,
  likely, Neon Object Storage) before a single request is even sent. Fixed
  to use path-style addressing whenever a custom endpoint is configured;
  verified end-to-end against real MinIO (upload → presigned PUT → download
  → byte-for-byte SHA-256 match).

**Flagged, not changed (a product decision, not a bug):**
- `ENABLE_SYNTHETIC_AUTH=true` is set in production (`render.yaml`) and the
  web dashboard's `api.ts` never called anything *but* the synthetic header
  path until this session's login build. In practice this means: anyone who
  can reach the API can act as any role — sign a plan sanction as "Sr. DOM,"
  accept flagged evidence as a Control Officer — just by setting a header,
  no credential required. This is consistent with the app's "synthetic
  demo" framing throughout, and disabling it would break the deployed
  control-center outright (it has no other way to reach the evidence/admin
  endpoints for most calls). A real login now exists and is fully wired for
  the endpoints that understand a Bearer token; the possession/plan/task API
  in `main.py` has no JWT support at all yet, so a real login's role is
  mirrored into the same synthetic header those endpoints still require.
