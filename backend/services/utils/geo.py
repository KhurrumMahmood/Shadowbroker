"""Geographic utility functions for cross-domain spatial analysis.

Extracted from test-silo/analyze.py — proven algorithms with zero external dependencies.
"""
import math
from collections import defaultdict


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two lat/lon points."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


def grid_cluster(
    items: list[dict],
    cell_degrees: float,
    lat_key: str = "lat",
    lon_key: str = "lon",
) -> dict[tuple[float, float], list[dict]]:
    """Bucket items into geographic grid cells.

    Returns dict mapping (cell_lat, cell_lon) to list of items in that cell.
    Items missing coordinates are silently skipped.
    """
    grid: dict[tuple[float, float], list[dict]] = defaultdict(list)
    for item in items:
        lat = item.get(lat_key)
        lon = item.get(lon_key)
        if lat is None or lon is None:
            continue
        try:
            lat_f, lon_f = float(lat), float(lon)
        except (ValueError, TypeError):
            continue
        key = (
            round(lat_f / cell_degrees) * cell_degrees,
            round(lon_f / cell_degrees) * cell_degrees,
        )
        grid[key].append(item)
    return dict(grid)


def spatial_join(
    entities_a: list[dict],
    entities_b: list[dict],
    radius_km: float,
    a_lat: str = "lat",
    a_lon: str = "lon",
    b_lat: str = "lat",
    b_lon: str = "lon",
) -> list[dict]:
    """Find all pairs where an entity from A is within radius_km of an entity from B.

    Returns list of {"entity_a": ..., "entity_b": ..., "distance_km": ...} dicts,
    sorted by distance ascending.
    """
    results = []
    for a in entities_a:
        alat = a.get(a_lat)
        alon = a.get(a_lon)
        if alat is None or alon is None:
            continue
        try:
            alat_f, alon_f = float(alat), float(alon)
        except (ValueError, TypeError):
            continue
        for b in entities_b:
            blat = b.get(b_lat)
            blon = b.get(b_lon)
            if blat is None or blon is None:
                continue
            try:
                blat_f, blon_f = float(blat), float(blon)
            except (ValueError, TypeError):
                continue
            d = haversine(alat_f, alon_f, blat_f, blon_f)
            if d <= radius_km:
                results.append({
                    "entity_a": a,
                    "entity_b": b,
                    "distance_km": d,
                })
    results.sort(key=lambda x: x["distance_km"])
    return results
