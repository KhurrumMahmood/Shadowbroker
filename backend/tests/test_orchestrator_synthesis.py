"""Tests for LLM-based synthesis in the Orchestrator."""
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from services.agent.orchestrator import Orchestrator, OrchestratorResult
from services.agent.router import QueryRouter
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


def _mock_sub_result(intent, summary):
    return SubAgentResult(
        sub_task_intent=intent,
        summary=summary,
        key_findings=[f"Finding from {intent}"],
        entity_references=[{"type": "ship", "id": "123"}],
        tool_calls_made=[],
        success=True,
        duration_ms=100,
    )


class TestLLMSynthesis:

    @patch("services.agent.orchestrator.SubAgent")
    @patch("services.agent.orchestrator.call_llm_simple")
    def test_synthesis_uses_llm(self, mock_llm, MockSubAgent, hormuz_ds, router, provider):
        """When LLM synthesis is enabled, orchestrator makes a synthesis call."""
        # Sub-agents return results
        mock_instance = MagicMock()
        mock_instance.run.return_value = _mock_sub_result("analyze_maritime", "12 tankers")
        MockSubAgent.return_value = mock_instance

        # Synthesis LLM returns structured JSON
        mock_llm.return_value = {
            "content": json.dumps({
                "summary": "Elevated maritime activity near Hormuz with 12 tankers in transit.",
                "risk_level": 6,
                "key_findings": ["12 tankers in transit", "GPS jamming detected"],
            }),
            "tool_calls_made": [],
            "error": None,
        }

        plan = router.classify("What ships and flights are near Hormuz?")
        orch = Orchestrator(provider=provider, ds=hormuz_ds, use_llm_synthesis=True)
        result = orch.run(plan.original_query, plan)

        assert "elevated" in result.summary.lower() or "tanker" in result.summary.lower()
        mock_llm.assert_called()

    @patch("services.agent.orchestrator.SubAgent")
    @patch("services.agent.orchestrator.call_llm_simple")
    def test_synthesis_fallback_on_error(self, mock_llm, MockSubAgent, hormuz_ds, router, provider):
        """If LLM synthesis fails, fall back to deterministic concatenation."""
        mock_instance = MagicMock()
        mock_instance.run.return_value = _mock_sub_result("analyze_maritime", "12 tankers")
        MockSubAgent.return_value = mock_instance

        # Synthesis LLM fails
        mock_llm.return_value = {
            "content": "",
            "tool_calls_made": [],
            "error": "LLM returned HTTP 500",
        }

        plan = router.classify("What ships and flights are near Hormuz?")
        orch = Orchestrator(provider=provider, ds=hormuz_ds, use_llm_synthesis=True)
        result = orch.run(plan.original_query, plan)

        # Should still produce a result via concatenation
        assert isinstance(result, OrchestratorResult)
        assert result.summary  # not empty

    @patch("services.agent.orchestrator.SubAgent")
    def test_no_synthesis_without_flag(self, MockSubAgent, hormuz_ds, router, provider):
        """Default: no LLM synthesis call, just concatenation."""
        mock_instance = MagicMock()
        mock_instance.run.return_value = _mock_sub_result("test", "test summary")
        MockSubAgent.return_value = mock_instance

        plan = router.classify("What's unusual right now?")
        orch = Orchestrator(provider=provider, ds=hormuz_ds)  # no use_llm_synthesis
        result = orch.run(plan.original_query, plan)

        assert result.summary  # concatenated

    @patch("services.agent.orchestrator.SubAgent")
    @patch("services.agent.orchestrator.call_llm_simple")
    def test_synthesis_prompt_includes_sub_results(self, mock_llm, MockSubAgent, hormuz_ds, router, provider):
        """Synthesis prompt should contain sub-agent summaries and findings."""
        mock_instance = MagicMock()
        mock_instance.run.return_value = _mock_sub_result("analyze_maritime", "12 tankers detected near Hormuz")
        MockSubAgent.return_value = mock_instance

        mock_llm.return_value = {
            "content": json.dumps({"summary": "Synthesized", "key_findings": []}),
            "tool_calls_made": [],
            "error": None,
        }

        plan = router.classify("What ships and flights are near Hormuz?")
        orch = Orchestrator(provider=provider, ds=hormuz_ds, use_llm_synthesis=True)
        orch.run(plan.original_query, plan)

        # Check that synthesis call includes sub-agent findings
        call_args = mock_llm.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages") or call_args[0][1]
        all_content = " ".join(m.get("content", "") for m in messages)
        assert "tanker" in all_content.lower()

    @patch("services.agent.orchestrator.SubAgent")
    @patch("services.agent.orchestrator.call_llm_simple")
    def test_synthesis_invalid_json_falls_back(self, mock_llm, MockSubAgent, hormuz_ds, router, provider):
        """If LLM returns non-JSON, use raw content as summary."""
        mock_instance = MagicMock()
        mock_instance.run.return_value = _mock_sub_result("test", "test")
        MockSubAgent.return_value = mock_instance

        mock_llm.return_value = {
            "content": "This is a plain text summary, not JSON.",
            "tool_calls_made": [],
            "error": None,
        }

        plan = router.classify("What's unusual right now?")
        orch = Orchestrator(provider=provider, ds=hormuz_ds, use_llm_synthesis=True)
        result = orch.run(plan.original_query, plan)

        assert "plain text summary" in result.summary
