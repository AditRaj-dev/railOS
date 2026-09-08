from dataclasses import FrozenInstanceError
import json
from pathlib import Path

import pytest

from integrations.geospatial.manifest import ManifestError, SnapshotManifest, sha256_file

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "datasets" / "geospatial" / "fixtures" / "overpass-bounded-synthetic.json"
MANIFEST = FIXTURE.with_suffix(".manifest.json")


def test_snapshot_manifest_carries_required_audit_metadata_and_verifies_checksum():
    manifest = SnapshotManifest.load(MANIFEST)

    manifest.verify_payload(FIXTURE)
    assert manifest.source_uri.startswith("fixture://")
    assert manifest.source_type == "overpass-json"
    assert manifest.retrieved_at
    assert manifest.source_timestamp
    assert manifest.licence_name
    assert manifest.attribution
    assert manifest.bbox == (77.43, 28.55, 77.58, 28.70)
    assert manifest.query.startswith("[out:json]")
    assert manifest.parser_version
    assert manifest.synthetic is True
    assert len(manifest.provenance_label) <= 100
    assert sha256_file(FIXTURE) == manifest.sha256


def test_snapshot_manifest_is_frozen():
    manifest = SnapshotManifest.load(MANIFEST)

    with pytest.raises(FrozenInstanceError):
        manifest.snapshot_id = "changed"  # type: ignore[misc]


def test_snapshot_checksum_mismatch_fails_closed(tmp_path):
    changed = tmp_path / "source.json"
    changed.write_text(FIXTURE.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    with pytest.raises(ManifestError, match="checksum mismatch"):
        SnapshotManifest.load(MANIFEST).verify_payload(changed)


def test_manifest_rejects_an_unbounded_or_naive_timestamp():
    raw = json.loads(MANIFEST.read_text(encoding="utf-8"))
    raw["bbox"] = [77.5, 28.7, 77.4, 28.5]
    raw["retrievedAt"] = "2026-09-08T09:30:00"

    with pytest.raises(ManifestError):
        SnapshotManifest.from_dict(raw)
