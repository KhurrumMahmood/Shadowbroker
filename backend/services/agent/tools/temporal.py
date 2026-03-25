"""Temporal analysis tools for the agent system.

Compares current entity counts to historical snapshots.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.agent.datasource import DataSource

# Default ID keys per category (same as snapshots.py)
_ID_KEYS = {
    "ships": "mmsi",
    "military_flights": "icao24",
    "commercial_flights": "icao24",
    "tracked_flights": "icao24",
    "private_flights": "icao24",
    "private_jets": "icao24",
    "satellites": "id",
    "earthquakes": "id",
}


def temporal_compare(
    ds: DataSource,
    category: str,
    hours_ago: float,
    id_key: str | None = None,
) -> dict | None:
    """Compare current counts/entities to a historical snapshot.

    Returns {current_count, historical_count, delta_pct,
             new_entity_ids, disappeared_entity_ids}
    or None if no historical snapshot available.
    """
    snap = ds.get_snapshot(hours_ago)
    if snap is None:
        # Check for injected snapshot (test support)
        snap = getattr(ds, "_snapshot", None)
        if snap is None:
            return None

    items = ds.query(category, limit=10000)
    current_count = len(items)

    key = id_key or _ID_KEYS.get(category, "id")
    current_ids = {str(item[key]) for item in items if item.get(key) is not None}

    historical_count = snap.counts.get(category, 0)
    historical_ids = snap.entity_ids.get(category, set())

    delta_pct = 0.0
    if historical_count > 0:
        delta_pct = ((current_count - historical_count) / historical_count) * 100

    return {
        "current_count": current_count,
        "historical_count": historical_count,
        "delta_pct": round(delta_pct, 1),
        "new_entity_ids": current_ids - historical_ids,
        "disappeared_entity_ids": historical_ids - current_ids,
        "hours_ago": hours_ago,
    }
