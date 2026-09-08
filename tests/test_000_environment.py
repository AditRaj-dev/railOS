"""Shared import-path bootstrap for standard-library unittest discovery."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for relative in (
    "apps/api", "packages/railos_model", "packages/railos_data",
    "packages/risk_engine", "packages/opportunity_engine",
    "packages/bundling_engine", "packages/optimizer", "packages/simulator",
    "packages/shared",
):
    sys.path.insert(0, str(ROOT / relative))

class EnvironmentTests(unittest.TestCase):
    def test_workspace_root_exists(self):
        self.assertTrue(ROOT.is_dir())
