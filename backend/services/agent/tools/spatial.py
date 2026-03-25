"""Spatial analysis tools for the agent system.

Provides multi-category proximity search and heading-band corridor analysis.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.agent.datasource import DataSource


def proximity_search(
    ds: DataSource,
    lat: float,
    lng: float,
    radius_km: float,
    categories: list[str] | None = None,
) -> dict:
    """Search all (or specified) categories for entities within a radius.

    Returns {category: [entities], ..., _summary: {total_entities, categories}}.
    """
    cats = categories or ds.categories()
    near = {"lat": lat, "lng": lng, "radius_km": radius_km}

    result: dict = {}
    total = 0
    found_cats = []

    for cat in cats:
        entities = ds.query(cat, near=near, limit=500)
        if entities:
            result[cat] = entities
            total += len(entities)
            found_cats.append(cat)
        else:
            result[cat] = []

    result["_summary"] = {
        "total_entities": total,
        "categories": found_cats,
        "search_center": {"lat": lat, "lng": lng},
        "radius_km": radius_km,
    }
    return result


def corridor_analysis(
    ds: DataSource,
    category: str,
    heading_min: float,
    heading_max: float,
    model_filter: str | None = None,
) -> dict:
    """Find entities traveling in a heading band.

    Supports wrapping (e.g., heading_min=350, heading_max=10 for northbound).
    """
    entities = ds.query(category, limit=1000)

    def _in_heading_band(heading: float | None) -> bool:
        if heading is None:
            return False
        if heading_min <= heading_max:
            return heading_min <= heading <= heading_max
        # Wrapping case: 350-10 means 350..360 or 0..10
        return heading >= heading_min or heading <= heading_max

    heading_key = "heading" if category == "military_flights" else "cog"

    matched = []
    for e in entities:
        h = e.get(heading_key)
        if h is None:
            h = e.get("heading") or e.get("cog")
        if h is not None:
            h = float(h)
        if not _in_heading_band(h):
            continue
        if model_filter and model_filter.lower() not in (e.get("model", "") or "").lower():
            continue
        matched.append(e)

    return {
        "count": len(matched),
        "entities": matched,
        "heading_band": {"min": heading_min, "max": heading_max},
        "model_filter": model_filter,
    }
