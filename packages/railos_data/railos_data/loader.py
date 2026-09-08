"""Load a dataset directory into a ScenarioWorld. Validation happens here, once."""

import json
import pathlib

from railos_model import (
    Asset,
    BlockWindow,
    Corridor,
    Defect,
    Dependency,
    GoodsForecast,
    MaintenanceTask,
    Resource,
    ScenarioWorld,
    TrainMovement,
)

_MODELS = {
    "corridors.json": Corridor,
    "assets.json": Asset,
    "maintenance_tasks.json": MaintenanceTask,
    "defects.json": Defect,
    "train_movements.json": TrainMovement,
    "goods_forecast.json": GoodsForecast,
    "block_windows.json": BlockWindow,
    "resources.json": Resource,
    "dependencies.json": Dependency,
}
_FIELD = {
    "corridors.json": "corridors",
    "assets.json": "assets",
    "maintenance_tasks.json": "tasks",
    "defects.json": "defects",
    "train_movements.json": "trains",
    "goods_forecast.json": "goods",
    "block_windows.json": "windows",
    "resources.json": "resources",
    "dependencies.json": "dependencies",
}

DEFAULT_DIR = pathlib.Path("datasets")


def load_world(path: str | pathlib.Path = DEFAULT_DIR) -> ScenarioWorld:
    root = pathlib.Path(path)
    meta = json.loads((root / "meta.json").read_text(encoding="utf-8"))
    kwargs: dict = {
        "horizonMinutes": meta["horizonMinutes"],
        "horizonStartIso": meta["horizonStartIso"],
    }
    for name, model in _MODELS.items():
        rows = json.loads((root / name).read_text(encoding="utf-8"))
        kwargs[_FIELD[name]] = [model.model_validate(r) for r in rows]
    return ScenarioWorld(**kwargs)
