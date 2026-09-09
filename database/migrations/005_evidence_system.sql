-- Migration 005: RailOS Field Evidence System
-- Authoritative schema for authenticated supervisors, ordered macro steps,
-- live geotagged photo/video evidence items, location sample traces,
-- multipart upload sessions, verification pipeline, and emergency hazard reports.

CREATE EXTENSION IF NOT EXISTS postgis;

-- 1. Users and Authentication
CREATE TABLE IF NOT EXISTS users (
  id text PRIMARY KEY,
  employee_id text UNIQUE NOT NULL,
  name text NOT NULL,
  email text UNIQUE,
  phone text,
  role text NOT NULL CHECK (role IN ('SUPERVISOR', 'ADMIN', 'DISPATCHER', 'INSPECTOR')),
  -- Required for supervisors: _department_scope() has no role-based mapping
  -- for them, so an account without one can never file or be assigned work.
  department text CHECK (department IN ('ENGG', 'SNT', 'TRD')),
  assigned_section_codes text[] NOT NULL DEFAULT '{}',
  password_hash text NOT NULL,
  active boolean NOT NULL DEFAULT true,
  disabled_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
  token_hash text PRIMARY KEY,
  user_id text NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at timestamptz NOT NULL,
  revoked_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id, expires_at);

-- 2. Field Areas and Supervisor Jurisdiction
CREATE TABLE IF NOT EXISTS field_areas (
  id text PRIMARY KEY,
  section_code text NOT NULL,
  division text NOT NULL,
  zone text NOT NULL,
  name text NOT NULL,
  center_lat double precision NOT NULL,
  center_lon double precision NOT NULL,
  boundary geometry(Polygon, 4326),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_field_areas_section ON field_areas(section_code);
CREATE INDEX IF NOT EXISTS idx_field_areas_boundary ON field_areas USING GIST(boundary);

CREATE TABLE IF NOT EXISTS supervisor_area_assignments (
  id text PRIMARY KEY,
  supervisor_id text NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  field_area_id text NOT NULL REFERENCES field_areas(id) ON DELETE CASCADE,
  authorized_from timestamptz NOT NULL,
  authorized_until timestamptz NOT NULL,
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_supervisor_assignments ON supervisor_area_assignments(supervisor_id, active);

-- 3. Ordered Macro Work Steps & Evidence Requirements
CREATE TABLE IF NOT EXISTS work_steps (
  id text PRIMARY KEY,
  task_id text NOT NULL REFERENCES maintenance_tasks(id) ON DELETE CASCADE,
  step_index integer NOT NULL,
  title text NOT NULL,
  description text NOT NULL DEFAULT '',
  requires_photo boolean NOT NULL DEFAULT true,
  requires_video boolean NOT NULL DEFAULT false,
  target_lat double precision NOT NULL,
  target_lon double precision NOT NULL,
  target_radius_m double precision NOT NULL DEFAULT 100.0,
  status text NOT NULL DEFAULT 'READY' CHECK (status IN (
    'READY', 'STARTED', 'IN_PROGRESS', 'PAUSED', 'DELAYED',
    'CANNOT_COMPLETE', 'COMPLETED_PENDING_EVIDENCE', 'COMPLETED'
  )),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(task_id, step_index)
);

CREATE INDEX IF NOT EXISTS idx_work_steps_task ON work_steps(task_id, step_index);

CREATE TABLE IF NOT EXISTS evidence_requirements (
  id text PRIMARY KEY,
  step_id text REFERENCES work_steps(id) ON DELETE CASCADE,
  task_id text REFERENCES maintenance_tasks(id) ON DELETE CASCADE,
  kind text NOT NULL CHECK (kind IN ('PHOTO', 'VIDEO')),
  required boolean NOT NULL DEFAULT true,
  min_duration_s integer,
  max_duration_s integer DEFAULT 90,
  target_radius_m double precision NOT NULL DEFAULT 100.0,
  target_accuracy_m double precision NOT NULL DEFAULT 50.0
);

-- 4. Evidence Items & Spatial Location Samples
CREATE TABLE IF NOT EXISTS evidence_items (
  id text PRIMARY KEY, -- UUIDv7
  task_id text NOT NULL REFERENCES maintenance_tasks(id),
  step_id text REFERENCES work_steps(id),
  supervisor_id text NOT NULL REFERENCES users(id),
  kind text NOT NULL CHECK (kind IN ('PHOTO', 'VIDEO')),
  status text NOT NULL DEFAULT 'DRAFT' CHECK (status IN (
    'DRAFT', 'UPLOAD_PENDING', 'UPLOADING', 'VERIFYING',
    'VERIFIED', 'FLAGGED_REVIEW', 'ACCEPTED_EXCEPTION', 'REJECTED'
  )),
  original_storage_key text,
  proof_storage_key text,
  original_sha256 char(64) CHECK (original_sha256 IS NULL OR original_sha256 ~ '^[0-9a-f]{64}$'),
  proof_sha256 char(64) CHECK (proof_sha256 IS NULL OR proof_sha256 ~ '^[0-9a-f]{64}$'),
  original_size_bytes bigint,
  proof_size_bytes bigint,
  capture_time_utc timestamptz NOT NULL,
  device_time_utc timestamptz NOT NULL,
  start_latitude double precision NOT NULL,
  start_longitude double precision NOT NULL,
  start_geom geometry(Point, 4326),
  gps_accuracy_m double precision NOT NULL,
  distance_to_target_m double precision,
  geo_verdict text NOT NULL CHECK (geo_verdict IN (
    'WITHIN_RADIUS', 'OUTSIDE_RADIUS', 'LOW_ACCURACY', 'NO_FIX', 'MOCKED_LOCATION', 'CLOCK_DRIFT'
  )),
  exception_reason text,
  reviewer_id text REFERENCES users(id),
  review_notes text,
  reviewed_at timestamptz,
  canonical_manifest jsonb,
  ed25519_signature text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_evidence_task_step ON evidence_items(task_id, step_id);
CREATE INDEX IF NOT EXISTS idx_evidence_status ON evidence_items(status);
CREATE INDEX IF NOT EXISTS idx_evidence_supervisor ON evidence_items(supervisor_id);
CREATE INDEX IF NOT EXISTS idx_evidence_start_geom ON evidence_items USING GIST(start_geom);

-- Trigger to auto-update start_geom point from lat/lon
CREATE OR REPLACE FUNCTION set_evidence_start_geom()
RETURNS trigger AS $$
BEGIN
  NEW.start_geom := ST_SetSRID(ST_MakePoint(NEW.start_longitude, NEW.start_latitude), 4326);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_evidence_items_geom ON evidence_items;
CREATE TRIGGER trg_evidence_items_geom
BEFORE INSERT OR UPDATE OF start_latitude, start_longitude ON evidence_items
FOR EACH ROW EXECUTE FUNCTION set_evidence_start_geom();

CREATE TABLE IF NOT EXISTS evidence_location_samples (
  id bigserial PRIMARY KEY,
  evidence_id text NOT NULL REFERENCES evidence_items(id) ON DELETE CASCADE,
  sample_index integer NOT NULL,
  timestamp_utc timestamptz NOT NULL,
  latitude double precision NOT NULL,
  longitude double precision NOT NULL,
  geom geometry(Point, 4326),
  altitude_m double precision,
  accuracy_m double precision NOT NULL,
  speed_mps double precision,
  bearing_deg double precision,
  is_mocked boolean NOT NULL DEFAULT false,
  UNIQUE(evidence_id, sample_index)
);

CREATE INDEX IF NOT EXISTS idx_samples_evidence ON evidence_location_samples(evidence_id);
CREATE INDEX IF NOT EXISTS idx_samples_geom ON evidence_location_samples USING GIST(geom);

-- 5. Resilient Multipart Uploads
CREATE TABLE IF NOT EXISTS upload_sessions (
  id text PRIMARY KEY,
  evidence_id text NOT NULL REFERENCES evidence_items(id) ON DELETE CASCADE,
  storage_kind text NOT NULL CHECK (storage_kind IN ('ORIGINAL', 'PROOF')),
  storage_key text NOT NULL,
  total_bytes bigint NOT NULL,
  part_size_bytes integer NOT NULL DEFAULT 8388608,
  total_parts integer NOT NULL,
  status text NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'COMPLETED', 'ABORTED')),
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS upload_parts (
  id bigserial PRIMARY KEY,
  session_id text NOT NULL REFERENCES upload_sessions(id) ON DELETE CASCADE,
  part_number integer NOT NULL,
  etag text NOT NULL,
  sha256 char(64),
  size_bytes bigint NOT NULL,
  uploaded_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(session_id, part_number)
);

-- 6. Verification Pipeline Jobs
CREATE TABLE IF NOT EXISTS verification_jobs (
  id text PRIMARY KEY,
  evidence_id text NOT NULL REFERENCES evidence_items(id) ON DELETE CASCADE,
  status text NOT NULL DEFAULT 'QUEUED' CHECK (status IN ('QUEUED', 'CLAIMED', 'COMPLETED', 'FAILED')),
  attempts integer NOT NULL DEFAULT 0,
  error_message text,
  claimed_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_verification_status ON verification_jobs(status, created_at);

-- 7. Emergency Reports
CREATE TABLE IF NOT EXISTS emergency_reports (
  id text PRIMARY KEY,
  supervisor_id text NOT NULL REFERENCES users(id),
  section_code text NOT NULL,
  km_post text NOT NULL,
  latitude double precision NOT NULL,
  longitude double precision NOT NULL,
  geom geometry(Point, 4326),
  severity text NOT NULL CHECK (severity IN ('IMR', 'IMRW', 'OBS', 'OMS_PEAK_HIGH', 'POINT_SLACK_DETECTION', 'OHE_DROPPING_FAULT')),
  hazard_type text NOT NULL,
  description text NOT NULL,
  photo_evidence_id text REFERENCES evidence_items(id),
  status text NOT NULL DEFAULT 'OPEN',
  reported_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_emergency_reports_section ON emergency_reports(section_code);
CREATE INDEX IF NOT EXISTS idx_emergency_reports_geom ON emergency_reports USING GIST(geom);
