"""Tests for news/GDELT/fires/outbreaks in _SEARCH_CONFIG and _QUERYABLE_FIELDS."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.llm_assistant import search_entities, _QUERYABLE_FIELDS, _FIELDS_BLOCK


class TestSearchNews:
    """Test that news items are searchable by the LLM."""

    def test_search_news_by_title(self):
        data = {
            "news": [
                {"id": 1, "title": "Ukraine conflict escalates", "source": "Reuters",
                 "risk_score": 8, "lat": 50.0, "lng": 30.0, "summary": "..."},
                {"id": 2, "title": "Local weather update", "source": "BBC",
                 "risk_score": 1, "lat": 51.0, "lng": -0.1, "summary": "..."},
            ]
        }
        result = search_entities("ukraine", data)
        assert "news" in result
        assert result["news"][0]["title"] == "Ukraine conflict escalates"

    def test_search_news_by_source(self):
        data = {
            "news": [
                {"id": 1, "title": "Story A", "source": "Reuters",
                 "risk_score": 5, "lat": 10.0, "lng": 20.0, "summary": "..."},
            ]
        }
        result = search_entities("reuters", data)
        assert "news" in result


class TestSearchGDELT:
    """Test that GDELT GeoJSON Feature items are searchable."""

    def test_search_gdelt_by_name(self):
        data = {
            "gdelt": [
                {
                    "type": "Feature",
                    "properties": {"name": "Sudan conflict zone", "count": 15, "action_geo_cc": "SD"},
                    "geometry": {"type": "Point", "coordinates": [32.0, 15.0]},
                },
                {
                    "type": "Feature",
                    "properties": {"name": "Ukraine border", "count": 8, "action_geo_cc": "UA"},
                    "geometry": {"type": "Point", "coordinates": [30.0, 50.0]},
                },
            ]
        }
        result = search_entities("sudan", data)
        assert "gdelt" in result
        assert result["gdelt"][0]["name"] == "Sudan conflict zone"

    def test_search_gdelt_compact_extracts_coords(self):
        data = {
            "gdelt": [
                {
                    "type": "Feature",
                    "properties": {"name": "Test zone", "count": 5, "action_geo_cc": "XX"},
                    "geometry": {"type": "Point", "coordinates": [35.0, 10.0]},
                },
            ]
        }
        result = search_entities("test zone", data)
        assert "gdelt" in result
        # GeoJSON [lon, lat] → compact should have lat=10, lng=35
        assert result["gdelt"][0]["lat"] == 10.0
        assert result["gdelt"][0]["lng"] == 35.0


class TestSearchFires:
    """Test that FIRMS fire data is searchable."""

    def test_search_fires_by_date(self):
        data = {
            "firms_fires": [
                {"lat": 10.0, "lng": 20.0, "frp": 50, "confidence": "high",
                 "acq_date": "2026-03-25", "daynight": "D"},
                {"lat": 30.0, "lng": 40.0, "frp": 10, "confidence": "low",
                 "acq_date": "2026-03-24", "daynight": "N"},
            ]
        }
        result = search_entities("2026-03-25", data)
        assert "firms_fires" in result

    def test_search_fires_by_confidence(self):
        data = {
            "firms_fires": [
                {"lat": 10.0, "lng": 20.0, "frp": 50, "confidence": "high",
                 "acq_date": "2026-03-25", "daynight": "D"},
            ]
        }
        result = search_entities("high confidence", data)
        assert "firms_fires" in result


class TestQueryableFields:
    """Test that new categories appear in _QUERYABLE_FIELDS and _FIELDS_BLOCK."""

    def test_news_in_queryable_fields(self):
        assert "news" in _QUERYABLE_FIELDS
        assert "title" in _QUERYABLE_FIELDS["news"]

    def test_gdelt_in_queryable_fields(self):
        assert "gdelt" in _QUERYABLE_FIELDS

    def test_firms_fires_in_queryable_fields(self):
        assert "firms_fires" in _QUERYABLE_FIELDS

    def test_disease_outbreaks_in_queryable_fields(self):
        assert "disease_outbreaks" in _QUERYABLE_FIELDS

    def test_fields_block_includes_new_categories(self):
        assert "news:" in _FIELDS_BLOCK
        assert "gdelt:" in _FIELDS_BLOCK
        assert "firms_fires:" in _FIELDS_BLOCK
        assert "disease_outbreaks:" in _FIELDS_BLOCK


class TestCompactIdsForResultEntities:
    """Compact formats must include an 'id' field so the LLM can emit
    result_entities that the frontend can resolve."""

    def test_fire_compact_has_coordinate_id(self):
        from services.llm_assistant import _SEARCH_CONFIG
        compact = _SEARCH_CONFIG["firms_fires"]["compact"]
        fire = {"lat": 26.5, "lng": 56.3, "frp": 100, "confidence": "high", "acq_date": "2026-03-28"}
        result = compact(fire)
        assert "id" in result, "Fire compact format must include an 'id' field"
        assert result["id"] == "26.5,56.3"

    def test_gdelt_compact_has_coordinate_id(self):
        from services.llm_assistant import _SEARCH_CONFIG
        compact = _SEARCH_CONFIG["gdelt"]["compact"]
        gdelt_item = {
            "type": "Feature",
            "properties": {"name": "Test zone", "count": 5, "action_geo_cc": "XX"},
            "geometry": {"type": "Point", "coordinates": [35.0, 10.0]},
        }
        result = compact(gdelt_item)
        assert "id" in result, "GDELT compact format must include an 'id' field"
        assert result["id"] == "10.0,35.0"  # lat,lng from GeoJSON [lng,lat]

    def test_fire_search_result_uses_coordinate_id(self):
        """Search results rendered for the LLM should show coordinate IDs for fires."""
        data = {
            "firms_fires": [
                {"lat": 34.1, "lng": -118.2, "frp": 50, "confidence": "high",
                 "acq_date": "2026-03-28", "daynight": "D"},
            ]
        }
        result = search_entities("2026-03-28", data)
        assert "firms_fires" in result
        # The compact output must have a coordinate-based id
        assert result["firms_fires"][0].get("id") == "34.1,-118.2"
