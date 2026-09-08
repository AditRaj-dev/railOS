"""Weight loading. Weights live in config/*.yaml, never inline in engine code."""

import functools
import pathlib

import yaml

DEFAULT_CONFIG_DIR = pathlib.Path("config")


@functools.lru_cache(maxsize=8)
def load_weights(path: str | pathlib.Path = DEFAULT_CONFIG_DIR / "weights.yaml") -> dict:
    cfg = yaml.safe_load(pathlib.Path(path).read_text(encoding="utf-8"))
    total = sum(cfg["priority"].values())
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"priority weights must sum to 1.0, got {total}")
    return cfg
