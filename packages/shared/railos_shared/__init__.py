"""Shared API contracts and provenance primitives."""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

@dataclass(frozen=True)
class Provenance:
    source: str
    source_version: str
    cursor: str
    scenario: str
    ingested_at: datetime
    synthetic: bool = True

class SourceAdapter(Protocol):
    provenance: Provenance
    def health(self) -> dict[str, Any]: ...
    def fetch(self, entity: str) -> list[dict[str, Any]]: ...
    def normalize(self, payload: dict[str, Any]) -> dict[str, Any]: ...
    def dedupe_key(self, payload: dict[str, Any]) -> str: ...
