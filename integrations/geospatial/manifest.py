"""Immutable source-snapshot metadata and checksum verification."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Mapping

PARSER_VERSION = "railos-geospatial-overpass/1.0.0"
SUPPORTED_SOURCE_TYPES = frozenset({"overpass-json", "osm-pbf"})
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ManifestError(ValueError):
    """Raised when snapshot metadata is incomplete or inconsistent."""


def sha256_file(path: str | Path) -> str:
    """Return the SHA-256 digest of a file without loading it all in memory."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _timestamp(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ManifestError(f"{field} must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ManifestError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ManifestError(f"{field} must include a UTC offset")
    return value


def _bbox(value: Any) -> tuple[float, float, float, float]:
    if not isinstance(value, list) or len(value) != 4:
        raise ManifestError("bbox must contain [west, south, east, north]")
    if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value):
        raise ManifestError("bbox coordinates must be numbers")
    west, south, east, north = (float(item) for item in value)
    if not all(math.isfinite(item) for item in (west, south, east, north)):
        raise ManifestError("bbox coordinates must be finite")
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ManifestError("bbox must be ordered and within WGS84 bounds")
    return west, south, east, north


def _required_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ManifestError(f"{field} must be an object")
    return value


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"{field} must be a non-empty string")
    return value


@dataclass(frozen=True, slots=True)
class SnapshotManifest:
    """Validated, immutable metadata for one source payload."""

    schema_version: str
    snapshot_id: str
    source_uri: str
    source_type: str
    retrieved_at: str
    source_timestamp: str
    sha256: str
    licence_name: str
    licence_url: str
    attribution: str
    bbox: tuple[float, float, float, float]
    query: str
    parser_version: str
    synthetic: bool
    provenance_label: str

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "SnapshotManifest":
        source = _required_mapping(raw.get("source"), "source")
        licence = _required_mapping(raw.get("licence"), "licence")
        source_type = _required_text(source.get("type"), "source.type")
        if source_type not in SUPPORTED_SOURCE_TYPES:
            choices = ", ".join(sorted(SUPPORTED_SOURCE_TYPES))
            raise ManifestError(f"source.type must be one of: {choices}")
        checksum = _required_text(raw.get("sha256"), "sha256")
        if not _SHA256_PATTERN.fullmatch(checksum):
            raise ManifestError("sha256 must contain 64 lowercase hexadecimal characters")
        synthetic = raw.get("synthetic")
        if not isinstance(synthetic, bool):
            raise ManifestError("synthetic must be a boolean")
        label = _required_text(raw.get("provenanceLabel"), "provenanceLabel")
        if len(label) > 100:
            raise ManifestError("provenanceLabel must be at most 100 characters")
        return cls(
            schema_version=_required_text(raw.get("schemaVersion"), "schemaVersion"),
            snapshot_id=_required_text(raw.get("snapshotId"), "snapshotId"),
            source_uri=_required_text(source.get("uri"), "source.uri"),
            source_type=source_type,
            retrieved_at=_timestamp(raw.get("retrievedAt"), "retrievedAt"),
            source_timestamp=_timestamp(raw.get("sourceTimestamp"), "sourceTimestamp"),
            sha256=checksum,
            licence_name=_required_text(licence.get("name"), "licence.name"),
            licence_url=_required_text(licence.get("url"), "licence.url"),
            attribution=_required_text(licence.get("attribution"), "licence.attribution"),
            bbox=_bbox(raw.get("bbox")),
            query=_required_text(raw.get("query"), "query"),
            parser_version=_required_text(raw.get("parserVersion"), "parserVersion"),
            synthetic=synthetic,
            provenance_label=label,
        )

    @classmethod
    def load(cls, path: str | Path) -> "SnapshotManifest":
        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ManifestError(f"manifest is not valid JSON: {exc.msg}") from exc
        if not isinstance(raw, Mapping):
            raise ManifestError("manifest root must be an object")
        return cls.from_dict(raw)

    def verify_payload(self, path: str | Path) -> None:
        actual = sha256_file(path)
        if actual != self.sha256:
            raise ManifestError(
                f"snapshot checksum mismatch: expected {self.sha256}, got {actual}"
            )

    def provenance(self) -> dict[str, Any]:
        """Return compact source context suitable for map features and UI text."""

        return {
            "attribution": self.attribution,
            "label": self.provenance_label,
            "licence": {"name": self.licence_name, "url": self.licence_url},
            "retrievedAt": self.retrieved_at,
            "snapshotId": self.snapshot_id,
            "source": self.source_uri,
            "sourceTimestamp": self.source_timestamp,
            "sourceType": self.source_type,
            "synthetic": self.synthetic,
        }
