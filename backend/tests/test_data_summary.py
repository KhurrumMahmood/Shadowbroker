"""Tests for _build_data_summary() rich context in main.py."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import _build_data_summary


class TestBuildDataSummary:
    """Test _build_data_summary returns rich context for LLM."""

    # ── existing behaviour: counts ─────────────────────────────────
    def test_summary_counts_basic(self):
        data = {"ships": [{"name": "A"}, {"name": "B"}], "earthquakes": [{"id": 1}]}
        s = _build_data_summary(data)
        assert s["ships"] == 2
        assert s["earthquakes"] == 1

    # ── top headlines ──────────────────────────────────────────────
    def test_summary_includes_top_headlines(self):
        news = [
            {"title": "Low risk", "source": "BBC", "risk_score": 2},
            {"title": "High risk", "source": "Reuters", "risk_score": 9},
            {"title": "Medium risk", "source": "AP", "risk_score": 5},
        ]
        s = _build_data_summary({"news": news})
        assert "top_headlines" in s
        assert s["top_headlines"][0]["title"] == "High risk"
        assert s["top_headlines"][0]["risk_score"] == 9
        assert len(s["top_headlines"]) == 3

    def test_summary_headlines_max_10(self):
        news = [{"title": f"Item {i}", "source": "X", "risk_score": i} for i in range(20)]
        s = _build_data_summary({"news": news})
        assert len(s["top_headlines"]) == 10
        assert s["top_headlines"][0]["risk_score"] == 19

    # ── markets ────────────────────────────────────────────────────
    def test_summary_includes_markets(self):
        data = {
            "stocks": {"SPY": {"price": 450.0, "change_percent": 1.2}},
            "oil": {"WTI": {"price": 78.5, "change_percent": -0.3}},
        }
        s = _build_data_summary(data)
        assert "markets" in s
        assert s["markets"]["stocks"]["SPY"]["price"] == 450.0
        assert s["markets"]["stocks"]["SPY"]["change"] == 1.2
        assert s["markets"]["oil"]["WTI"]["price"] == 78.5
        assert s["markets"]["oil"]["WTI"]["change"] == -0.3

    # ── coverage gaps ──────────────────────────────────────────────
    def test_summary_includes_coverage_gaps(self):
        gaps = [
            {"lat": 10, "lon": 20, "gdelt_count": 5, "top_event_codes": ["14"]},
            {"lat": 30, "lon": 40, "gdelt_count": 15, "top_event_codes": ["19"]},
            {"lat": 50, "lon": 60, "gdelt_count": 10, "top_event_codes": ["18"]},
        ]
        s = _build_data_summary({"coverage_gaps": gaps})
        assert "top_coverage_gaps" in s
        assert s["top_coverage_gaps"][0]["gdelt_count"] == 15
        assert s["top_coverage_gaps"][0]["lat"] == 30

    def test_summary_coverage_gaps_max_5(self):
        gaps = [{"lat": i, "lon": i, "gdelt_count": i, "top_event_codes": []} for i in range(10)]
        s = _build_data_summary({"coverage_gaps": gaps})
        assert len(s["top_coverage_gaps"]) == 5

    # ── correlations ───────────────────────────────────────────────
    def test_summary_includes_correlations(self):
        corrs = [
            {"type": "military_near_conflict", "distance_km": 100,
             "entity": {"flight": "DUKE01", "type": "C-17", "operator": "US"}, "gdelt_count": 8},
            {"type": "outage_near_conflict", "distance_km": 50, "entity_name": "Sudan", "gdelt_count": 12},
        ]
        s = _build_data_summary({"correlations": corrs})
        assert "top_correlations" in s
        assert len(s["top_correlations"]) == 2
        assert s["top_correlations"][0]["entity"] == "DUKE01"
        assert s["top_correlations"][1]["entity"] == "Sudan"

    def test_summary_correlations_max_3(self):
        corrs = [{"type": "t", "distance_km": 1, "conflict_location": f"C{i}", "gdelt_count": 1} for i in range(10)]
        s = _build_data_summary({"correlations": corrs})
        assert len(s["top_correlations"]) == 3

    # ── disease outbreaks ──────────────────────────────────────────
    def test_summary_includes_disease_outbreaks(self):
        outbreaks = [
            {"disease_name": "Ebola", "country": "Uganda", "pub_date": "2026-03-01"},
            {"disease_name": "Cholera", "country": "Haiti", "pub_date": "2026-02-15"},
        ]
        s = _build_data_summary({"disease_outbreaks": outbreaks})
        assert s["disease_outbreaks"] == 2
        assert "recent_outbreaks" in s
        assert s["recent_outbreaks"][0]["disease"] == "Ebola"

    # ── empty data ─────────────────────────────────────────────────
    def test_summary_empty_data(self):
        s = _build_data_summary({})
        assert "top_headlines" not in s
        assert "markets" not in s
        assert "top_coverage_gaps" not in s
        assert "top_correlations" not in s
        assert "recent_outbreaks" not in s

    def test_summary_empty_lists(self):
        s = _build_data_summary({
            "news": [], "stocks": {}, "oil": {},
            "coverage_gaps": [], "correlations": [], "disease_outbreaks": [],
        })
        assert "top_headlines" not in s
        assert "markets" not in s
        assert "top_coverage_gaps" not in s
        assert "top_correlations" not in s
        assert "recent_outbreaks" not in s
