"""Export JSON Schema for every contract. This is the handoff artifact for the
API/DB agent and the UI agent -- they generate their types from schemas/, not from
reading this Python.

    python -m railos_model.export_schemas [outdir]
"""

import json
import pathlib
import sys

from pydantic import BaseModel

from . import models

OUT_DEFAULT = pathlib.Path("schemas")


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    out = pathlib.Path(argv[0]) if argv else OUT_DEFAULT
    out.mkdir(parents=True, exist_ok=True)
    written = 0
    for name in dir(models):
        obj = getattr(models, name)
        if isinstance(obj, type) and issubclass(obj, BaseModel) and obj is not BaseModel:
            (out / f"{name}.schema.json").write_text(
                json.dumps(obj.model_json_schema(), indent=2), encoding="utf-8"
            )
            written += 1
    print(f"wrote {written} schemas to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
