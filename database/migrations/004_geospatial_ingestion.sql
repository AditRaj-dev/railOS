-- Reproducible community-geometry ingestion. Geometry is not official
-- Indian Railways operational or engineering data.
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS geospatial_source_snapshots (
  snapshot_id text PRIMARY KEY,
  schema_version text NOT NULL,
  source_uri text NOT NULL,
  source_type text NOT NULL CHECK (source_type IN ('overpass-json', 'osm-pbf')),
  retrieved_at timestamptz NOT NULL,
  source_timestamp timestamptz NOT NULL,
  sha256 char(64) NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
  licence_name text NOT NULL,
  licence_url text NOT NULL,
  attribution text NOT NULL,
  west double precision NOT NULL CHECK (west >= -180 AND west <= 180),
  south double precision NOT NULL CHECK (south >= -90 AND south <= 90),
  east double precision NOT NULL CHECK (east >= -180 AND east <= 180),
  north double precision NOT NULL CHECK (north >= -90 AND north <= 90),
  query_text text NOT NULL,
  parser_version text NOT NULL,
  synthetic boolean NOT NULL,
  provenance_label varchar(100) NOT NULL,
  manifest jsonb NOT NULL,
  bbox geometry(Polygon, 4326) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (west < east AND south < north),
  CHECK (ST_SRID(bbox) = 4326)
);

CREATE INDEX IF NOT EXISTS idx_geospatial_snapshots_source_time
  ON geospatial_source_snapshots(source_type, source_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_geospatial_snapshots_sha256
  ON geospatial_source_snapshots(sha256);
CREATE INDEX IF NOT EXISTS idx_geospatial_snapshots_bbox
  ON geospatial_source_snapshots USING GIST(bbox);

-- A captured payload and its manifest are append-only. Corrections create a
-- new snapshot_id instead of mutating provenance used by existing features.
CREATE OR REPLACE FUNCTION reject_geospatial_snapshot_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION 'geospatial source snapshots are immutable; create a new snapshot';
END;
$$;

DROP TRIGGER IF EXISTS geospatial_source_snapshots_immutable
  ON geospatial_source_snapshots;
CREATE TRIGGER geospatial_source_snapshots_immutable
BEFORE UPDATE OR DELETE ON geospatial_source_snapshots
FOR EACH ROW EXECUTE FUNCTION reject_geospatial_snapshot_mutation();

CREATE TABLE IF NOT EXISTS geospatial_stations (
  station_id text PRIMARY KEY,
  snapshot_id text NOT NULL REFERENCES geospatial_source_snapshots(snapshot_id),
  source_element_type text NOT NULL CHECK (source_element_type = 'node'),
  source_id bigint NOT NULL CHECK (source_id > 0),
  station_kind text NOT NULL CHECK (station_kind IN ('station', 'halt')),
  name text,
  osm_ref text,
  osm_tags jsonb NOT NULL DEFAULT '{}'::jsonb,
  geometry geometry(Point, 4326) NOT NULL,
  synthetic boolean NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(snapshot_id, source_element_type, source_id),
  CHECK (ST_SRID(geometry) = 4326),
  CHECK (ST_IsValid(geometry))
);

CREATE INDEX IF NOT EXISTS idx_geospatial_stations_geometry
  ON geospatial_stations USING GIST(geometry);
CREATE INDEX IF NOT EXISTS idx_geospatial_stations_source
  ON geospatial_stations(source_element_type, source_id);
CREATE INDEX IF NOT EXISTS idx_geospatial_stations_osm_ref
  ON geospatial_stations(osm_ref) WHERE osm_ref IS NOT NULL;

CREATE TABLE IF NOT EXISTS geospatial_track_segments (
  track_id text PRIMARY KEY,
  snapshot_id text NOT NULL REFERENCES geospatial_source_snapshots(snapshot_id),
  source_element_type text NOT NULL CHECK (source_element_type = 'way'),
  source_id bigint NOT NULL CHECK (source_id > 0),
  railway_class text NOT NULL CHECK (railway_class = 'rail'),
  name text,
  osm_tags jsonb NOT NULL DEFAULT '{}'::jsonb,
  geometry geometry(LineString, 4326) NOT NULL,
  synthetic boolean NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(snapshot_id, source_element_type, source_id),
  CHECK (ST_SRID(geometry) = 4326),
  CHECK (ST_IsValid(geometry)),
  CHECK (ST_NPoints(geometry) >= 2)
);

CREATE INDEX IF NOT EXISTS idx_geospatial_track_segments_geometry
  ON geospatial_track_segments USING GIST(geometry);
CREATE INDEX IF NOT EXISTS idx_geospatial_track_segments_source
  ON geospatial_track_segments(source_element_type, source_id);
CREATE INDEX IF NOT EXISTS idx_geospatial_track_segments_snapshot
  ON geospatial_track_segments(snapshot_id);

CREATE TABLE IF NOT EXISTS geospatial_conflation_records (
  conflation_id bigserial PRIMARY KEY,
  snapshot_id text NOT NULL REFERENCES geospatial_source_snapshots(snapshot_id),
  source_entity_type text NOT NULL CHECK (source_entity_type IN ('STATION', 'TRACK')),
  source_entity_id text NOT NULL,
  candidate_entity_type text NOT NULL,
  candidate_entity_id text NOT NULL,
  status text NOT NULL DEFAULT 'PENDING'
    CHECK (status IN ('PENDING', 'MATCHED', 'REJECTED')),
  confidence numeric(5,4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  method text NOT NULL,
  evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
  reviewed_by text,
  reviewed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(snapshot_id, source_entity_type, source_entity_id, candidate_entity_type, candidate_entity_id),
  CHECK ((status = 'PENDING' AND reviewed_at IS NULL) OR status <> 'PENDING')
);

CREATE INDEX IF NOT EXISTS idx_geospatial_conflation_source
  ON geospatial_conflation_records(source_entity_type, source_entity_id);
CREATE INDEX IF NOT EXISTS idx_geospatial_conflation_candidate
  ON geospatial_conflation_records(candidate_entity_type, candidate_entity_id);
CREATE INDEX IF NOT EXISTS idx_geospatial_conflation_status_confidence
  ON geospatial_conflation_records(status, confidence DESC);
