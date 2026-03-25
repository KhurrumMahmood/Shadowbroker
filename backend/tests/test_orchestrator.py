"""Tests for the Orchestrator — parallel sub-agent dispatch + synthesis."""
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from services.agent.orchestrator import Orchestrator, OrchestratorResult
from services.agent.router import QueryRouter, QueryComplexity
from services.agent.sub_agent import SubAgentResult
from services.agent.datasource import StaticDataSource

FIXTURES = Path(__file__).parent / "fixtures" / "scenarios"


@pytest.fixture
def hormuz_ds():
    return StaticDataSource(FIXTURES / "hormuz_crisis")


@pytest.fixture
def router():
    return QueryRouter()


@pytest.fixture
def provider():
    return {"api_key": "test", "base_url": "http://test", "model": "test-model"}


def _mock_sub_agent_result(intent, summary, success=True):
    return SubAgentResult(
        sub_task_intent=intent,
        summary=summary,
        key_findings=[f"Finding from {intent}"],
        entity_references=[],
        tool_calls_made=[],
        success=success,
        duration_ms=100,
    )


class TestOrchestratorDispatch:

    @patch("services.agent.orchestrator.SubAgent")
    def test_dispatches_sub_agents_for_compound(self, MockSubAgent, hormuz_ds, router, provider):
        """Compound query should spawn multiple sub-agents."""
        mock_instance = MagicMock()
        mock_instance.run.return_value = _mock_sub_agent_result(
            "analyze_maritime", "Found ships"
        )
        MockSubAgent.return_value = mock_instance

        plan = router.classify("What ships and military flights are near Hormuz?")
        assert plan.complexity == QueryComplexity.COMPOUND

        orch = Orchestrator(provider=provider, ds=hormuz_ds)
        result = orch.run(plan.original_query, plan)

        assert isinstance(result, OrchestratorResult)
        assert len(result.sub_results) >= 2  # at least 2 domain sub-agents
        assert result.plan == plan

    @patch("services.agent.orchestrator.SubAgent")
    def test_handles_partial_failure(self, MockSubAgent, hormuz_ds, router, provider):
        """If one sub-agent fails, orchestrator still returns results from others."""
        call_count = [0]
        def make_result():
            r = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                r.run.return_value = _mock_sub_agent_result(
                    "analyze_maritime", "Found ships", success=True
                )
            else:
                r.run.return_value = _mock_sub_agent_result(
                    "analyze_aviation", "", success=False
                )
            return r

        MockSubAgent.side_effect = lambda **kw: make_result()

        plan = router.classify("What ships and flights are near Hormuz?")
        orch = Orchestrator(provider=provider, ds=hormuz_ds)
        result = orch.run(plan.original_query, plan)

        # Should still produce a result
        assert isinstance(result, OrchestratorResult)
        successful = [r for r in result.sub_results if r.success]
        assert len(successful) >= 1

    @patch("services.agent.orchestrator.SubAgent")
    def test_concatenates_summaries(self, MockSubAgent, hormuz_ds, router, provider):
        """Without LLM synthesis, orchestrator concatenates sub-agent summaries."""
        results_iter = iter([
            _mock_sub_agent_result("analyze_maritime", "12 tankers detected"),
            _mock_sub_agent_result("analyze_aviation", "3 military flights"),
            _mock_sub_agent_result("synthesis", "Elevated activity near Hormuz"),
        ])

        mock_instance = MagicMock()
        mock_instance.run.side_effect = lambda: next(results_iter)
        MockSubAgent.return_value = mock_instance

        plan = router.classify("What ships and military flights are near Hormuz?")
        orch = Orchestrator(provider=provider, ds=hormuz_ds)
        result = orch.run(plan.original_query, plan)

        assert "tanker" in result.summary.lower() or "flight" in result.summary.lower()

    @patch("services.agent.orchestrator.SubAgent")
    def test_records_duration(self, MockSubAgent, hormuz_ds, router, provider):
        mock_instance = MagicMock()
        mock_instance.run.return_value = _mock_sub_agent_result("test", "test")
        MockSubAgent.return_value = mock_instance

        plan = router.classify("What's unusual right now?")
        orch = Orchestrator(provider=provider, ds=hormuz_ds)
        result = orch.run(plan.original_query, plan)

        assert result.duration_ms >= 0


class TestOrchestratorDoesNotRunForSimple:

    def test_simple_query_not_orchestrated(self, router):
        plan = router.classify("Show tankers near Hormuz")
        assert plan.complexity == QueryComplexity.SIMPLE
        # Simple queries should NOT go through the orchestrator
