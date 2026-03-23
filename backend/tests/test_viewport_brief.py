"""Tests for the viewport briefing feature (Phase 4E)."""
import pytest
from services.llm_assistant import build_briefing_context


# --- Test data ---
MOCK_DATA = {
    "commercial_flights": [
        {"icao24": "a1", "callsign": "BA123", "lat": 51.5, "lng": -0.1, "alt": 35000, "country": "UK", "model": "B738", "origin_name": "LHR", "dest_name": "CDG"},
        {"icao24": "a2", "callsign": "AF456", "lat": 51.2, "lng": 0.5, "alt": 38000, "country": "France", "model": "A320", "origin_name": "CDG", "dest_name": "LHR"},
        {"icao24": "a3", "callsign": "UA789", "lat": 40.7, "lng": -74.0, "alt": 30000, "country": "US", "model": "B777", "origin_name": "JFK", "dest_name": "LAX"},
    ],
    "military_flights": [
        {"icao24": "m1", "callsign": "RCH401", "lat": 51.0, "lng": -0.5, "alt": 30000, "country": "US", "model": "C-17", "military_type": "cargo"},
    ],
    "tracked_flights": [
        {"icao24": "t1", "callsign": "EXEC1", "lat": 51.2, "lng": -0.3, "alt": 40000, "country": "US", "model": "G650", "tracked_name": "US Gov Jet", "alert_category": "Government"},
    ],
    "ships": [
        {"mmsi": 111, "name": "HMS QUEEN ELIZABETH", "type": "carrier", "lat": 50.8, "lng": -1.1, "country": "UK", "sog": 12, "heading": 180},
        {"mmsi": 222, "name": "MAERSK OHIO", "type": "cargo", "lat": 51.0, "lng": -0.5, "country": "Denmark", "sog": 10, "heading": 90},
        {"mmsi": 333, "name": "PACIFIC VOYAGER", "type": "tanker", "lat": 26.5, "lng": 56.3, "country": "Panama", "sog": 8, "heading": 45},
    ],
    "earthquakes": [
        {"id": "eq1", "place": "Near London", "lat": 51.3, "lng": -0.2, "mag": 3.2},
        {"id": "eq2", "place": "Near Tokyo", "lat": 35.6, "lng": 139.7, "mag": 5.1},
    ],
    "military_bases": [
        {"name": "RAF Northolt", "country": "UK", "lat": 51.55, "lng": -0.42, "branch": "RAF"},
    ],
    "satellites": [
        {"id": 1, "name": "ISS", "lat": 51.0, "lng": -0.5, "alt_km": 408, "speed_knots": 0, "heading": 0, "country": "ISA", "mission": "space_station", "sat_type": "station"},
    ],
}

# Viewport covering London area
LONDON_VIEWPORT = {"south": 50.5, "west": -1.5, "north": 52.0, "east": 1.0}

# Viewport covering nothing interesting
EMPTY_VIEWPORT = {"south": -50.0, "west": -50.0, "north": -49.0, "east": -49.0}


class TestBuildBriefingContext:
    """Tests for build_briefing_context()."""

    def test_filters_to_viewport(self):
        """Only entities within viewport are included."""
        ctx = build_briefing_context(MOCK_DATA, LONDON_VIEWPORT)
        # London viewport should capture BA123, AF456, RCH401, tracked, HMS QE, MAERSK, eq1, RAF base
        assert ctx["counts"]["commercial_flights"] == 2  # BA123 + AF456
        assert ctx["counts"]["military_flights"] == 1  # RCH401
        assert ctx["counts"]["ships"] >= 2  # HMS QE + MAERSK
        # UA789 (JFK) and PACIFIC VOYAGER (Hormuz) should be excluded
        assert "UA789" not in str(ctx.get("notable", []))

    def test_empty_viewport_returns_zero_counts(self):
        """Viewport with no entities returns all-zero counts."""
        ctx = build_briefing_context(MOCK_DATA, EMPTY_VIEWPORT)
        total = sum(ctx["counts"].values())
        assert total == 0
        assert ctx["notable"] == []

    def test_notable_includes_military_and_tracked(self):
        """Military vessels, tracked flights, and carriers are flagged as notable."""
        ctx = build_briefing_context(MOCK_DATA, LONDON_VIEWPORT)
        notable_names = [n["name"] for n in ctx["notable"]]
        # Carrier should be notable
        assert any("QUEEN ELIZABETH" in n for n in notable_names)
        # Tracked flight should be notable
        assert any("EXEC1" in n or "US Gov" in n for n in notable_names)
        # Military flight should be notable
        assert any("RCH401" in n for n in notable_names)

    def test_notable_has_required_fields(self):
        """Each notable entity has type, id, name, and why."""
        ctx = build_briefing_context(MOCK_DATA, LONDON_VIEWPORT)
        for n in ctx["notable"]:
            assert "type" in n
            assert "id" in n
            assert "name" in n
            assert "why" in n

    def test_notable_includes_significant_earthquakes(self):
        """Earthquakes with mag >= 4.0 are flagged as notable."""
        # The London earthquake (mag 3.2) is NOT notable, but add a big one
        big_quake_data = dict(MOCK_DATA)
        big_quake_data["earthquakes"] = [
            {"id": "eq_big", "place": "Central London", "lat": 51.5, "lng": -0.1, "mag": 5.5},
        ]
        ctx = build_briefing_context(big_quake_data, LONDON_VIEWPORT)
        notable_names = [n["name"] for n in ctx["notable"]]
        assert any("Central London" in n for n in notable_names)

    def test_counts_per_category(self):
        """Counts dict has expected category keys."""
        ctx = build_briefing_context(MOCK_DATA, LONDON_VIEWPORT)
        assert "commercial_flights" in ctx["counts"]
        assert "military_flights" in ctx["counts"]
        assert "ships" in ctx["counts"]

    def test_suggested_layers(self):
        """Suggested layers enable categories that have data in viewport."""
        ctx = build_briefing_context(MOCK_DATA, LONDON_VIEWPORT)
        assert ctx["suggested_layers"].get("flights") is True  # commercial flights in view
        assert ctx["suggested_layers"].get("military") is True  # military flight in view
        assert ctx["suggested_layers"].get("tracked") is True  # tracked flight in view

    def test_returns_dict_structure(self):
        """Return value has the expected top-level keys."""
        ctx = build_briefing_context(MOCK_DATA, LONDON_VIEWPORT)
        assert "counts" in ctx
        assert "notable" in ctx
        assert "suggested_layers" in ctx
        assert "summary_text" in ctx

    def test_summary_text_is_nonempty(self):
        """Summary text is a non-empty string when there's data in viewport."""
        ctx = build_briefing_context(MOCK_DATA, LONDON_VIEWPORT)
        assert isinstance(ctx["summary_text"], str)
        assert len(ctx["summary_text"]) > 10

    def test_handles_missing_data_keys(self):
        """Works with incomplete data (e.g. no ships key)."""
        partial_data = {"commercial_flights": MOCK_DATA["commercial_flights"]}
        ctx = build_briefing_context(partial_data, LONDON_VIEWPORT)
        assert ctx["counts"]["commercial_flights"] == 2
        assert ctx["counts"].get("ships", 0) == 0
