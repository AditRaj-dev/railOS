"""Make monorepo packages importable for both unittest and pytest discovery."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for relative in (
    "apps/api", "packages/railos_model", "packages/railos_data",
    "packages/risk_engine", "packages/opportunity_engine",
    "packages/bundling_engine", "packages/optimizer", "packages/simulator",
    "packages/shared",
):
    path = str(ROOT / relative)
    if path not in sys.path:
        sys.path.insert(0, path)
