"""Seed intermediate stations and per-track segments into ``datasets/network.json``.

The curated catalogue carried only the four section end stations and one
straight two-point line per section, so the map had nothing between Ghaziabad
and Aligarh and no way to draw the UP and DOWN roads apart. This fills both in
deterministically: halt stations interpolated along each section by chainage,
and one segment per track offset a few metres either side of the section
centreline.

Everything here is synthetic, like the rest of the catalogue -- plausible
halt names and codes for the corridor, not an Indian Railways GIS extract.
Re-running is idempotent: seeded ids are rebuilt from scratch each time.

    python -m railos_data.seed_network [datasets/network.json]
"""

from __future__ import annotations

import json
import pathlib
import sys

#: Halts between the section end stations, as (code, name, fraction along the
#: section from its start). Chainage fractions, not surveyed positions.
INTERMEDIATE_STATIONS: dict[str, list[tuple[str, str, float]]] = {
    "SEC_GZB_DER": [
        ("CPJ", "Chipiyana Buzurg", 0.30),
        ("MRPT", "Maripat", 0.62),
    ],
    "SEC_DER_KRJ": [
        ("BRKI", "Boraki", 0.28),
        ("AJR", "Ajaibpur", 0.66),
    ],
    "SEC_KRJ_SMQ": [
        ("DNW", "Danwar", 0.34),
        ("VZR", "Vajidpur", 0.70),
    ],
    "SEC_SMQ_ALJN": [
        ("MHRB", "Mahrawal", 0.32),
        ("SSB", "Sasni Bypass Halt", 0.68),
    ],
}

#: Tracks get their own line, offset perpendicular to the centreline so both
#: roads are visible at map zoom. Degrees; ~55 m at this latitude.
TRACK_OFFSET_DEGREES = 0.0005


def _interpolate(start: list[float], end: list[float], fraction: float) -> list[float]:
    return [
        round(start[0] + (end[0] - start[0]) * fraction, 6),
        round(start[1] + (end[1] - start[1]) * fraction, 6),
    ]


def _offset(line: list[list[float]], amount: float) -> list[list[float]]:
    """Shift a line sideways by ``amount`` degrees, perpendicular to itself."""
    (x0, y0), (x1, y1) = line[0], line[-1]
    dx, dy = x1 - x0, y1 - y0
    length = (dx * dx + dy * dy) ** 0.5 or 1.0
    nx, ny = -dy / length, dx / length
    return [[round(x + nx * amount, 6), round(y + ny * amount, 6)] for x, y in line]


def seed(path: pathlib.Path) -> dict[str, int]:
    catalogue = json.loads(path.read_text(encoding="utf-8"))
    sections = {section["sectionId"]: section for section in catalogue["sections"]}

    # Drop anything a previous run added, so this stays idempotent.
    catalogue["stations"] = [s for s in catalogue["stations"] if not s.get("seeded")]
    catalogue["segments"] = [s for s in catalogue["segments"] if not s.get("seeded")]

    added_stations = 0
    for section_id, halts in INTERMEDIATE_STATIONS.items():
        section = sections.get(section_id)
        if section is None:
            continue
        line = section["geometry"]["coordinates"]
        start, end = line[0], line[-1]
        for code, name, fraction in halts:
            catalogue["stations"].append({
                "stationId": f"STN_{code}",
                "code": code,
                "name": name,
                "sectionIds": [section_id],
                "geometry": {"type": "Point", "coordinates": _interpolate(start, end, fraction)},
                "planningEnabled": section.get("planningEnabled", False),
                "seeded": True,
            })
            added_stations += 1

        # Redraw the section through its halts so the line follows the road
        # rather than cutting straight across it.
        section["geometry"]["coordinates"] = (
            [start]
            + [_interpolate(start, end, fraction) for _, _, fraction in halts]
            + [end]
        )

    added_segments = 0
    for section in catalogue["sections"]:
        if not section.get("planningEnabled"):
            continue
        line = section["geometry"]["coordinates"]
        for index, track in enumerate(section.get("tracks", [])):
            sign = 1 if index % 2 == 0 else -1
            catalogue["segments"].append({
                "segmentId": f"SEG_{section['sectionId'].removeprefix('SEC_')}_{track}",
                "sectionId": section["sectionId"],
                "divisionId": section["divisionId"],
                "zoneId": section["zoneId"],
                "track": track,
                "geometry": {"type": "LineString", "coordinates": _offset(line, sign * TRACK_OFFSET_DEGREES)},
                "riskScore": min(100, section["metrics"]["maintenanceDebt"]),
                "maintenancePressure": min(100, section["metrics"]["pendingMaintenanceCount"] * 10),
                "trafficPressure": section["metrics"]["trafficPressure"],
                "activeBlock": False,
                "planningEnabled": True,
                "seeded": True,
            })
            added_segments += 1

    path.write_text(json.dumps(catalogue, indent=2) + "\n", encoding="utf-8")
    return {
        "stations": len(catalogue["stations"]),
        "stationsAdded": added_stations,
        "segments": len(catalogue["segments"]),
        "segmentsAdded": added_segments,
    }


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    path = pathlib.Path(argv[0]) if argv else pathlib.Path("datasets/network.json")
    counts = seed(path)
    print(
        f"{path}: {counts['stationsAdded']} halts seeded ({counts['stations']} stations), "
        f"{counts['segmentsAdded']} track segments seeded ({counts['segments']} segments)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
