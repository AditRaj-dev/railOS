"""Normalize a bounded Overpass JSON snapshot into deterministic RailOS data."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from .manifest import ManifestError, PARSER_VERSION, SnapshotManifest


class NormalizationError(ValueError):
    """Raised when selected railway geometry cannot be normalized safely."""


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize JSON deterministically for checksums and reproducible builds."""

    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _osm_id(value: Any, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise NormalizationError(f"{context} must have a positive integer OSM id")
    return value


def _tags(value: Any, context: str) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise NormalizationError(f"{context} tags must be an object")
    normalized: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not isinstance(item, str):
            raise NormalizationError(f"{context} tags must contain string keys and values")
        normalized[key] = item
    return dict(sorted(normalized.items()))


def _coordinate(lon: Any, lat: Any, context: str) -> list[float]:
    values = (lon, lat)
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in values):
        raise NormalizationError(f"{context} coordinate must contain numbers")
    longitude, latitude = float(lon), float(lat)
    if not math.isfinite(longitude) or not math.isfinite(latitude):
        raise NormalizationError(f"{context} coordinate must be finite")
    if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
        raise NormalizationError(f"{context} coordinate is outside WGS84 bounds")
    return [longitude, latitude]


def _inside_bbox(coordinate: Sequence[float], bbox: Sequence[float]) -> bool:
    west, south, east, north = bbox
    return west <= coordinate[0] <= east and south <= coordinate[1] <= north


def _feature_provenance(manifest: SnapshotManifest) -> dict[str, Any]:
    return manifest.provenance()


def _station_feature(
    element: Mapping[str, Any], manifest: SnapshotManifest
) -> dict[str, Any]:
    osm_id = _osm_id(element.get("id"), "station node")
    coordinate = _coordinate(element.get("lon"), element.get("lat"), f"node/{osm_id}")
    if not _inside_bbox(coordinate, manifest.bbox):
        raise NormalizationError(f"station node/{osm_id} lies outside the snapshot bbox")
    tags = _tags(element.get("tags"), f"node/{osm_id}")
    station_kind = tags.get("railway")
    source_id = f"node/{osm_id}"
    entity_id = f"osm-node-{osm_id}"
    properties: dict[str, Any] = {
        "entityId": entity_id,
        "entityType": "STATION",
        "osmElementType": "node",
        "osmId": osm_id,
        "osmTags": tags,
        "planningEnabled": False,
        "provenance": _feature_provenance(manifest),
        "sourceId": source_id,
        "stationId": entity_id,
        "stationKind": station_kind,
        "synthetic": manifest.synthetic,
    }
    if tags.get("name"):
        properties["name"] = tags["name"]
    if tags.get("ref"):
        properties["osmRef"] = tags["ref"]
    return {
        "geometry": {"coordinates": coordinate, "type": "Point"},
        "id": entity_id,
        "properties": properties,
        "type": "Feature",
    }


def _track_feature(
    element: Mapping[str, Any],
    nodes: Mapping[int, list[float]],
    manifest: SnapshotManifest,
) -> dict[str, Any]:
    osm_id = _osm_id(element.get("id"), "rail way")
    node_refs = element.get("nodes")
    if not isinstance(node_refs, list) or len(node_refs) < 2:
        raise NormalizationError(f"way/{osm_id} must reference at least two nodes")
    coordinates: list[list[float]] = []
    for raw_ref in node_refs:
        ref = _osm_id(raw_ref, f"way/{osm_id} node reference")
        if ref not in nodes:
            raise NormalizationError(f"way/{osm_id} references missing or invalid node/{ref}")
        coordinates.append(nodes[ref])
    if len({tuple(coordinate) for coordinate in coordinates}) < 2:
        raise NormalizationError(f"way/{osm_id} must contain at least two distinct coordinates")
    tags = _tags(element.get("tags"), f"way/{osm_id}")
    source_id = f"way/{osm_id}"
    entity_id = f"osm-way-{osm_id}"
    properties: dict[str, Any] = {
        "entityId": entity_id,
        "entityType": "TRACK",
        "osmElementType": "way",
        "osmId": osm_id,
        "osmTags": tags,
        "planningEnabled": False,
        "provenance": _feature_provenance(manifest),
        "railway": "rail",
        "sourceId": source_id,
        "synthetic": manifest.synthetic,
        "trackId": entity_id,
    }
    if tags.get("name"):
        properties["name"] = tags["name"]
    return {
        "geometry": {"coordinates": coordinates, "type": "LineString"},
        "id": entity_id,
        "properties": properties,
        "type": "Feature",
    }


def _seed_record(feature: Mapping[str, Any]) -> dict[str, Any]:
    return {
        **dict(feature["properties"]),
        "geometry": dict(feature["geometry"]),
    }


def normalize_overpass(
    payload: Mapping[str, Any], manifest: SnapshotManifest
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a GeoJSON collection and RailOS seed object.

    Input order is irrelevant. Only ``railway=rail`` ways and
    ``railway=station|halt`` nodes become features. Relations and other railway
    classes remain in the immutable source snapshot for future parser versions.
    """

    if manifest.source_type != "overpass-json":
        raise ManifestError("this normalizer requires source.type=overpass-json")
    if manifest.parser_version != PARSER_VERSION:
        raise ManifestError(
            f"parser version mismatch: manifest has {manifest.parser_version}, "
            f"runtime is {PARSER_VERSION}"
        )
    elements = payload.get("elements")
    if not isinstance(elements, list):
        raise NormalizationError("Overpass payload must contain an elements array")

    nodes: dict[int, list[float]] = {}
    indexed: list[Mapping[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for raw in elements:
        if not isinstance(raw, Mapping):
            raise NormalizationError("every Overpass element must be an object")
        element_type = raw.get("type")
        if element_type not in {"node", "way", "relation"}:
            continue
        osm_id = _osm_id(raw.get("id"), f"{element_type} element")
        key = (element_type, osm_id)
        if key in seen:
            raise NormalizationError(f"duplicate Overpass element {element_type}/{osm_id}")
        seen.add(key)
        indexed.append(raw)
        if element_type == "node":
            try:
                nodes[osm_id] = _coordinate(raw.get("lon"), raw.get("lat"), f"node/{osm_id}")
            except NormalizationError:
                # Fail only when the invalid node is selected or referenced by a
                # selected railway feature; unrelated source elements are retained.
                pass

    station_elements: list[Mapping[str, Any]] = []
    track_elements: list[Mapping[str, Any]] = []
    for element in indexed:
        tags = _tags(element.get("tags"), f"{element.get('type')}/{element.get('id')}")
        if element.get("type") == "node" and tags.get("railway") in {"station", "halt"}:
            station_elements.append(element)
        elif element.get("type") == "way" and tags.get("railway") == "rail":
            track_elements.append(element)

    tracks = [
        _track_feature(element, nodes, manifest)
        for element in sorted(track_elements, key=lambda item: int(item["id"]))
    ]
    stations = [
        _station_feature(element, manifest)
        for element in sorted(station_elements, key=lambda item: int(item["id"]))
    ]
    provenance = manifest.provenance()
    collection = {
        "bbox": list(manifest.bbox),
        "count": len(tracks) + len(stations),
        "features": tracks + stations,
        "provenance": provenance,
        "synthetic": manifest.synthetic,
        "type": "FeatureCollection",
    }
    seed = {
        "provenance": provenance,
        "schemaVersion": "1.0",
        "stations": [_seed_record(feature) for feature in stations],
        "tracks": [_seed_record(feature) for feature in tracks],
    }
    return collection, seed


def write_outputs(
    source_path: str | Path,
    manifest_path: str | Path,
    output_dir: str | Path,
) -> tuple[Path, Path]:
    """Verify a snapshot, normalize it, and write deterministic output files."""

    source = Path(source_path)
    manifest = SnapshotManifest.load(manifest_path)
    manifest.verify_payload(source)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise NormalizationError(f"source is not valid JSON: {exc.msg}") from exc
    if not isinstance(payload, Mapping):
        raise NormalizationError("Overpass payload root must be an object")
    collection, seed = normalize_overpass(payload, manifest)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    geojson_path = destination / "network.geojson"
    seed_path = destination / "network.seed.json"
    geojson_path.write_bytes(canonical_json_bytes(collection))
    seed_path.write_bytes(canonical_json_bytes(seed))
    return geojson_path, seed_path
