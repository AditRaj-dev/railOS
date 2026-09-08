"""Load the provenance-labelled regional-pilot map catalogue."""

from __future__ import annotations

import json
import math
import pathlib
from collections.abc import Sequence
from typing import Any

from railos_model import NetworkCatalog


DEFAULT_NETWORK_PATH = pathlib.Path("datasets/network.json")

BBox = tuple[float, float, float, float]
Point = tuple[float, float]


def load_network(path: str | pathlib.Path = DEFAULT_NETWORK_PATH) -> NetworkCatalog:
    source = pathlib.Path(path)
    return NetworkCatalog.model_validate(json.loads(source.read_text(encoding="utf-8")))


def geometry_intersects_bbox(geometry: Any, bbox: BBox) -> bool:
    """Return whether a supported GeoJSON geometry intersects ``bbox``.

    This deliberately has no spatial-database dependency so the deterministic
    in-memory demo API and its tests use correct viewport semantics. Production
    storage can implement the same contract with a spatial index later.
    """

    if hasattr(geometry, "model_dump"):
        geometry = geometry.model_dump(mode="json")
    if not isinstance(geometry, dict):
        return False

    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    try:
        if geometry_type == "Point":
            point = _point(coordinates)
            return point is not None and _point_in_bbox(point, bbox)
        if geometry_type == "LineString":
            return _line_intersects_bbox(coordinates, bbox)
        if geometry_type == "MultiLineString":
            return isinstance(coordinates, Sequence) and any(
                _line_intersects_bbox(line, bbox) for line in coordinates
            )
        if geometry_type == "Polygon":
            return _polygon_intersects_bbox(coordinates, bbox)
        if geometry_type == "MultiPolygon":
            return isinstance(coordinates, Sequence) and any(
                _polygon_intersects_bbox(polygon, bbox) for polygon in coordinates
            )
    except (TypeError, ValueError, IndexError):
        return False
    return False


def _point(value: Any) -> Point | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) < 2:
        return None
    x, y = float(value[0]), float(value[1])
    return (x, y) if math.isfinite(x) and math.isfinite(y) else None


def _point_in_bbox(point: Point, bbox: BBox) -> bool:
    min_x, min_y, max_x, max_y = bbox
    return min_x <= point[0] <= max_x and min_y <= point[1] <= max_y


def _line_intersects_bbox(coordinates: Any, bbox: BBox) -> bool:
    if not isinstance(coordinates, Sequence) or isinstance(coordinates, (str, bytes)):
        return False
    points = [point for value in coordinates if (point := _point(value)) is not None]
    if any(_point_in_bbox(point, bbox) for point in points):
        return True
    return any(_segment_intersects_bbox(start, end, bbox) for start, end in zip(points, points[1:]))


def _segment_intersects_bbox(start: Point, end: Point, bbox: BBox) -> bool:
    """Liang-Barsky line clipping against an axis-aligned rectangle."""

    min_x, min_y, max_x, max_y = bbox
    dx, dy = end[0] - start[0], end[1] - start[1]
    lower, upper = 0.0, 1.0
    for direction, distance in (
        (-dx, start[0] - min_x),
        (dx, max_x - start[0]),
        (-dy, start[1] - min_y),
        (dy, max_y - start[1]),
    ):
        if direction == 0:
            if distance < 0:
                return False
            continue
        ratio = distance / direction
        if direction < 0:
            lower = max(lower, ratio)
        else:
            upper = min(upper, ratio)
        if lower > upper:
            return False
    return True


def _polygon_intersects_bbox(coordinates: Any, bbox: BBox) -> bool:
    if not isinstance(coordinates, Sequence) or isinstance(coordinates, (str, bytes)):
        return False
    rings = [
        [point for value in ring if (point := _point(value)) is not None]
        for ring in coordinates
        if isinstance(ring, Sequence) and not isinstance(ring, (str, bytes))
    ]
    if not rings or len(rings[0]) < 3:
        return False

    for ring in rings:
        if any(_point_in_bbox(point, bbox) for point in ring):
            return True
        closed_ring = ring if ring[0] == ring[-1] else [*ring, ring[0]]
        if any(
            _segment_intersects_bbox(start, end, bbox)
            for start, end in zip(closed_ring, closed_ring[1:])
        ):
            return True

    min_x, min_y, max_x, max_y = bbox
    return any(
        _point_in_polygon(corner, rings)
        for corner in ((min_x, min_y), (min_x, max_y), (max_x, min_y), (max_x, max_y))
    )


def _point_in_polygon(point: Point, rings: list[list[Point]]) -> bool:
    if _point_on_ring(point, rings[0]):
        return True
    if not _point_in_ring(point, rings[0]):
        return False
    for hole in rings[1:]:
        if _point_on_ring(point, hole):
            return True
        if _point_in_ring(point, hole):
            return False
    return True


def _point_on_ring(point: Point, ring: list[Point]) -> bool:
    if len(ring) < 2:
        return False
    closed_ring = ring if ring[0] == ring[-1] else [*ring, ring[0]]
    return any(_point_on_segment(point, start, end) for start, end in zip(closed_ring, closed_ring[1:]))


def _point_on_segment(point: Point, start: Point, end: Point) -> bool:
    cross = (point[1] - start[1]) * (end[0] - start[0]) - (point[0] - start[0]) * (end[1] - start[1])
    if not math.isclose(cross, 0.0, abs_tol=1e-12):
        return False
    return (
        min(start[0], end[0]) <= point[0] <= max(start[0], end[0])
        and min(start[1], end[1]) <= point[1] <= max(start[1], end[1])
    )


def _point_in_ring(point: Point, ring: list[Point]) -> bool:
    inside = False
    previous = ring[-1]
    for current in ring:
        if (current[1] > point[1]) != (previous[1] > point[1]):
            intersection_x = (
                (previous[0] - current[0])
                * (point[1] - current[1])
                / (previous[1] - current[1])
                + current[0]
            )
            if point[0] < intersection_x:
                inside = not inside
        previous = current
    return inside
