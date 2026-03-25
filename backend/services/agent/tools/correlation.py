"""Cross-source correlation tools for the agent system.

Identifies co-located entities across multiple data categories,
enabling multi-domain situational awareness.
"""
from __future__ import annotations

from itertools import combinations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.agent.datasource import DataSource


def cross_correlate(
    ds: DataSource,
    lat: float,
    lng: float,
    radius_km: float,
) -> dict:
    """Spatial co-location analysis across all categories.

    Returns which categories have entities in the same area,
    along with counts and co-located pairs.
    """
    cats = ds.categories()
    near = {"lat": lat, "lng": lng, "radius_km": radius_km}

    counts: dict[str, int] = {}
    co_located: list[str] = []

    for cat in cats:
        entities = ds.query(cat, near=near, limit=500)
        if entities:
            counts[cat] = len(entities)
            co_located.append(cat)

    # Build pairs of co-located categories
    pairs = []
    for a, b in combinations(co_located, 2):
        pairs.append({
            "categories": [a, b],
            "counts": {a: counts[a], b: counts[b]},
        })

    return {
        "co_located_categories": co_located,
        "counts": counts,
        "pairs": pairs,
        "search_center": {"lat": lat, "lng": lng},
        "radius_km": radius_km,
        "total_categories": len(co_located),
    }
