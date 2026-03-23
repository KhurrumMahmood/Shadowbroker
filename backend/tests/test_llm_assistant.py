"""Tests for llm_assistant search and parsing utilities."""
import pytest
from services.llm_assistant import (
    _parse_directional_hints,
    search_entities,
    parse_llm_response,
)


class TestParseDirectionalHints:
    def test_from_to(self):
        h = _parse_directional_hints("flights from London to New York")
        assert "london" in h["origin_terms"]
        assert "york" in h["dest_terms"] or "new" in h["dest_terms"]

    def test_out_of(self):
        h = _parse_directional_hints("flights out of Heathrow to Paris")
        assert "heathrow" in h["origin_terms"]
        assert "paris" in h["dest_terms"]

    def test_departing_heading(self):
        h = _parse_directional_hints("departing Tokyo heading to Sydney")
        assert "tokyo" in h["origin_terms"]
        assert "sydney" in h["dest_terms"]

    def test_bound_for(self):
        h = _parse_directional_hints("ships bound for Rotterdam")
        assert "rotterdam" in h["dest_terms"]

    def test_leaving(self):
        h = _parse_directional_hints("leaving Berlin to Munich")
        assert "berlin" in h["origin_terms"]
        assert "munich" in h["dest_terms"]

    def test_no_direction(self):
        h = _parse_directional_hints("show me military flights")
        assert h["origin_terms"] == []
        assert h["dest_terms"] == []

    def test_only_destination(self):
        h = _parse_directional_hints("flights going to JFK")
        assert h["origin_terms"] == []
        assert "jfk" in h["dest_terms"]

    def test_only_origin(self):
        h = _parse_directional_hints("flights from LAX")
        assert "lax" in h["origin_terms"]


class TestSearchEntitiesDirectional:
    """Verify directional hints boost the right entities."""

    FLIGHTS = [
        {"callsign": "BA100", "icao24": "a1", "origin_name": "LHR: London Heathrow",
         "dest_name": "JFK: John F Kennedy", "country": "UK", "model": "B777",
         "lat": 51.47, "lng": -0.46, "alt": 10000, "registration": "G-ABCD",
         "airline_code": "BAW"},
        {"callsign": "AA200", "icao24": "a2", "origin_name": "JFK: John F Kennedy",
         "dest_name": "LHR: London Heathrow", "country": "US", "model": "B787",
         "lat": 40.6, "lng": -73.7, "alt": 11000, "registration": "N-1234",
         "airline_code": "AAL"},
        {"callsign": "LH300", "icao24": "a3", "origin_name": "FRA: Frankfurt",
         "dest_name": "CDG: Paris Charles de Gaulle", "country": "DE", "model": "A320",
         "lat": 49.0, "lng": 8.5, "alt": 9000, "registration": "D-ABCD",
         "airline_code": "DLH"},
    ]

    def test_from_london_boosts_origin(self):
        data = {"commercial_flights": self.FLIGHTS}
        results = search_entities("flights from London to JFK", data)
        ids = [e["icao24"] for e in results.get("commercial_flights", [])]
        # BA100 (origin=London, dest=JFK) should rank above AA200 (dest=London)
        assert "a1" in ids
        if "a2" in ids:
            assert ids.index("a1") < ids.index("a2")

    def test_to_london_boosts_destination(self):
        data = {"commercial_flights": self.FLIGHTS}
        results = search_entities("flights to London", data)
        ids = [e["icao24"] for e in results.get("commercial_flights", [])]
        # AA200 (dest=London) should rank above BA100 (origin=London)
        assert "a2" in ids
        if "a1" in ids:
            assert ids.index("a2") < ids.index("a1")

    def test_no_direction_matches_both(self):
        data = {"commercial_flights": self.FLIGHTS}
        results = search_entities("London flights", data)
        ids = [e["icao24"] for e in results.get("commercial_flights", [])]
        assert "a1" in ids
        assert "a2" in ids

    def test_unrelated_excluded(self):
        data = {"commercial_flights": self.FLIGHTS}
        results = search_entities("flights from London to JFK", data)
        ids = [e["icao24"] for e in results.get("commercial_flights", [])]
        # Frankfurt→Paris flight shouldn't match
        assert "a3" not in ids


class TestParseLlmResponse:
    def test_valid_json(self):
        raw = '{"summary": "Found 3 flights.", "layers": {"flights": true}}'
        r = parse_llm_response(raw)
        assert r["summary"] == "Found 3 flights."
        assert r["layers"] == {"flights": True}

    def test_markdown_fence(self):
        raw = '```json\n{"summary": "test"}\n```'
        r = parse_llm_response(raw)
        assert r["summary"] == "test"

    def test_truncated_json_salvages_summary(self):
        raw = '{"summary": "Found 88 flights near London.", "layers": {"flights": true}, "result_entities": [{"type": "flight", "id": "abc'
        r = parse_llm_response(raw)
        assert "88 flights" in r["summary"]
        assert r["result_entities"] == []

    def test_garbage_returns_raw(self):
        raw = "I cannot help with that request."
        r = parse_llm_response(raw)
        assert "cannot help" in r["summary"]

    def test_clamps_viewport(self):
        raw = '{"summary": "ok", "viewport": {"lat": 200, "lng": -300, "zoom": 50}}'
        r = parse_llm_response(raw)
        assert r["viewport"]["lat"] == 90
        assert r["viewport"]["lng"] == -180
        assert r["viewport"]["zoom"] == 20

    def test_filters_unknown_layers(self):
        raw = '{"summary": "ok", "layers": {"flights": true, "bogus_layer": true}}'
        r = parse_llm_response(raw)
        assert "flights" in r["layers"]
        assert "bogus_layer" not in r["layers"]

    def test_result_entities_max_50(self):
        entities = [{"type": "flight", "id": str(i)} for i in range(60)]
        import json
        raw = json.dumps({"summary": "ok", "result_entities": entities})
        r = parse_llm_response(raw)
        assert len(r["result_entities"]) == 50
