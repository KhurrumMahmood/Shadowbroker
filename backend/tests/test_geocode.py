"""Tests for GET /api/geocode and expanded gazetteer."""


class TestGeocodeEndpoint:
    def test_exact_match(self, client):
        r = client.get("/api/geocode?q=karachi")
        assert r.status_code == 200
        data = r.json()
        assert len(data["results"]) >= 1
        assert data["results"][0]["name"].lower() == "karachi"

    def test_substring_match(self, client):
        r = client.get("/api/geocode?q=kara")
        assert r.status_code == 200
        names = [m["name"].lower() for m in r.json()["results"]]
        assert any("karachi" in n for n in names)

    def test_empty_query(self, client):
        r = client.get("/api/geocode?q=")
        assert r.status_code == 200
        assert r.json()["results"] == []

    def test_short_query(self, client):
        r = client.get("/api/geocode?q=a")
        assert r.status_code == 200
        assert r.json()["results"] == []

    def test_no_query_param(self, client):
        r = client.get("/api/geocode")
        assert r.status_code == 200
        assert r.json()["results"] == []

    def test_max_8_results(self, client):
        """Even broad queries should cap at 8 results."""
        r = client.get("/api/geocode?q=strait")
        assert r.status_code == 200
        assert len(r.json()["results"]) <= 8

    def test_result_has_required_fields(self, client):
        r = client.get("/api/geocode?q=london")
        data = r.json()
        assert len(data["results"]) >= 1
        loc = data["results"][0]
        assert "name" in loc
        assert "lat" in loc
        assert "lng" in loc
        assert "radius_km" in loc

    def test_case_insensitive(self, client):
        r1 = client.get("/api/geocode?q=Bangkok")
        r2 = client.get("/api/geocode?q=bangkok")
        assert r1.json()["results"][0]["name"] == r2.json()["results"][0]["name"]


class TestGazetteerCoverage:
    """Spot-check that major cities exist in the expanded gazetteer."""

    def test_south_asia_cities(self):
        from services.geo_gazetteer import STRATEGIC_LOCATIONS
        for city in ["karachi", "lahore", "islamabad", "dhaka", "colombo"]:
            assert city in STRATEGIC_LOCATIONS, f"{city} missing"

    def test_southeast_asia_cities(self):
        from services.geo_gazetteer import STRATEGIC_LOCATIONS
        for city in ["bangkok", "jakarta", "manila", "kuala lumpur"]:
            assert city in STRATEGIC_LOCATIONS, f"{city} missing"

    def test_americas_cities(self):
        from services.geo_gazetteer import STRATEGIC_LOCATIONS
        for city in ["chicago", "houston", "toronto", "bogota"]:
            assert city in STRATEGIC_LOCATIONS, f"{city} missing"

    def test_europe_cities(self):
        from services.geo_gazetteer import STRATEGIC_LOCATIONS
        for city in ["madrid", "amsterdam", "vienna", "prague", "stockholm"]:
            assert city in STRATEGIC_LOCATIONS, f"{city} missing"

    def test_africa_cities(self):
        from services.geo_gazetteer import STRATEGIC_LOCATIONS
        for city in ["accra", "kinshasa", "khartoum", "cape town"]:
            assert city in STRATEGIC_LOCATIONS, f"{city} missing"

    def test_middle_east_cities(self):
        from services.geo_gazetteer import STRATEGIC_LOCATIONS
        for city in ["doha", "jeddah", "amman", "beirut"]:
            assert city in STRATEGIC_LOCATIONS, f"{city} missing"

    def test_total_entries_over_250(self):
        from services.geo_gazetteer import STRATEGIC_LOCATIONS
        assert len(STRATEGIC_LOCATIONS) >= 250
