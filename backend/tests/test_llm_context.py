"""Tests for _current_situation_section() in llm_assistant.py."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.llm_assistant import _current_situation_section


class TestCurrentSituationSection:
    """Test CURRENT SITUATION block generation for LLM system prompt."""

    def test_headlines_rendered(self):
        summary = {
            "top_headlines": [
                {"title": "War in region X", "source": "Reuters", "risk_score": 9},
                {"title": "Peace talks", "source": "BBC", "risk_score": 3},
            ]
        }
        result = _current_situation_section(summary)
        assert "CURRENT SITUATION:" in result
        assert "TOP HEADLINES" in result
        assert "[9] War in region X (Reuters)" in result
        assert "[3] Peace talks (BBC)" in result

    def test_markets_rendered(self):
        summary = {
            "markets": {
                "stocks": {"SPY": {"price": 450.0, "change": 1.2}},
                "oil": {"WTI": {"price": 78.5, "change": -0.3}},
            }
        }
        result = _current_situation_section(summary)
        assert "MARKETS:" in result
        assert "SPY: $450.0 (+1.2%)" in result
        assert "WTI: $78.5 (-0.3%)" in result

    def test_markets_zero_change_no_plus(self):
        summary = {
            "markets": {
                "stocks": {"FLAT": {"price": 100.0, "change": 0}},
                "oil": {},
            }
        }
        result = _current_situation_section(summary)
        assert "FLAT: $100.0 (0%)" in result

    def test_coverage_gaps_rendered(self):
        summary = {
            "coverage_gaps_count": 15,
            "top_coverage_gaps": [
                {"lat": 10.0, "lon": 20.0, "gdelt_count": 25, "top_event_codes": ["14", "19"]},
            ]
        }
        result = _current_situation_section(summary)
        assert "COVERAGE GAPS (15 total" in result
        assert "(10.0, 20.0): 25 events" in result

    def test_correlations_rendered(self):
        summary = {
            "correlations_count": 5,
            "top_correlations": [
                {"type": "military_near_conflict", "entity": "DUKE01", "distance_km": 150, "gdelt_count": 8},
            ]
        }
        result = _current_situation_section(summary)
        assert "CROSS-DOMAIN CORRELATIONS (5 total)" in result
        assert "military_near_conflict: DUKE01 within 150km" in result

    def test_disease_outbreaks_rendered(self):
        summary = {
            "disease_outbreaks": 3,
            "recent_outbreaks": [
                {"disease": "Ebola", "country": "Uganda", "date": "2026-03-01"},
            ]
        }
        result = _current_situation_section(summary)
        assert "DISEASE OUTBREAKS (3 total)" in result
        assert "Ebola" in result
        assert "Uganda" in result

    def test_empty_summary_returns_empty(self):
        result = _current_situation_section({})
        assert result == ""

    def test_partial_data(self):
        """Only headlines, no other sections."""
        summary = {
            "top_headlines": [
                {"title": "Breaking news", "source": "AP", "risk_score": 7},
            ]
        }
        result = _current_situation_section(summary)
        assert "CURRENT SITUATION:" in result
        assert "TOP HEADLINES" in result
        assert "MARKETS:" not in result
        assert "COVERAGE GAPS" not in result
