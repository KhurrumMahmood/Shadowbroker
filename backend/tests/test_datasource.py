"""Tests for the DataSource abstraction layer.

Tests StaticDataSource against JSON fixtures and InMemoryDataSource
against the live data store dict format.
"""
import json
import os
import pytest
from pathlib import Path

from services.agent.datasource import (
    DataSource,
    StaticDataSource,
    InMemoryDataSource,
    BaselineStat,
)


# ── Fixtures ──────────────────────────────────────────────────────────

SAMPLE_SHIPS = [
    {"mmsi": "123456789", "name": "TANKER ONE", "type": "tanker",
     "destination": "DUBAI", "country": "Iran", "lat": 26.5, "lng": 56.3,
     "sog": 12.5, "callsign": "T1"},
    {"mmsi": "987654321", "name": "CARGO STAR", "type": "cargo",
     "destination": "SINGAPORE", "country": "China", "lat": 1.3, "lng": 103.8,
     "sog": 8.0, "callsign": "CS"},
    {"mmsi": "111222333", "name": "NAVY VESSEL", "type": "military_vessel",
     "destination": "", "country": "United States", "lat": 26.6, "lng": 56.4,
     "sog": 18.0, "callsign": "NV"},
]

SAMPLE_MILITARY_FLIGHTS = [
    {"icao24": "ae1234", "callsign": "FORTE11", "country": "United States",
     "model": "RQ-4B", "lat": 26.0, "lng": 56.0, "alt": 15000,
     "heading": 90, "military_type": "recon"},
    {"icao24": "ae5678", "callsign": "RCH471", "country": "United States",
     "model": "C17", "lat": 50.0, "lng": -10.0, "alt": 10000,
     "heading": 85, "military_type": "cargo"},
    {"icao24": "780100", "callsign": "PLA001", "country": "China",
     "model": "J-16", "lat": 24.5, "lng": 119.5, "alt": 8000,
     "heading": 180, "military_type": "fighter"},
]

SAMPLE_EARTHQUAKES = [
    {"id": "us2026abc", "place": "10km NE of Tonga", "lat": -21.2,
     "lng": -175.1, "mag": 5.9},
    {"id": "us2026def", "place": "5km S of Baku, Azerbaijan", "lat": 40.3,
     "lng": 49.8, "mag": 3.2},
]

SAMPLE_NEWS = [
    {"title": "Iran tensions rise in Gulf", "link": "https://example.com/1",
     "source": "BBC", "risk_score": 8, "lat": 26.5, "lng": 56.3},
    {"title": "Earthquake hits Tonga region", "link": "https://example.com/2",
     "source": "USGS", "risk_score": 5, "lat": -21.2, "lng": -175.1},
]


@pytest.fixture
def sample_data():
    return {
        "ships": SAMPLE_SHIPS,
        "military_flights": SAMPLE_MILITARY_FLIGHTS,
        "earthquakes": SAMPLE_EARTHQUAKES,
        "news": SAMPLE_NEWS,
        "commercial_flights": [],
        "stocks": {},
        "oil": {},
    }


@pytest.fixture
def static_ds(tmp_path, sample_data):
    """Create a StaticDataSource from temporary JSON fixtures."""
    scenario_dir = tmp_path / "test_scenario"
    scenario_dir.mkdir()
    for key, value in sample_data.items():
        if isinstance(value, list) and value:
            (scenario_dir / f"{key}.json").write_text(json.dumps(value))
    return StaticDataSource(scenario_dir)


@pytest.fixture
def inmemory_ds(sample_data):
    return InMemoryDataSource(sample_data)


# ── StaticDataSource Tests ────────────────────────────────────────────

class TestStaticDataSource:

    def test_loads_categories_from_json_files(self, static_ds):
        ships = static_ds.query("ships")
        assert len(ships) == 3

    def test_missing_category_returns_empty(self, static_ds):
        result = static_ds.query("satellites")
        assert result == []

    def test_filter_by_field(self, static_ds):
        tankers = static_ds.query("ships", filters={"type": "tanker"})
        assert len(tankers) == 1
        assert tankers[0]["name"] == "TANKER ONE"

    def test_filter_case_insensitive(self, static_ds):
        tankers = static_ds.query("ships", filters={"type": "TANKER"})
        assert len(tankers) == 1

    def test_filter_multiple_fields_and_logic(self, static_ds):
        result = static_ds.query("ships", filters={"type": "tanker", "country": "Iran"})
        assert len(result) == 1
        result = static_ds.query("ships", filters={"type": "tanker", "country": "China"})
        assert len(result) == 0

    def test_near_filter(self, static_ds):
        # Hormuz area: 26.5N, 56.3E — should find ships and the RQ-4B
        near = {"lat": 26.5, "lng": 56.3, "radius_km": 100}
        ships = static_ds.query("ships", near=near)
        assert len(ships) == 2  # TANKER ONE and NAVY VESSEL
        assert all(s["lng"] > 56 for s in ships)

    def test_near_filter_excludes_distant(self, static_ds):
        near = {"lat": 26.5, "lng": 56.3, "radius_km": 100}
        mil = static_ds.query("military_flights", near=near)
        # Only FORTE11 is near Hormuz, not RCH471 or PLA001
        assert len(mil) == 1
        assert mil[0]["callsign"] == "FORTE11"

    def test_limit(self, static_ds):
        result = static_ds.query("ships", limit=2)
        assert len(result) == 2

    def test_aggregate_group_by(self, static_ds):
        result = static_ds.aggregate("ships", group_by="type")
        assert result["total_items"] == 3
        assert result["top_groups"]["tanker"] == 1
        assert result["top_groups"]["cargo"] == 1
        assert result["top_groups"]["military_vessel"] == 1

    def test_aggregate_group_by_country(self, static_ds):
        result = static_ds.aggregate("military_flights", group_by="country")
        assert result["top_groups"]["United States"] == 2
        assert result["top_groups"]["China"] == 1

    def test_aggregate_with_near_filter(self, static_ds):
        near = {"lat": 26.5, "lng": 56.3, "radius_km": 100}
        result = static_ds.aggregate("ships", group_by="type", near=near)
        assert result["total_items"] == 2

    def test_aggregate_with_top_n(self, static_ds):
        result = static_ds.aggregate("ships", group_by="type", top_n=1)
        assert len(result["top_groups"]) == 1

    def test_categories_lists_loaded_categories(self, static_ds):
        cats = static_ds.categories()
        assert "ships" in cats
        assert "military_flights" in cats
        assert "earthquakes" in cats

    def test_get_snapshot_returns_none(self, static_ds):
        # StaticDataSource has no temporal data
        assert static_ds.get_snapshot(1.0) is None

    def test_get_baseline_returns_none(self, static_ds):
        assert static_ds.get_baseline("ships_count") is None


# ── InMemoryDataSource Tests ──────────────────────────────────────────

class TestInMemoryDataSource:

    def test_reads_from_dict(self, inmemory_ds):
        ships = inmemory_ds.query("ships")
        assert len(ships) == 3

    def test_filter_works(self, inmemory_ds):
        result = inmemory_ds.query("military_flights",
                                   filters={"country": "China"})
        assert len(result) == 1
        assert result[0]["callsign"] == "PLA001"

    def test_near_filter_works(self, inmemory_ds):
        near = {"lat": 24.5, "lng": 119.5, "radius_km": 50}
        result = inmemory_ds.query("military_flights", near=near)
        assert len(result) == 1
        assert result[0]["callsign"] == "PLA001"

    def test_aggregate_works(self, inmemory_ds):
        result = inmemory_ds.aggregate("ships", group_by="country")
        assert result["total_items"] == 3

    def test_non_list_category_returns_empty(self, inmemory_ds):
        result = inmemory_ds.query("stocks")
        assert result == []

    def test_empty_list_category(self, inmemory_ds):
        result = inmemory_ds.query("commercial_flights")
        assert result == []

    def test_categories_lists_all_with_data(self, inmemory_ds):
        cats = inmemory_ds.categories()
        assert "ships" in cats
        assert "stocks" not in cats  # dict, not list
        assert "commercial_flights" not in cats  # empty list


# ── Protocol Compliance ───────────────────────────────────────────────

class TestProtocolCompliance:
    """Verify both implementations satisfy the DataSource interface."""

    def test_static_is_datasource(self, static_ds):
        assert isinstance(static_ds, DataSource)

    def test_inmemory_is_datasource(self, inmemory_ds):
        assert isinstance(inmemory_ds, DataSource)
