from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "database" / "migrations" / "004_geospatial_ingestion.sql"


def test_geospatial_migration_is_postgis_ready_and_indexed():
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    assert "create extension if not exists postgis" in sql
    assert "geometry(point, 4326)" in sql
    assert "geometry(linestring, 4326)" in sql
    assert "using gist(geometry)" in sql
    assert "geospatial_stations(source_element_type, source_id)" in sql
    assert "geospatial_track_segments(source_element_type, source_id)" in sql


def test_snapshot_schema_is_append_only_and_conflation_is_explicit():
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    assert "before update or delete on geospatial_source_snapshots" in sql
    assert "raise exception 'geospatial source snapshots are immutable" in sql
    assert "create table if not exists geospatial_conflation_records" in sql
    assert "confidence numeric(5,4)" in sql
    assert "status in ('pending', 'matched', 'rejected')" in sql
