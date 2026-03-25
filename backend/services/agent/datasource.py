"""DataSource abstraction for the agent system.

Provides a clean interface for querying entity data regardless of
where it comes from — in-memory store, JSON fixtures, or a database.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass
class BaselineStat:
    """Rolling statistical baseline for anomaly detection."""
    mean: float
    std: float
    n: int


@dataclass
class Snapshot:
    """A point-in-time data snapshot for temporal comparison."""
    timestamp: float
    counts: dict[str, int]
    entity_ids: dict[str, set[str]]


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two points in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _fuzzy_contains(field_val: str, match_val: str) -> bool:
    """Case-insensitive substring match."""
    return match_val.lower() in field_val.lower()


def _apply_filters(
    items: list[dict],
    filters: dict[str, str] | None,
    near: dict | None,
) -> list[dict]:
    """Apply field filters (AND, case-insensitive contains) and geo filter."""
    result = items
    if filters:
        for field, match_val in filters.items():
            mv = str(match_val)
            result = [
                e for e in result
                if _fuzzy_contains(str(e.get(field, "")), mv)
            ]
    if near:
        lat = near.get("lat", 0)
        lng = near.get("lng", 0)
        radius = near.get("radius_km", 200)
        result = [
            e for e in result
            if e.get("lat") is not None
            and e.get("lng") is not None
            and _haversine_km(lat, lng, float(e["lat"]), float(e["lng"])) <= radius
        ]
    return result


@runtime_checkable
class DataSource(Protocol):
    """Interface for querying entity data.

    Implementations:
    - InMemoryDataSource: reads from ShadowBroker's latest_data dict
    - StaticDataSource: reads from JSON fixture files (for testing)
    - PostgresDataSource: reads from ingestion database (future)
    """

    def query(
        self,
        category: str,
        filters: dict[str, str] | None = None,
        near: dict | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Query entities in a category with optional filters and geo proximity."""
        ...

    def aggregate(
        self,
        category: str,
        group_by: str,
        filters: dict[str, str] | None = None,
        near: dict | None = None,
        top_n: int = 20,
    ) -> dict:
        """Count entities grouped by a field. Returns {total_items, unique_values, top_groups}."""
        ...

    def categories(self) -> list[str]:
        """List available data categories that have entities."""
        ...

    def get_snapshot(self, hours_ago: float) -> Snapshot | None:
        """Get a historical data snapshot from N hours ago. None if unavailable."""
        ...

    def get_baseline(self, metric: str) -> BaselineStat | None:
        """Get rolling baseline statistics for a metric. None if unavailable."""
        ...


class InMemoryDataSource:
    """Reads from ShadowBroker's in-memory latest_data dict."""

    def __init__(self, data: dict, snapshot_store=None, baseline_store=None):
        self._data = data
        self._snapshot_store = snapshot_store
        self._baseline_store = baseline_store

    def query(
        self,
        category: str,
        filters: dict[str, str] | None = None,
        near: dict | None = None,
        limit: int = 100,
    ) -> list[dict]:
        items = self._data.get(category)
        if not items or not isinstance(items, list):
            return []
        filtered = _apply_filters(items, filters, near)
        return filtered[:limit]

    def aggregate(
        self,
        category: str,
        group_by: str,
        filters: dict[str, str] | None = None,
        near: dict | None = None,
        top_n: int = 20,
    ) -> dict:
        items = self._data.get(category)
        if not items or not isinstance(items, list):
            return {"total_items": 0, "unique_values": 0, "top_groups": {}}
        filtered = _apply_filters(items, filters, near)
        counts: dict[str, int] = {}
        for e in filtered:
            val = str(e.get(group_by, "UNKNOWN")).strip() or "UNKNOWN"
            counts[val] = counts.get(val, 0) + 1
        sorted_groups = dict(sorted(counts.items(), key=lambda x: -x[1])[:top_n])
        return {
            "total_items": len(filtered),
            "unique_values": len(counts),
            "top_groups": sorted_groups,
        }

    def categories(self) -> list[str]:
        return [
            k for k, v in self._data.items()
            if isinstance(v, list) and len(v) > 0
        ]

    def get_snapshot(self, hours_ago: float) -> Snapshot | None:
        if self._snapshot_store is not None:
            return self._snapshot_store.get_snapshot(hours_ago)
        return None

    def get_baseline(self, metric: str) -> BaselineStat | None:
        if self._baseline_store is not None:
            stat = self._baseline_store.get(metric)
            if stat is not None:
                return BaselineStat(mean=stat.mean, std=stat.std, n=stat.n)
        return None


class StaticDataSource:
    """Reads from JSON fixture files on disk. Used for deterministic testing."""

    def __init__(self, scenario_dir: str | Path):
        self._data: dict[str, list[dict]] = {}
        scenario_path = Path(scenario_dir)
        for f in scenario_path.glob("*.json"):
            if f.stem == "expected":
                continue
            with open(f) as fh:
                content = json.load(fh)
            if isinstance(content, list):
                self._data[f.stem] = content

    def query(
        self,
        category: str,
        filters: dict[str, str] | None = None,
        near: dict | None = None,
        limit: int = 100,
    ) -> list[dict]:
        items = self._data.get(category, [])
        if not items:
            return []
        filtered = _apply_filters(items, filters, near)
        return filtered[:limit]

    def aggregate(
        self,
        category: str,
        group_by: str,
        filters: dict[str, str] | None = None,
        near: dict | None = None,
        top_n: int = 20,
    ) -> dict:
        items = self._data.get(category, [])
        if not items:
            return {"total_items": 0, "unique_values": 0, "top_groups": {}}
        filtered = _apply_filters(items, filters, near)
        counts: dict[str, int] = {}
        for e in filtered:
            val = str(e.get(group_by, "UNKNOWN")).strip() or "UNKNOWN"
            counts[val] = counts.get(val, 0) + 1
        sorted_groups = dict(sorted(counts.items(), key=lambda x: -x[1])[:top_n])
        return {
            "total_items": len(filtered),
            "unique_values": len(counts),
            "top_groups": sorted_groups,
        }

    def categories(self) -> list[str]:
        return [k for k, v in self._data.items() if v]

    def get_snapshot(self, hours_ago: float) -> Snapshot | None:
        return None

    def get_baseline(self, metric: str) -> BaselineStat | None:
        return None
