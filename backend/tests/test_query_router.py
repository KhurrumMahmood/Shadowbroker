"""Tests for the deterministic query router (simple vs compound classification)."""
import time
import pytest

from services.agent.router import QueryRouter, QueryComplexity


@pytest.fixture
def router():
    return QueryRouter()


class TestSimpleQueries:
    """Single-domain, single-intent queries should be classified as SIMPLE."""

    def test_single_category_query(self, router):
        plan = router.classify("Show military flights near Iran")
        assert plan.complexity == QueryComplexity.SIMPLE

    def test_count_query(self, router):
        plan = router.classify("How many C-17s are flying eastbound?")
        assert plan.complexity == QueryComplexity.SIMPLE

    def test_ship_query(self, router):
        plan = router.classify("What tankers are near the Strait of Hormuz?")
        assert plan.complexity == QueryComplexity.SIMPLE

    def test_earthquake_query(self, router):
        plan = router.classify("Any earthquakes above magnitude 5?")
        assert plan.complexity == QueryComplexity.SIMPLE

    def test_news_query(self, router):
        plan = router.classify("Latest news about Iran")
        assert plan.complexity == QueryComplexity.SIMPLE

    def test_simple_preserves_original(self, router):
        q = "Show military flights near Iran"
        plan = router.classify(q)
        assert plan.original_query == q


class TestCompoundQueries:
    """Multi-domain or analytical queries should be classified as COMPOUND."""

    def test_two_domains(self, router):
        plan = router.classify("What ships and military flights are near Hormuz?")
        assert plan.complexity == QueryComplexity.COMPOUND

    def test_cross_correlation_keyword(self, router):
        plan = router.classify("Are there cascading events in the region?")
        assert plan.complexity == QueryComplexity.COMPOUND

    def test_discovery_query(self, router):
        plan = router.classify("What's unusual right now?")
        assert plan.complexity == QueryComplexity.COMPOUND

    def test_developing_situations(self, router):
        plan = router.classify("Any developing situations I should know about?")
        assert plan.complexity == QueryComplexity.COMPOUND

    def test_temporal_plus_spatial(self, router):
        plan = router.classify("What changed near the Strait of Hormuz in the last 4 hours?")
        assert plan.complexity == QueryComplexity.COMPOUND

    def test_compare_regions(self, router):
        plan = router.classify("Compare military posture in the Gulf to Taiwan")
        assert plan.complexity == QueryComplexity.COMPOUND

    def test_market_impact(self, router):
        plan = router.classify("What geopolitical events could move oil prices?")
        assert plan.complexity == QueryComplexity.COMPOUND

    def test_compound_events(self, router):
        plan = router.classify("Are there compound events or cascade situations developing?")
        assert plan.complexity == QueryComplexity.COMPOUND

    def test_ew_detection(self, router):
        plan = router.classify("Is there electronic warfare activity with GPS jamming and internet outages?")
        assert plan.complexity == QueryComplexity.COMPOUND

    def test_risk_assessment(self, router):
        plan = router.classify("Risk assessment for shipping through the Red Sea")
        assert plan.complexity == QueryComplexity.COMPOUND

    def test_compound_has_subtasks(self, router):
        plan = router.classify("What ships and military flights are near Hormuz?")
        assert len(plan.sub_tasks) >= 2

    def test_compound_has_domains(self, router):
        plan = router.classify("What ships and military flights are near Hormuz?")
        assert "maritime" in plan.domains_detected
        assert "aviation" in plan.domains_detected


class TestDomainDetection:
    """Verify domain taxonomy matching."""

    def test_maritime_domain(self, router):
        plan = router.classify("Show me tankers near the strait")
        assert "maritime" in plan.domains_detected

    def test_aviation_domain(self, router):
        plan = router.classify("How many C-17 aircraft are airborne?")
        assert "aviation" in plan.domains_detected

    def test_seismic_domain(self, router):
        plan = router.classify("Recent earthquake activity near Turkey")
        assert "seismic" in plan.domains_detected

    def test_infrastructure_domain(self, router):
        plan = router.classify("Power plants near the conflict zone")
        assert "infrastructure" in plan.domains_detected

    def test_conflict_domain(self, router):
        plan = router.classify("Military base activity near the border")
        assert "conflict" in plan.domains_detected

    def test_intelligence_domain(self, router):
        plan = router.classify("GPS jamming zones in the Gulf")
        assert "intelligence" in plan.domains_detected


class TestPerformance:
    """Router must be fast — no LLM calls, pure keyword matching."""

    def test_thousand_calls_under_100ms(self, router):
        queries = [
            "Show military flights near Iran",
            "What ships and flights are near Hormuz?",
            "What's unusual right now?",
            "Any earthquakes?",
            "Compare Gulf to Taiwan military posture",
        ] * 200  # 1000 queries

        start = time.monotonic()
        for q in queries:
            router.classify(q)
        elapsed_ms = (time.monotonic() - start) * 1000

        assert elapsed_ms < 100, f"1000 classifications took {elapsed_ms:.0f}ms (limit: 100ms)"
