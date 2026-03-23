"""Tests for geo_gazetteer and entity search functionality (Phase 4A)."""
import pytest
import math


# ─── Gazetteer tests ──────────────────────────────────────────────────────────

class TestGeoGazetteer:
    def test_find_exact_location(self):
        from services.geo_gazetteer import find_location
        loc = find_location("strait of hormuz")
        assert loc is not None
        assert loc["name"].lower() == "strait of hormuz"
        assert 25 < loc["lat"] < 28
        assert 55 < loc["lng"] < 58

    def test_find_partial_match(self):
        from services.geo_gazetteer import find_location
        loc = find_location("hormuz")
        assert loc is not None
        assert "hormuz" in loc["name"].lower()

    def test_find_case_insensitive(self):
        from services.geo_gazetteer import find_location
        loc = find_location("BLACK SEA")
        assert loc is not None
        assert "black sea" in loc["name"].lower()

    def test_find_returns_none_for_unknown(self):
        from services.geo_gazetteer import find_location
        assert find_location("planet mars base alpha") is None

    def test_find_common_cities(self):
        from services.geo_gazetteer import find_location
        for name in ["london", "moscow", "washington", "beijing", "tokyo"]:
            loc = find_location(name)
            assert loc is not None, f"Expected to find {name}"

    def test_find_maritime_chokepoints(self):
        from services.geo_gazetteer import find_location
        for name in ["suez canal", "strait of malacca", "bosphorus", "panama canal"]:
            loc = find_location(name)
            assert loc is not None, f"Expected to find {name}"

    def test_entities_in_radius(self):
        from services.geo_gazetteer import entities_in_radius
        entities = [
            {"lat": 26.5, "lng": 56.3, "name": "ship_near"},   # ~0km from Hormuz center
            {"lat": 50.0, "lng": 0.0, "name": "ship_far"},     # thousands of km away
            {"lat": 26.6, "lng": 56.4, "name": "ship_close"},  # ~15km away
        ]
        result = entities_in_radius(entities, lat=26.5, lng=56.3, radius_km=150)
        names = [e["name"] for e in result]
        assert "ship_near" in names
        assert "ship_close" in names
        assert "ship_far" not in names

    def test_entities_in_radius_empty_list(self):
        from services.geo_gazetteer import entities_in_radius
        assert entities_in_radius([], 0, 0, 100) == []

    def test_entities_missing_coords_skipped(self):
        from services.geo_gazetteer import entities_in_radius
        entities = [
            {"name": "no_coords"},
            {"lat": 26.5, "lng": 56.3, "name": "has_coords"},
        ]
        result = entities_in_radius(entities, 26.5, 56.3, 100)
        assert len(result) == 1
        assert result[0]["name"] == "has_coords"


# ─── Entity search tests ─────────────────────────────────────────────────────

MOCK_DATA = {
    "commercial_flights": [
        {"icao24": "abc123", "callsign": "BA123", "origin_name": "LHR: London Heathrow",
         "dest_name": "CDG: Paris Charles de Gaulle", "country": "UK", "model": "A320",
         "lat": 51.0, "lng": -0.5, "alt": 35000, "airline_code": "BA"},
        {"icao24": "def456", "callsign": "AF789", "origin_name": "CDG: Paris Charles de Gaulle",
         "dest_name": "JFK: New York JFK", "country": "France", "model": "B777",
         "lat": 48.8, "lng": 2.3, "alt": 38000, "airline_code": "AF"},
        {"icao24": "ghi789", "callsign": "EZY100", "origin_name": "LGW: London Gatwick",
         "dest_name": "CDG: Paris Charles de Gaulle", "country": "UK", "model": "A319",
         "lat": 50.5, "lng": 0.5, "alt": 32000, "airline_code": "EZY"},
    ],
    "military_flights": [
        {"icao24": "mil001", "callsign": "RCH401", "country": "United States",
         "model": "C-17", "lat": 43.0, "lng": 34.0, "alt": 30000,
         "origin_name": "", "dest_name": "", "military_type": "transport"},
    ],
    "ships": [
        {"mmsi": 111111, "name": "EVER GIVEN", "type": "cargo",
         "destination": "Rotterdam", "country": "Panama", "lat": 31.0, "lng": 32.5,
         "sog": 12.5, "callsign": "VRDE7"},
        {"mmsi": 222222, "name": "FRONT ALTAIR", "type": "tanker",
         "destination": "Fujairah", "country": "Marshall Islands", "lat": 26.5, "lng": 56.3,
         "sog": 10.0, "callsign": "V7XY8"},
        {"mmsi": 333333, "name": "USS NIMITZ", "type": "carrier",
         "destination": "", "country": "United States", "lat": 26.6, "lng": 56.4,
         "sog": 15.0, "callsign": "NAVY1"},
        {"mmsi": 444444, "name": "PACIFIC TRADER", "type": "tanker",
         "destination": "Singapore", "country": "Liberia", "lat": 1.3, "lng": 103.8,
         "sog": 8.0, "callsign": "D5AA1"},
    ],
    "military_bases": [
        {"name": "Ramstein Air Base", "country": "Germany",
         "lat": 49.44, "lng": 7.60, "branch": "Air Force"},
        {"name": "Camp Humphreys", "country": "South Korea",
         "lat": 36.96, "lng": 127.03, "branch": "Army"},
    ],
    "earthquakes": [
        {"id": "eq001", "place": "Near Tokyo", "lat": 35.6, "lng": 139.7, "mag": 4.2},
    ],
}


class TestSearchEntities:
    def test_keyword_flight_by_origin(self):
        from services.llm_assistant import search_entities
        results = search_entities("flights from London", MOCK_DATA)
        flights = results.get("commercial_flights", [])
        assert len(flights) >= 1
        callsigns = [f["callsign"] for f in flights]
        assert "BA123" in callsigns  # LHR: London Heathrow
        assert "EZY100" in callsigns  # LGW: London Gatwick

    def test_keyword_flight_by_destination(self):
        from services.llm_assistant import search_entities
        results = search_entities("flights to Paris", MOCK_DATA)
        flights = results.get("commercial_flights", [])
        assert len(flights) >= 1
        callsigns = [f["callsign"] for f in flights]
        assert "BA123" in callsigns  # dest: CDG Paris

    def test_combined_origin_and_destination(self):
        from services.llm_assistant import search_entities
        results = search_entities("flights from London to Paris", MOCK_DATA)
        flights = results.get("commercial_flights", [])
        # Both BA123 and EZY100 go London→Paris
        callsigns = [f["callsign"] for f in flights]
        assert "BA123" in callsigns
        assert "EZY100" in callsigns

    def test_specific_callsign(self):
        from services.llm_assistant import search_entities
        results = search_entities("BA123", MOCK_DATA)
        flights = results.get("commercial_flights", [])
        assert len(flights) >= 1
        assert flights[0]["callsign"] == "BA123"

    def test_ship_by_name(self):
        from services.llm_assistant import search_entities
        results = search_entities("USS Nimitz", MOCK_DATA)
        ships = results.get("ships", [])
        assert len(ships) >= 1
        assert any(s["name"] == "USS NIMITZ" for s in ships)

    def test_geographic_search_tankers_near_hormuz(self):
        from services.llm_assistant import search_entities
        results = search_entities("oil tankers near Strait of Hormuz", MOCK_DATA)
        ships = results.get("ships", [])
        # FRONT ALTAIR is a tanker at ~26.5, 56.3 (right at Hormuz)
        # PACIFIC TRADER is a tanker at Singapore — too far
        names = [s["name"] for s in ships]
        assert "FRONT ALTAIR" in names
        assert "PACIFIC TRADER" not in names

    def test_geographic_search_military_ships_in_area(self):
        from services.llm_assistant import search_entities
        results = search_entities("military ships in the Persian Gulf", MOCK_DATA)
        ships = results.get("ships", [])
        # USS NIMITZ is carrier at 26.6, 56.4 — near Persian Gulf
        names = [s["name"] for s in ships]
        assert "USS NIMITZ" in names

    def test_military_base_by_country(self):
        from services.llm_assistant import search_entities
        results = search_entities("military bases in Germany", MOCK_DATA)
        bases = results.get("military_bases", [])
        assert len(bases) >= 1
        assert bases[0]["name"] == "Ramstein Air Base"

    def test_empty_query_returns_empty(self):
        from services.llm_assistant import search_entities
        results = search_entities("", MOCK_DATA)
        # Should have no entity lists (only meta keys)
        entity_lists = {k: v for k, v in results.items() if not k.startswith("_") and v}
        assert len(entity_lists) == 0

    def test_cap_at_100_per_category(self):
        from services.llm_assistant import search_entities
        # Create data with 200 flights matching "test"
        big_data = {
            "commercial_flights": [
                {"icao24": f"id{i}", "callsign": f"TEST{i}", "origin_name": "test",
                 "dest_name": "test", "country": "test", "model": "test",
                 "lat": 0, "lng": 0, "alt": 0, "airline_code": "TST"}
                for i in range(200)
            ]
        }
        results = search_entities("test", big_data)
        assert len(results.get("commercial_flights", [])) <= 100

    def test_totals_track_full_match_count(self):
        from services.llm_assistant import search_entities
        big_data = {
            "commercial_flights": [
                {"icao24": f"id{i}", "callsign": f"TEST{i}", "origin_name": "test",
                 "dest_name": "test", "country": "test", "model": "test",
                 "lat": 0, "lng": 0, "alt": 0, "airline_code": "TST"}
                for i in range(200)
            ]
        }
        results = search_entities("test", big_data)
        assert results.get("_totals", {}).get("commercial_flights") == 200

    def test_returns_compact_flight_format(self):
        from services.llm_assistant import search_entities
        results = search_entities("BA123", MOCK_DATA)
        flight = results["commercial_flights"][0]
        # Should have compact fields
        assert "icao24" in flight
        assert "callsign" in flight
        assert "origin_name" in flight
        assert "dest_name" in flight
        assert "lat" in flight
        assert "lng" in flight

    def test_returns_compact_ship_format(self):
        from services.llm_assistant import search_entities
        results = search_entities("Ever Given", MOCK_DATA)
        ship = results["ships"][0]
        assert "mmsi" in ship
        assert "name" in ship
        assert "type" in ship
        assert "lat" in ship
        assert "lng" in ship

    def test_scoring_exact_match_ranks_higher(self):
        from services.llm_assistant import search_entities
        results = search_entities("BA123", MOCK_DATA)
        flights = results.get("commercial_flights", [])
        # BA123 should be first (exact callsign match)
        assert flights[0]["callsign"] == "BA123"
