"""Temporal snapshot store for the agent system.

Maintains a ring buffer of periodic data snapshots, enabling
temporal comparison queries like "what changed in the last 4 hours?"
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class Snapshot:
    """A point-in-time data snapshot for temporal comparison."""
    timestamp: float
    counts: dict[str, int]
    entity_ids: dict[str, set[str]] = field(default_factory=dict)


class SnapshotStore:
    """In-memory ring buffer of periodic data snapshots.

    Records entity counts and ID sets at regular intervals.
    Supports querying historical snapshots and computing deltas.

    Default: 288 snapshots × 5min intervals = 24h of history.
    """

    def __init__(self, max_snapshots: int = 288):
        self._ring: deque[Snapshot] = deque(maxlen=max_snapshots)

    @property
    def size(self) -> int:
        return len(self._ring)

    def record(self, data: dict, id_keys: dict[str, str] | None = None) -> Snapshot:
        """Take a snapshot of current entity counts and ID sets.

        Args:
            data: The latest_data dict (or any dict of category -> list[dict])
            id_keys: Map of category -> field name for entity ID.
                     Defaults: mmsi for ships, icao24 for flights, id for others.
        """
        defaults = {
            "ships": "mmsi",
            "military_flights": "icao24",
            "commercial_flights": "icao24",
            "tracked_flights": "icao24",
            "private_flights": "icao24",
            "private_jets": "icao24",
            "satellites": "id",
            "earthquakes": "id",
        }
        keys = {**defaults, **(id_keys or {})}

        counts: dict[str, int] = {}
        entity_ids: dict[str, set[str]] = {}

        for category, items in data.items():
            if not isinstance(items, list):
                continue
            counts[category] = len(items)
            id_key = keys.get(category, "id")
            ids = set()
            for item in items:
                eid = item.get(id_key)
                if eid is not None:
                    ids.add(str(eid))
            if ids:
                entity_ids[category] = ids

        snap = Snapshot(
            timestamp=time.time(),
            counts=counts,
            entity_ids=entity_ids,
        )
        self._ring.append(snap)
        return snap

    def get_snapshot(self, hours_ago: float) -> Snapshot | None:
        """Find the snapshot closest to N hours ago.

        Returns None if no snapshots exist or all are newer than the target.
        """
        if not self._ring:
            return None

        target_ts = time.time() - (hours_ago * 3600)

        # If target is before our oldest snapshot, return the oldest
        if target_ts <= self._ring[0].timestamp:
            return self._ring[0]

        # If target is after our newest, nothing is old enough
        if target_ts >= self._ring[-1].timestamp:
            return None

        # Binary-ish search for closest
        best = None
        best_diff = float("inf")
        for snap in self._ring:
            diff = abs(snap.timestamp - target_ts)
            if diff < best_diff:
                best_diff = diff
                best = snap
        return best

    def get_delta(
        self, current_data: dict, hours_ago: float, category: str,
        id_key: str | None = None,
    ) -> dict | None:
        """Compare current counts/entities to a historical snapshot.

        Returns:
            {current_count, historical_count, delta_pct,
             new_entity_ids, disappeared_entity_ids}
            or None if no historical snapshot available.
        """
        snap = self.get_snapshot(hours_ago)
        if snap is None:
            return None

        # Current state
        items = current_data.get(category)
        if not isinstance(items, list):
            current_count = 0
            current_ids: set[str] = set()
        else:
            current_count = len(items)
            defaults = {"ships": "mmsi", "military_flights": "icao24"}
            key = id_key or defaults.get(category, "id")
            current_ids = {str(item.get(key)) for item in items if item.get(key) is not None}

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
        }
