from __future__ import annotations
import hashlib
from datetime import datetime, timezone
from typing import Any, Protocol
try:
    from railos_shared import Provenance
except ImportError:  # direct API startup without monorepo package path
    from dataclasses import dataclass
    @dataclass(frozen=True)
    class Provenance:
        source: str; source_version: str; cursor: str; scenario: str; ingested_at: Any; synthetic: bool = True

class SyntheticAdapter:
    def __init__(self, name: str, version: str = "demo-1"):
        self.name=name; self.provenance=Provenance(name,version,"0","GZB_ALJN_DEMO",datetime.now(timezone.utc),True)
    def health(self): return {"source":self.name,"sourceVersion":self.provenance.source_version,"status":"SIMULATED","live":False,"synthetic":True}
    def fetch(self, entity): return [{"id":f"{self.name}-{entity}-001","entity":entity,"source":self.name,"synthetic":True}]
    def normalize(self,payload): return {**payload,"provenance":self.provenance.__dict__}
    def dedupe_key(self,payload): return hashlib.sha256(f"{self.name}:{payload.get('id')}".encode()).hexdigest()

class TMSAdapter(SyntheticAdapter): pass
class SMMSAdapter(SyntheticAdapter): pass
class TDMSAdapter(SyntheticAdapter): pass
class COAAdapter(SyntheticAdapter): pass
class BDMSAdapter(SyntheticAdapter): pass
class TimetableAdapter(SyntheticAdapter): pass
class GoodsAdapter(SyntheticAdapter): pass

class SourceAdapter(Protocol):
    name: str
    provenance: Provenance
    def health(self) -> dict[str, Any]: ...
    def fetch(self, entity: str) -> list[dict[str, Any]]: ...
    def normalize(self, payload: dict[str, Any]) -> dict[str, Any]: ...
    def dedupe_key(self, payload: dict[str, Any]) -> str: ...
