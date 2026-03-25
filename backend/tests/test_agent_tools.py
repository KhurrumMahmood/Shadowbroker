"""Tests for agent analysis tools — spatial, temporal, anomaly, correlation."""
import pytest
from pathlib import Path

from services.agent.datasource import StaticDataSource

FIXTURES = Path(__file__).parent / "fixtures" / "scenarios"


@pytest.fixture
def hormuz_ds():
    return StaticDataSource(FIXTURES / "hormuz_crisis")


@pytest.fixture
def airlift_ds():
    return StaticDataSource(FIXTURES / "airlift_surge")


@pytest.fixture
def cascade_ds():
    return StaticDataSource(FIXTURES / "cascade_event")


@pytest.fixture
def quiet_ds():
    return StaticDataSource(FIXTURES / "quiet_day")


# ── Spatial Tools ──────────────────────────────────────────────────────


class TestProximitySearch:
    """proximity_search: multi-category spatial query."""

    def test_finds_entities_near_hormuz(self, hormuz_ds):
        from services.agent.tools.spatial import proximity_search

        result = proximity_search(hormuz_ds, lat=26.5, lng=56.3, radius_km=100)
        # Should find ships AND military flights near Hormuz
        assert "ships" in result
        assert "military_flights" in result
        assert len(result["ships"]) > 0
        assert len(result["military_flights"]) > 0

    def test_filters_to_specified_categories(self, hormuz_ds):
        from services.agent.tools.spatial import proximity_search

        result = proximity_search(
            hormuz_ds, lat=26.5, lng=56.3, radius_km=100,
            categories=["ships"],
        )
        assert "ships" in result
        assert "military_flights" not in result

    def test_returns_empty_for_no_matches(self, hormuz_ds):
        from services.agent.tools.spatial import proximity_search

        # Middle of the Pacific — nothing there
        result = proximity_search(hormuz_ds, lat=0.0, lng=-170.0, radius_km=50)
        assert result["_summary"]["total_entities"] == 0
        assert result["_summary"]["categories"] == []

    def test_includes_gps_jamming(self, hormuz_ds):
        from services.agent.tools.spatial import proximity_search

        result = proximity_search(hormuz_ds, lat=26.5, lng=56.5, radius_km=100)
        assert "gps_jamming" in result
        assert len(result["gps_jamming"]) > 0

    def test_returns_summary_counts(self, hormuz_ds):
        from services.agent.tools.spatial import proximity_search

        result = proximity_search(hormuz_ds, lat=26.5, lng=56.3, radius_km=200)
        assert "_summary" in result
        assert result["_summary"]["total_entities"] > 0
        assert "ships" in result["_summary"]["categories"]


class TestCorridorAnalysis:
    """corridor_analysis: find entities traveling in a heading band."""

    def test_finds_eastbound_c17s(self, airlift_ds):
        from services.agent.tools.spatial import corridor_analysis

        result = corridor_analysis(
            airlift_ds, category="military_flights",
            heading_min=60, heading_max=130,
        )
        assert result["count"] >= 8  # 9 C-17s + C-5M in the corridor
        assert len(result["entities"]) >= 8

    def test_model_filter(self, airlift_ds):
        from services.agent.tools.spatial import corridor_analysis

        result = corridor_analysis(
            airlift_ds, category="military_flights",
            heading_min=60, heading_max=130,
            model_filter="C-17",
        )
        # Should only include C-17s, not C-5M or tankers
        for e in result["entities"]:
            assert "C-17" in e.get("model", "")

    def test_narrow_heading_band(self, airlift_ds):
        from services.agent.tools.spatial import corridor_analysis

        result = corridor_analysis(
            airlift_ds, category="military_flights",
            heading_min=114, heading_max=116,
        )
        # Only heading=115 should match
        assert result["count"] >= 1

    def test_wrapping_heading(self, hormuz_ds):
        from services.agent.tools.spatial import corridor_analysis

        # Heading band crossing 360: 350-10 degrees (north-ish)
        result = corridor_analysis(
            hormuz_ds, category="ships",
            heading_min=350, heading_max=10,
        )
        # Ships with cog=0 should match
        ships_at_north = [s for s in hormuz_ds.query("ships") if s.get("cog") == 0]
        assert result["count"] >= len(ships_at_north)

    def test_empty_category(self, quiet_ds):
        from services.agent.tools.spatial import corridor_analysis

        result = corridor_analysis(
            quiet_ds, category="nonexistent",
            heading_min=0, heading_max=360,
        )
        assert result["count"] == 0


# ── Temporal Tools ─────────────────────────────────────────────────────


class TestTemporalCompare:
    """temporal_compare: compare current to historical snapshot."""

    def test_returns_none_without_snapshot(self, hormuz_ds):
        from services.agent.tools.temporal import temporal_compare

        result = temporal_compare(hormuz_ds, category="ships", hours_ago=1.0)
        assert result is None

    def test_returns_delta_with_snapshot(self):
        from services.agent.tools.temporal import temporal_compare
        from services.agent.datasource import InMemoryDataSource, Snapshot
        import time

        ds = InMemoryDataSource({"ships": [
            {"mmsi": "100", "lat": 10, "lng": 20},
            {"mmsi": "200", "lat": 11, "lng": 21},
            {"mmsi": "300", "lat": 12, "lng": 22},
        ]})
        # Inject a mock snapshot with only 2 ships
        snap = Snapshot(
            timestamp=time.time() - 3600,
            counts={"ships": 2},
            entity_ids={"ships": {"100", "200"}},
        )
        ds._snapshot = snap  # we'll read this in temporal_compare

        result = temporal_compare(ds, category="ships", hours_ago=1.0)
        assert result is not None
        assert result["current_count"] == 3
        assert result["historical_count"] == 2
        assert "300" in result["new_entity_ids"]


# ── Anomaly Tools ──────────────────────────────────────────────────────


class TestAnomalyScan:
    """anomaly_scan: check category counts against baselines."""

    def test_returns_results_per_category(self, hormuz_ds):
        from services.agent.tools.anomaly import anomaly_scan

        result = anomaly_scan(hormuz_ds)
        # Should have an entry per available category
        cats = hormuz_ds.categories()
        for cat in cats:
            assert cat in result, f"Missing category: {cat}"
            assert "count" in result[cat]

    def test_no_anomaly_on_quiet_day(self, quiet_ds):
        from services.agent.tools.anomaly import anomaly_scan

        result = anomaly_scan(quiet_ds)
        # Without baselines, no z-scores — anomaly_level should be "unknown"
        for cat, info in result.items():
            assert info["anomaly_level"] in ("unknown", "normal")

    def test_specific_categories(self, hormuz_ds):
        from services.agent.tools.anomaly import anomaly_scan

        result = anomaly_scan(hormuz_ds, categories=["ships", "military_flights"])
        assert "ships" in result
        assert "military_flights" in result
        assert "news" not in result


class TestPatternDetect:
    """pattern_detect: behavioral pattern detection."""

    def test_dark_vessel_detection(self, hormuz_ds):
        from services.agent.tools.anomaly import pattern_detect

        result = pattern_detect(hormuz_ds, category="ships", pattern_type="dark_vessel")
        # Ships with empty/suspicious destination are flagged
        assert isinstance(result["flagged"], list)
        # NOOR 1 (empty dest) and DENA ("FOR ORDERS") should be flagged
        flagged_names = [e.get("name") for e in result["flagged"]]
        assert "NOOR 1" in flagged_names or "DENA" in flagged_names

    def test_holding_pattern_detection(self, hormuz_ds):
        from services.agent.tools.anomaly import pattern_detect

        result = pattern_detect(
            hormuz_ds, category="ships", pattern_type="holding_pattern"
        )
        # Ships with very low speed-over-ground are potentially loitering
        assert isinstance(result["flagged"], list)

    def test_unknown_pattern_type(self, hormuz_ds):
        from services.agent.tools.anomaly import pattern_detect

        result = pattern_detect(
            hormuz_ds, category="ships", pattern_type="nonexistent"
        )
        assert result["flagged"] == []
        assert "error" in result or result["pattern_type"] == "nonexistent"


# ── Correlation Tools ──────────────────────────────────────────────────


class TestCrossCorrelate:
    """cross_correlate: co-location analysis across all categories."""

    def test_finds_colocation_at_hormuz(self, hormuz_ds):
        from services.agent.tools.correlation import cross_correlate

        result = cross_correlate(hormuz_ds, lat=26.5, lng=56.3, radius_km=100)
        assert "co_located_categories" in result
        cats = result["co_located_categories"]
        # Ships and military flights should both be present near Hormuz
        assert "ships" in cats
        assert "military_flights" in cats

    def test_cascade_colocation(self, cascade_ds):
        from services.agent.tools.correlation import cross_correlate

        # Near the Turkey earthquake epicenter
        result = cross_correlate(cascade_ds, lat=38.8, lng=43.4, radius_km=100)
        cats = result["co_located_categories"]
        # Earthquakes, fires, and outages should all be co-located
        assert "earthquakes" in cats
        assert "firms_fires" in cats
        assert "internet_outages" in cats

    def test_no_colocation_in_empty_area(self, hormuz_ds):
        from services.agent.tools.correlation import cross_correlate

        result = cross_correlate(hormuz_ds, lat=0.0, lng=-170.0, radius_km=50)
        assert len(result["co_located_categories"]) == 0

    def test_returns_counts_per_category(self, hormuz_ds):
        from services.agent.tools.correlation import cross_correlate

        result = cross_correlate(hormuz_ds, lat=26.5, lng=56.3, radius_km=100)
        for cat in result["co_located_categories"]:
            assert result["counts"][cat] > 0

    def test_correlation_pairs(self, cascade_ds):
        from services.agent.tools.correlation import cross_correlate

        result = cross_correlate(cascade_ds, lat=38.8, lng=43.4, radius_km=100)
        # Should identify which pairs of categories are co-located
        assert "pairs" in result
        assert len(result["pairs"]) > 0
