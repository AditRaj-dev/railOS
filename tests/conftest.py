import pathlib

import pytest

from railos_data import load_world

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def world():
    return load_world(ROOT / "datasets")


@pytest.fixture(scope="session")
def plan(world):
    from optimizer import solve

    return solve(world)
