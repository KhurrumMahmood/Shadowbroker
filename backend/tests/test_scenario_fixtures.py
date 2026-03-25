"""Tests that verify scenario fixtures load correctly and produce expected query results.

Each scenario is a directory of JSON files under tests/fixtures/scenarios/.
StaticDataSource loads them and should return coherent, queryable data.
"""
import json
import pytest
from pathlib import Path

from services.agent.datasource import StaticDataSource


SCENARIOS_DIR = Path(__file__).parent / "fixtures" / "scenarios"

SCENARIO_NAMES = [
    "hormuz_crisis",
    "taiwan_posture",
    "quiet_day",
    "cascade_event",
    "airlift_surge",
    "open_ended_discovery",
]


@pytest.fixture(params=SCENARIO_NAMES)
def scenario(request):
    """Yield (name, StaticDataSource, expected) for each scenario."""
    name = request.param
    ds = StaticDataSource(SCENARIOS_DIR / name)
    expected_path = SCENARIOS_DIR / name / "expected.json"
    expected = json.loads(expected_path.read_text())
    return name, ds, expected


# ── Loading Tests ─────────────────────────────────────────────────────


class TestScenarioLoading:
    """Verify all scenarios load and have the right categories."""

    def test_scenario_loads_without_error(self, scenario):
        name, ds, _ = scenario
        cats = ds.categories()
        assert len(cats) > 0, f"Scenario {name} loaded zero categories"

    def test_expected_json_has_required_fields(self, scenario):
        _, _, expected = scenario
        assert "scenario_name" in expected
        assert "test_queries" in expected
        for tq in expected["test_queries"]:
            assert "query" in tq
            assert "required_mentions" in tq
            assert "required_data_sources_queried" in tq

    def test_all_referenced_categories_exist(self, scenario):
        """Categories referenced in expected.json should exist in the fixture data."""
        name, ds, expected = scenario
        available = set(ds.categories())
        for tq in expected["test_queries"]:
            for cat in tq["required_data_sources_queried"]:
                assert cat in available, (
                    f"Scenario {name}: expected category '{cat}' "
                    f"not found in fixture data. Available: {available}"
                )


# ── Hormuz Crisis Tests ───────────────────────────────────────────────


class TestHormuzCrisis:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.ds = StaticDataSource(SCENARIOS_DIR / "hormuz_crisis")

    def test_has_tankers_near_hormuz(self):
        near = {"lat": 26.5, "lng": 56.3, "radius_km": 100}
        tankers = self.ds.query("ships", filters={"type": "tanker"}, near=near)
        assert len(tankers) >= 4, "Should have multiple tankers near Hormuz"

    def test_has_iranian_military_vessels(self):
        result = self.ds.query("ships", filters={"country": "Iran", "type": "military"})
        assert len(result) >= 2

    def test_has_us_carrier(self):
        result = self.ds.query("ships", filters={"type": "carrier"})
        assert len(result) >= 1
        assert any("United States" in s["country"] for s in result)

    def test_military_flights_near_strait(self):
        near = {"lat": 26.5, "lng": 56.3, "radius_km": 150}
        flights = self.ds.query("military_flights", near=near)
        assert len(flights) >= 4

    def test_has_isr_aircraft(self):
        recon = self.ds.query("military_flights", filters={"military_type": "recon"})
        isr = self.ds.query("military_flights", filters={"military_type": "isr"})
        assert len(recon) + len(isr) >= 2

    def test_gps_jamming_in_gulf(self):
        zones = self.ds.query("gps_jamming")
        assert len(zones) >= 2
        assert any(z["severity"] == "high" for z in zones)

    def test_news_high_risk(self):
        news = self.ds.query("news")
        assert any(n["risk_score"] >= 8 for n in news)

    def test_gdelt_iran_events(self):
        events = self.ds.query("gdelt", filters={"action_geo_cc": "IR"})
        assert len(events) >= 3

    def test_aggregate_ships_by_type(self):
        result = self.ds.aggregate("ships", group_by="type")
        assert result["top_groups"]["tanker"] >= 5
        assert "military_vessel" in result["top_groups"]
        assert "carrier" in result["top_groups"]

    def test_aggregate_military_by_country(self):
        result = self.ds.aggregate("military_flights", group_by="country")
        assert "United States" in result["top_groups"]
        assert "Iran" in result["top_groups"]


# ── Taiwan Posture Tests ──────────────────────────────────────────────


class TestTaiwanPosture:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.ds = StaticDataSource(SCENARIOS_DIR / "taiwan_posture")

    def test_pla_flights_near_strait(self):
        near = {"lat": 24.5, "lng": 119.5, "radius_km": 200}
        flights = self.ds.query("military_flights", filters={"country": "China"}, near=near)
        assert len(flights) >= 3

    def test_multi_country_naval_presence(self):
        result = self.ds.aggregate("ships", group_by="country")
        countries = set(result["top_groups"].keys())
        assert {"China", "Japan", "United States"}.issubset(countries)

    def test_carriers_present(self):
        carriers = self.ds.query("ships", filters={"type": "carrier"})
        assert len(carriers) >= 2  # Chinese + US carriers

    def test_recon_satellites_overhead(self):
        near = {"lat": 24.5, "lng": 120.0, "radius_km": 500}
        sats = self.ds.query("satellites", near=near)
        assert len(sats) >= 2

    def test_aggregate_military_flights_by_country(self):
        result = self.ds.aggregate("military_flights", group_by="country")
        assert result["top_groups"]["China"] >= 5
        assert "United States" in result["top_groups"]
        assert "Japan" in result["top_groups"]
        assert "Taiwan" in result["top_groups"]


# ── Quiet Day Tests ───────────────────────────────────────────────────


class TestQuietDay:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.ds = StaticDataSource(SCENARIOS_DIR / "quiet_day")

    def test_low_military_count(self):
        mil = self.ds.query("military_flights")
        assert len(mil) <= 3

    def test_no_high_risk_news(self):
        news = self.ds.query("news")
        assert all(n["risk_score"] <= 3 for n in news)

    def test_only_minor_earthquakes(self):
        quakes = self.ds.query("earthquakes")
        assert all(q["mag"] < 4.0 for q in quakes)

    def test_commercial_traffic_normal(self):
        ships = self.ds.query("ships")
        assert len(ships) >= 3
        types = {s["type"] for s in ships}
        assert "cargo" in types


# ── Cascade Event Tests ───────────────────────────────────────────────


class TestCascadeEvent:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.ds = StaticDataSource(SCENARIOS_DIR / "cascade_event")

    def test_major_earthquake(self):
        quakes = self.ds.query("earthquakes")
        big_quakes = [q for q in quakes if q["mag"] >= 5.0]
        assert len(big_quakes) >= 1

    def test_fires_near_earthquake(self):
        quake = self.ds.query("earthquakes")[0]
        near = {"lat": quake["lat"], "lng": quake["lng"], "radius_km": 50}
        fires = self.ds.query("firms_fires", near=near)
        assert len(fires) >= 3

    def test_outages_near_earthquake(self):
        near = {"lat": 38.80, "lng": 43.40, "radius_km": 200}
        outages = self.ds.query("internet_outages", near=near)
        assert len(outages) >= 1
        assert any(o["severity"] >= 50 for o in outages)

    def test_power_plant_near_earthquake(self):
        near = {"lat": 38.80, "lng": 43.40, "radius_km": 100}
        plants = self.ds.query("power_plants", near=near)
        assert len(plants) >= 1

    def test_cascade_co_location(self):
        """All three cascade elements should be within 100km of the quake epicenter."""
        near = {"lat": 38.80, "lng": 43.40, "radius_km": 100}
        quakes = self.ds.query("earthquakes", near=near)
        fires = self.ds.query("firms_fires", near=near)
        outages = self.ds.query("internet_outages", near=near)
        assert len(quakes) >= 1 and len(fires) >= 3 and len(outages) >= 1


# ── Airlift Surge Tests ──────────────────────────────────────────────


class TestAirliftSurge:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.ds = StaticDataSource(SCENARIOS_DIR / "airlift_surge")

    def test_c17_count(self):
        c17s = self.ds.query("military_flights", filters={"model": "C-17"})
        assert len(c17s) >= 8

    def test_eastbound_heading(self):
        """Most C-17s should have eastbound headings (60-120 degrees)."""
        c17s = self.ds.query("military_flights", filters={"model": "C-17"})
        eastbound = [f for f in c17s if 60 <= f["heading"] <= 130]
        assert len(eastbound) >= 6

    def test_rch_callsign_prefix(self):
        rch = self.ds.query("military_flights", filters={"callsign": "RCH"})
        assert len(rch) >= 8

    def test_tanker_support(self):
        tankers = self.ds.query("military_flights", filters={"military_type": "tanker"})
        assert len(tankers) >= 2

    def test_bases_along_corridor(self):
        bases = self.ds.query("military_bases")
        base_names = {b["name"] for b in bases}
        assert "Ramstein Air Base" in base_names
        assert "Al Udeid Air Base" in base_names
        assert "Incirlik Air Base" in base_names

    def test_aggregate_by_type(self):
        result = self.ds.aggregate("military_flights", group_by="military_type")
        assert result["top_groups"]["cargo"] >= 8
        assert "tanker" in result["top_groups"]


# ── Open-Ended Discovery Tests ────────────────────────────────────────


class TestOpenEndedDiscovery:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.ds = StaticDataSource(SCENARIOS_DIR / "open_ended_discovery")

    def test_corridor_finds_c17_surge(self):
        from services.agent.tools.spatial import corridor_analysis

        result = corridor_analysis(
            self.ds, category="military_flights",
            heading_min=60, heading_max=130,
        )
        # Should find the 3 C-17s in the eastbound corridor
        assert result["count"] >= 3

    def test_cross_correlate_finds_turkey_cascade(self):
        from services.agent.tools.correlation import cross_correlate

        result = cross_correlate(self.ds, lat=37.5, lng=29.0, radius_km=100)
        cats = result["co_located_categories"]
        # Earthquake, fires, and outage should all co-locate near Turkey
        assert "earthquakes" in cats
        assert "firms_fires" in cats
        assert "internet_outages" in cats

    def test_dark_vessel_detected_in_gulf(self):
        from services.agent.tools.anomaly import pattern_detect

        result = pattern_detect(self.ds, category="ships", pattern_type="dark_vessel")
        # SHADOW VESSEL has empty destination + near-zero speed
        flagged_names = [e.get("name") for e in result["flagged"]]
        assert "SHADOW VESSEL" in flagged_names

    def test_proximity_search_gulf_finds_gps_jamming(self):
        from services.agent.tools.spatial import proximity_search

        result = proximity_search(self.ds, lat=26.5, lng=56.3, radius_km=50)
        assert "gps_jamming" in result["_summary"]["categories"]
        assert "ships" in result["_summary"]["categories"]

    def test_anomaly_scan_reports_all_categories(self):
        from services.agent.tools.anomaly import anomaly_scan

        result = anomaly_scan(self.ds)
        # Without baselines, all should be "unknown"
        for cat, info in result.items():
            assert info["anomaly_level"] in ("unknown", "normal")
            assert "count" in info
