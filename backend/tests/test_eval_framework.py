"""Tests for the eval framework scoring functions and report generation."""
import pytest

from services.agent.eval import (
    EvalResult,
    AgentResponse,
    score_mentions,
    score_sources,
    score_judgment,
    score_entities,
    evaluate,
    format_eval_report,
)


# ── score_mentions ────────────────────────────────────────────────────


class TestScoreMentions:

    def test_all_mentioned(self):
        text = "There are 5 tankers near Hormuz with GPS jamming detected. Oil prices spiking."
        assert score_mentions(text, ["tanker", "Hormuz", "GPS jamming", "oil"]) == 1.0

    def test_none_mentioned(self):
        text = "Everything is normal today."
        assert score_mentions(text, ["tanker", "Hormuz", "GPS jamming"]) == 0.0

    def test_partial_mentions(self):
        text = "There are tankers near the strait."
        score = score_mentions(text, ["tanker", "Hormuz", "GPS jamming", "oil"])
        assert score == pytest.approx(0.25)

    def test_case_insensitive(self):
        text = "TANKER activity near HORMUZ"
        assert score_mentions(text, ["tanker", "hormuz"]) == 1.0

    def test_empty_required(self):
        assert score_mentions("anything", []) == 1.0

    def test_empty_text(self):
        assert score_mentions("", ["tanker"]) == 0.0


# ── score_sources ─────────────────────────────────────────────────────


class TestScoreSources:

    def test_all_queried(self):
        assert score_sources(
            ["ships", "military_flights", "news"],
            ["ships", "military_flights", "news"],
        ) == 1.0

    def test_none_queried(self):
        assert score_sources([], ["ships", "military_flights"]) == 0.0

    def test_partial_match(self):
        score = score_sources(
            ["ships", "earthquakes"],
            ["ships", "military_flights", "news", "earthquakes"],
        )
        assert score == pytest.approx(0.5)

    def test_extra_sources_ok(self):
        """Querying extra sources beyond required shouldn't penalize."""
        assert score_sources(
            ["ships", "military_flights", "news", "gdelt", "satellites"],
            ["ships", "military_flights"],
        ) == 1.0

    def test_empty_required(self):
        assert score_sources(["ships"], []) == 1.0


# ── score_judgment ────────────────────────────────────────────────────


class TestScoreJudgment:

    def test_within_range(self):
        assert score_judgment(8.0, [6, 10]) == 1.0

    def test_at_lower_bound(self):
        assert score_judgment(6.0, [6, 10]) == 1.0

    def test_at_upper_bound(self):
        assert score_judgment(10.0, [6, 10]) == 1.0

    def test_slightly_outside(self):
        assert score_judgment(4.0, [6, 10]) == 0.5

    def test_far_outside(self):
        assert score_judgment(1.0, [6, 10]) == 0.0

    def test_none_with_low_range(self):
        """No risk assessment is OK if expected range starts at 0-1."""
        assert score_judgment(None, [0, 3]) == 1.0

    def test_none_with_high_range(self):
        """No risk assessment is bad if expected range requires high values."""
        assert score_judgment(None, [6, 10]) == 0.0


# ── score_entities ────────────────────────────────────────────────────


class TestScoreEntities:

    def test_all_present(self):
        assert score_entities(
            ["ship", "military_flight", "earthquake"],
            ["ship", "military_flight"],
        ) == 1.0

    def test_none_present(self):
        assert score_entities([], ["ship", "military_flight"]) == 0.0

    def test_partial(self):
        score = score_entities(["ship"], ["ship", "military_flight"])
        assert score == pytest.approx(0.5)

    def test_empty_required(self):
        assert score_entities(["ship"], []) == 1.0


# ── evaluate ──────────────────────────────────────────────────────────


class TestEvaluate:

    def test_perfect_response(self):
        response = AgentResponse(
            summary="There are 5 tankers near Hormuz with GPS jamming. Oil prices are up.",
            risk_level=8.0,
            queried_categories=["ships", "military_flights", "news", "gps_jamming"],
            returned_entity_types=["ship", "military_flight"],
            latency=3.5,
            llm_calls=2,
        )
        expected = {
            "required_mentions": ["tanker", "Hormuz", "GPS jamming", "oil"],
            "required_data_sources_queried": ["ships", "military_flights", "news", "gps_jamming"],
            "risk_level_range": [7, 10],
            "must_include_entity_types": ["ship", "military_flight"],
            "max_latency_seconds": 10.0,
        }
        result = evaluate("hormuz_crisis", "Is Hormuz at risk?", response, expected)
        assert result.score == pytest.approx(1.0)
        assert result.mentions_score == 1.0
        assert result.sources_score == 1.0
        assert result.judgment_score == 1.0
        assert result.entity_score == 1.0
        assert result.details["latency_ok"] is True

    def test_poor_response(self):
        response = AgentResponse(
            summary="I don't have enough information.",
            risk_level=2.0,
            queried_categories=["news"],
            returned_entity_types=[],
            latency=1.0,
        )
        expected = {
            "required_mentions": ["tanker", "Hormuz", "GPS jamming", "oil"],
            "required_data_sources_queried": ["ships", "military_flights", "news", "gps_jamming"],
            "risk_level_range": [7, 10],
            "must_include_entity_types": ["ship", "military_flight"],
            "max_latency_seconds": 10.0,
        }
        result = evaluate("hormuz_crisis", "Is Hormuz at risk?", response, expected)
        assert result.score < 0.3
        assert result.mentions_score == 0.0
        assert result.sources_score == 0.25  # only news out of 4
        assert result.judgment_score == 0.0   # 2.0 is far from [7,10]
        assert result.entity_score == 0.0

    def test_latency_tracked(self):
        response = AgentResponse(
            summary="Analysis complete.",
            latency=15.0,
        )
        expected = {"max_latency_seconds": 10.0}
        result = evaluate("test", "test query", response, expected)
        assert result.details["latency_ok"] is False

    def test_composite_weights(self):
        """Verify composite formula: mentions=0.35, sources=0.30, judgment=0.20, entity=0.15."""
        result = EvalResult(scenario="test", query="test")
        result.mentions_score = 1.0
        result.sources_score = 0.0
        result.judgment_score = 0.0
        result.entity_score = 0.0
        result.compute_composite()
        assert result.score == pytest.approx(0.35)

        result.mentions_score = 0.0
        result.sources_score = 1.0
        result.compute_composite()
        assert result.score == pytest.approx(0.30)


# ── format_eval_report ────────────────────────────────────────────────


class TestFormatEvalReport:

    def test_report_contains_metric_line(self):
        results = [
            EvalResult(scenario="test", query="q1", score=0.85,
                       mentions_score=1.0, sources_score=0.8,
                       judgment_score=0.7, entity_score=0.9, latency=3.0),
            EvalResult(scenario="test", query="q2", score=0.70,
                       mentions_score=0.8, sources_score=0.6,
                       judgment_score=0.5, entity_score=1.0, latency=5.0),
        ]
        report = format_eval_report(results)
        assert "METRIC overall_eval_score=" in report
        # Overall should be average: (0.85 + 0.70) / 2 = 0.775
        assert "0.7750" in report

    def test_report_has_header(self):
        results = [EvalResult(scenario="s", query="q", score=0.5)]
        report = format_eval_report(results)
        assert "SCENARIO" in report
        assert "SCORE" in report

    def test_empty_results(self):
        assert format_eval_report([]) == "No eval results."

    def test_report_truncates_long_queries(self):
        long_query = "A" * 100
        results = [EvalResult(scenario="s", query=long_query, score=0.5)]
        report = format_eval_report(results)
        assert "..." in report
