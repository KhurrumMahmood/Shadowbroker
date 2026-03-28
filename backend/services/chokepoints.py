"""
Strategic maritime chokepoints — shared constants used by both
AIS streaming (always-subscribe regions) and alert checkers.
"""
from __future__ import annotations

import math

CHOKEPOINTS = [
    {"name": "Strait of Hormuz", "lat": 26.5, "lng": 56.3, "radius_km": 150},
    {"name": "Suez Canal", "lat": 30.0, "lng": 32.5, "radius_km": 100},
    {"name": "Strait of Malacca", "lat": 2.5, "lng": 101.5, "radius_km": 150},
    {"name": "Bab-el-Mandeb", "lat": 12.6, "lng": 43.3, "radius_km": 100},
    {"name": "Panama Canal", "lat": 9.1, "lng": -79.7, "radius_km": 80},
    {"name": "Taiwan Strait", "lat": 24.5, "lng": 119.5, "radius_km": 200},
]


def _compute_bboxes() -> list[list[list[float]]]:
    """Convert chokepoints to AIS bounding boxes: [[[south, west], [north, east]], ...]

    Uses the approximation: 1° lat ≈ 111 km, 1° lng ≈ 111 * cos(lat) km.
    """
    bboxes: list[list[list[float]]] = []
    for cp in CHOKEPOINTS:
        lat = cp["lat"]
        lng = cp["lng"]
        r = cp["radius_km"]
        dlat = r / 111.0
        dlng = r / (111.0 * math.cos(math.radians(lat)))
        bboxes.append([
            [round(lat - dlat, 4), round(lng - dlng, 4)],
            [round(lat + dlat, 4), round(lng + dlng, 4)],
        ])
    return bboxes


# Pre-computed once at import time — CHOKEPOINTS is static
_CACHED_BBOXES = _compute_bboxes()


def chokepoint_bboxes() -> list[list[list[float]]]:
    """Return cached chokepoint bounding boxes."""
    return _CACHED_BBOXES
