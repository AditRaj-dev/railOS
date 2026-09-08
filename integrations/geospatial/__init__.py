"""Reproducible railway-geometry ingestion for RailOS.

The package deliberately keeps community geometry separate from official
operational identifiers.  Its public API is dependency-free so fixtures and
snapshot verification can run in an offline test environment.
"""

from .manifest import PARSER_VERSION, SnapshotManifest, sha256_file
from .normalize import NormalizationError, normalize_overpass, write_outputs

__all__ = [
    "NormalizationError",
    "PARSER_VERSION",
    "SnapshotManifest",
    "normalize_overpass",
    "sha256_file",
    "write_outputs",
]
