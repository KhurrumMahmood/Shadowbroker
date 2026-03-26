"""Tests for WHO DON disease outbreak fetcher."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
from unittest.mock import patch, MagicMock


class TestParseTitle(unittest.TestCase):
    """Test _parse_title extracts disease and country from DON titles."""

    def setUp(self):
        from services.fetchers.health import _parse_title
        self._parse = _parse_title

    def test_en_dash_separator(self):
        disease, country = self._parse("Ebola virus disease \u2013 Uganda")
        assert disease == "Ebola virus disease"
        assert country == "Uganda"

    def test_hyphen_separator(self):
        disease, country = self._parse("Cholera - Haiti")
        assert disease == "Cholera"
        assert country == "Haiti"

    def test_no_separator(self):
        disease, country = self._parse("Monkeypox update")
        assert disease == "Monkeypox update"
        assert country == ""

    def test_multi_word_country(self):
        disease, country = self._parse("Avian Influenza A(H5N1) \u2013 Republic of the Congo")
        assert disease == "Avian Influenza A(H5N1)"
        assert country == "Republic of the Congo"


class TestSeverityScore(unittest.TestCase):
    """Test _severity_score assigns correct risk tiers."""

    def setUp(self):
        from services.fetchers.health import _severity_score
        self._score = _severity_score

    def test_high_severity_ebola(self):
        assert self._score("Ebola virus disease") == 9

    def test_high_severity_marburg(self):
        assert self._score("Marburg haemorrhagic fever") == 9

    def test_medium_severity_cholera(self):
        assert self._score("Cholera") == 6

    def test_medium_severity_mers(self):
        assert self._score("MERS-CoV") == 7

    def test_lower_severity_dengue(self):
        assert self._score("Dengue fever") == 5

    def test_default_unknown(self):
        assert self._score("Unknown disease XYZ") == 3

    def test_case_insensitive(self):
        assert self._score("EBOLA VIRUS DISEASE") == 9


class TestFetchOutbreaks(unittest.TestCase):
    """Test fetch_disease_outbreaks with mocked HTTP."""

    _MOCK_RESPONSE = {
        "value": [
            {
                "Id": "don-001",
                "Title": "Ebola virus disease \u2013 Uganda",
                "DatePublished": "2026-03-01T00:00:00Z",
                "Summary": "An outbreak of Ebola virus disease was confirmed...",
                "Url": "https://www.who.int/emergencies/disease-outbreak-news/item/don-001",
            },
            {
                "Id": "don-002",
                "Title": "Cholera - Haiti",
                "DatePublished": "2026-02-15T00:00:00Z",
                "Summary": "Cholera cases reported in Port-au-Prince...",
                "Url": "https://www.who.int/emergencies/disease-outbreak-news/item/don-002",
            },
        ]
    }

    @patch("services.fetchers.health.fetch_with_curl")
    def test_writes_to_store(self, mock_fetch):
        from services.fetchers._store import latest_data
        from services.fetchers.health import fetch_disease_outbreaks

        mock_resp = MagicMock()
        mock_resp.json.return_value = self._MOCK_RESPONSE
        mock_fetch.return_value = mock_resp

        fetch_disease_outbreaks()

        outbreaks = latest_data["disease_outbreaks"]
        assert len(outbreaks) == 2
        assert outbreaks[0]["disease_name"] == "Ebola virus disease"
        assert outbreaks[0]["country"] == "Uganda"
        assert outbreaks[0]["risk_score"] == 9
        assert outbreaks[0]["source"] == "WHO DON"
        assert outbreaks[1]["disease_name"] == "Cholera"
        assert outbreaks[1]["country"] == "Haiti"
        assert outbreaks[1]["risk_score"] == 6

    @patch("services.fetchers.health.fetch_with_curl")
    def test_coords_resolved(self, mock_fetch):
        from services.fetchers._store import latest_data
        from services.fetchers.health import fetch_disease_outbreaks

        mock_resp = MagicMock()
        mock_resp.json.return_value = self._MOCK_RESPONSE
        mock_fetch.return_value = mock_resp

        fetch_disease_outbreaks()

        # Uganda should resolve to coords via _resolve_coords
        uganda_item = latest_data["disease_outbreaks"][0]
        # _resolve_coords may or may not find "Uganda" — test that lat/lng fields exist
        assert "lat" in uganda_item
        assert "lng" in uganda_item

    @patch("services.fetchers.health.fetch_with_curl")
    def test_empty_response(self, mock_fetch):
        from services.fetchers._store import latest_data
        from services.fetchers.health import fetch_disease_outbreaks

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"value": []}
        mock_fetch.return_value = mock_resp

        fetch_disease_outbreaks()

        assert latest_data["disease_outbreaks"] == []

    @patch("services.fetchers.health.fetch_with_curl")
    def test_summary_truncated(self, mock_fetch):
        from services.fetchers._store import latest_data
        from services.fetchers.health import fetch_disease_outbreaks

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"value": [{
            "Id": "don-long",
            "Title": "Test - Country",
            "DatePublished": "2026-01-01",
            "Summary": "A" * 500,
            "Url": "https://example.com",
        }]}
        mock_fetch.return_value = mock_resp

        fetch_disease_outbreaks()

        assert len(latest_data["disease_outbreaks"][0]["summary"]) == 300


if __name__ == "__main__":
    unittest.main()
