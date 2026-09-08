import copy
import hashlib
import json
from pathlib import Path

import pytest

from integrations.geospatial import SnapshotManifest
from integrations.geospatial.normalize import (
    NormalizationError,
    canonical_json_bytes,
    normalize_overpass,
    write_outputs,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "datasets" / "geospatial" / "fixtures" / "overpass-bounded-synthetic.json"
MANIFEST = FIXTURE.with_suffix(".manifest.json")


def _source():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_normalizer_is_deterministic_and_input_order_independent():
    manifest = SnapshotManifest.load(MANIFEST)
    source = _source()
    reordered = copy.deepcopy(source)
    reordered["elements"].reverse()

    first = normalize_overpass(source, manifest)
    second = normalize_overpass(reordered, manifest)

    assert canonical_json_bytes(first) == canonical_json_bytes(second)
    digest = hashlib.sha256(canonical_json_bytes(first)).hexdigest()
    assert digest == "72d8bd1e40b4f0f652f0051b02b0762d08bd078c8232c27789ff7b56f7743c3f"


def test_normalizer_selects_only_mainline_tracks_and_stations_without_official_claims():
    collection, seed = normalize_overpass(_source(), SnapshotManifest.load(MANIFEST))

    assert collection["type"] == "FeatureCollection"
    assert collection["count"] == 4
    assert [feature["id"] for feature in collection["features"]] == [
        "osm-way-9001",
        "osm-way-9002",
        "osm-node-101",
        "osm-node-102",
    ]
    assert len(seed["tracks"]) == 2
    assert len(seed["stations"]) == 2
    station = seed["stations"][0]
    assert station["osmId"] == 101
    assert station["sourceId"] == "node/101"
    assert station["osmRef"] == "FXJ"
    assert "code" not in station
    assert station["planningEnabled"] is False
    assert station["provenance"]["synthetic"] is True
    assert "not operational" in station["provenance"]["label"]
    assert seed["tracks"][0]["osmTags"]["gauge"] == "1676"


def test_writer_verifies_source_and_emits_stable_outputs(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"

    first_paths = write_outputs(FIXTURE, MANIFEST, first)
    second_paths = write_outputs(FIXTURE, MANIFEST, second)

    assert [path.read_bytes() for path in first_paths] == [
        path.read_bytes() for path in second_paths
    ]
    assert json.loads(first_paths[0].read_text(encoding="utf-8"))["count"] == 4


def test_selected_track_with_missing_node_is_rejected():
    source = _source()
    source["elements"] = [element for element in source["elements"] if element.get("id") != 102]

    with pytest.raises(NormalizationError, match="missing or invalid node/102"):
        normalize_overpass(source, SnapshotManifest.load(MANIFEST))


def test_selected_station_outside_snapshot_bbox_is_rejected():
    source = _source()
    station = next(element for element in source["elements"] if element.get("id") == 101)
    station["lon"] = 80.0

    with pytest.raises(NormalizationError, match="outside the snapshot bbox"):
        normalize_overpass(source, SnapshotManifest.load(MANIFEST))
