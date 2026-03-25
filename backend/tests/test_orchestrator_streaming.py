"""Tests for SSE streaming from the Orchestrator."""
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from services.agent.orchestrator import Orchestrator
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


def _mock_sub_result(intent, summary, success=True):
    return SubAgentResult(
        sub_task_intent=intent,
        summary=summary,
        key_findings=[f"Finding from {intent}"],
        entity_references=[],
        tool_calls_made=[],
        success=success,
        duration_ms=100,
    )


def _parse_sse(event_str):
    """Parse an SSE event string into (event_type, data_dict)."""
    lines = event_str.strip().split("\n")
    event_type = None
    data = None
    for line in lines:
        if line.startswith("event: "):
            event_type = line[7:]
        elif line.startswith("data: "):
            data = json.loads(line[6:])
    return event_type, data


class TestStreamingEvents:

    @patch("services.agent.orchestrator.SubAgent")
    def test_emits_plan_event(self, MockSubAgent, hormuz_ds, router, provider):
        """Compound query should emit a 'plan' SSE event."""
        mock_instance = MagicMock()
        mock_instance.run.return_value = _mock_sub_result("test", "test")
        MockSubAgent.return_value = mock_instance

        plan = router.classify("What ships and flights are near Hormuz?")
        orch = Orchestrator(provider=provider, ds=hormuz_ds)
        events = list(orch.run_streaming(plan.original_query, plan))

        plan_events = [(t, d) for t, d in ((_parse_sse(e)) for e in events) if t == "plan"]
        assert len(plan_events) == 1
        _, plan_data = plan_events[0]
        assert plan_data["complexity"] == "compound"
        assert len(plan_data["sub_tasks"]) >= 2

    @patch("services.agent.orchestrator.SubAgent")
    def test_emits_sub_result_events(self, MockSubAgent, hormuz_ds, router, provider):
        """Each sub-agent completion should emit a 'sub_result' SSE event."""
        mock_instance = MagicMock()
        mock_instance.run.return_value = _mock_sub_result("analyze_maritime", "Found 12 ships")
        MockSubAgent.return_value = mock_instance

        plan = router.classify("What ships and flights are near Hormuz?")
        orch = Orchestrator(provider=provider, ds=hormuz_ds)
        events = list(orch.run_streaming(plan.original_query, plan))

        sub_events = [(t, d) for t, d in (_parse_sse(e) for e in events) if t == "sub_result"]
        assert len(sub_events) >= 1
        _, first = sub_events[0]
        assert "sub_task" in first
        assert "success" in first

    @patch("services.agent.orchestrator.SubAgent")
    def test_final_event_is_result(self, MockSubAgent, hormuz_ds, router, provider):
        """Last event should always be 'result'."""
        mock_instance = MagicMock()
        mock_instance.run.return_value = _mock_sub_result("test", "test")
        MockSubAgent.return_value = mock_instance

        plan = router.classify("What's unusual right now?")
        orch = Orchestrator(provider=provider, ds=hormuz_ds)
        events = list(orch.run_streaming(plan.original_query, plan))

        last_type, last_data = _parse_sse(events[-1])
        assert last_type == "result"
        assert "summary" in last_data

    @patch("services.agent.orchestrator.SubAgent")
    def test_event_order(self, MockSubAgent, hormuz_ds, router, provider):
        """Events should be: plan, then sub_results, then result."""
        mock_instance = MagicMock()
        mock_instance.run.return_value = _mock_sub_result("test", "test")
        MockSubAgent.return_value = mock_instance

        plan = router.classify("What ships and flights are near Hormuz?")
        orch = Orchestrator(provider=provider, ds=hormuz_ds)
        events = list(orch.run_streaming(plan.original_query, plan))

        types = [_parse_sse(e)[0] for e in events]
        # plan comes first
        assert types[0] == "plan"
        # result comes last
        assert types[-1] == "result"
        # sub_results in the middle
        for t in types[1:-1]:
            assert t == "sub_result"
