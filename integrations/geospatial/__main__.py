"""Command-line entry point for offline snapshot verification and normalization."""

from __future__ import annotations

import argparse

from .manifest import SnapshotManifest
from .normalize import write_outputs


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m integrations.geospatial")
    commands = parser.add_subparsers(dest="command", required=True)

    verify = commands.add_parser("verify", help="verify source metadata and SHA-256")
    verify.add_argument("--source", required=True)
    verify.add_argument("--manifest", required=True)

    normalize = commands.add_parser(
        "normalize-overpass", help="write deterministic GeoJSON and seed JSON"
    )
    normalize.add_argument("--source", required=True)
    normalize.add_argument("--manifest", required=True)
    normalize.add_argument("--output-dir", required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    manifest = SnapshotManifest.load(args.manifest)
    manifest.verify_payload(args.source)
    if args.command == "verify":
        print(f"verified {manifest.snapshot_id} {manifest.sha256}")
        return 0
    geojson, seed = write_outputs(args.source, args.manifest, args.output_dir)
    print(f"wrote {geojson}")
    print(f"wrote {seed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
