"""Tests for SSE streaming from the Orchestrator."""
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from services.agent.orchestrator import Orchestrator
from services.agent.router import QueryRouter, QueryComplexity
from services.agent.sub_agent import SubAgentResult
from services.agent.artifact_agent import ArtifactAgentResult
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


class TestStreamingArtifacts:
    """Tests for artifact generation during streaming."""

    @patch("services.agent.orchestrator.ArtifactAgent")
    @patch("services.agent.orchestrator.get_artifact_store")
    @patch("services.agent.orchestrator.SubAgent")
    def test_artifact_event_emitted_when_enabled(
        self, MockSubAgent, mock_get_store, MockArtifactAgent, hormuz_ds, router, provider,
    ):
        """When generate_artifact=True and sub-agents succeed, an artifact SSE event is emitted."""
        mock_instance = MagicMock()
        mock_instance.run.return_value = _mock_sub_result("maritime", "Found 12 ships")
        MockSubAgent.return_value = mock_instance

        # Mock artifact agent
        mock_art = MagicMock()
        mock_art.run.return_value = ArtifactAgentResult(
            html="<div>dashboard</div>", title="Risk Dashboard",
            success=True, artifact_type="dashboard",
        )
        MockArtifactAgent.return_value = mock_art

        # Mock artifact store
        mock_store = MagicMock()
        mock_store.save.return_value = "art-123"
        mock_get_store.return_value = mock_store

        plan = router.classify("What ships and flights are near Hormuz?")
        orch = Orchestrator(provider=provider, ds=hormuz_ds, generate_artifact=True)
        events = list(orch.run_streaming(plan.original_query, plan))

        types_and_data = [_parse_sse(e) for e in events]
        art_events = [(t, d) for t, d in types_and_data if t == "artifact"]
        assert len(art_events) == 1
        _, art_data = art_events[0]
        assert art_data["artifact_id"] == "art-123"
        assert art_data["title"] == "Risk Dashboard"

    @patch("services.agent.orchestrator.ArtifactAgent")
    @patch("services.agent.orchestrator.get_artifact_store")
    @patch("services.agent.orchestrator.SubAgent")
    def test_result_includes_artifact_id(
        self, MockSubAgent, mock_get_store, MockArtifactAgent, hormuz_ds, router, provider,
    ):
        """The final result event should include artifact_id when artifact was generated."""
        mock_instance = MagicMock()
        mock_instance.run.return_value = _mock_sub_result("maritime", "Ships found")
        MockSubAgent.return_value = mock_instance

        mock_art = MagicMock()
        mock_art.run.return_value = ArtifactAgentResult(
            html="<div>chart</div>", title="Chart",
            success=True, artifact_type="chart",
        )
        MockArtifactAgent.return_value = mock_art

        mock_store = MagicMock()
        mock_store.save.return_value = "art-456"
        mock_get_store.return_value = mock_store

        plan = router.classify("What ships and flights are near Hormuz?")
        orch = Orchestrator(provider=provider, ds=hormuz_ds, generate_artifact=True)
        events = list(orch.run_streaming(plan.original_query, plan))

        last_type, last_data = _parse_sse(events[-1])
        assert last_type == "result"
        assert last_data["artifact_id"] == "art-456"
        assert last_data["artifact_title"] == "Chart"

    @patch("services.agent.orchestrator.SubAgent")
    def test_no_artifact_when_disabled(self, MockSubAgent, hormuz_ds, router, provider):
        """When generate_artifact=False (default), no artifact event is emitted."""
        mock_instance = MagicMock()
        mock_instance.run.return_value = _mock_sub_result("maritime", "Ships found")
        MockSubAgent.return_value = mock_instance

        plan = router.classify("What ships and flights are near Hormuz?")
        orch = Orchestrator(provider=provider, ds=hormuz_ds)  # default: generate_artifact=False
        events = list(orch.run_streaming(plan.original_query, plan))

        types = [_parse_sse(e)[0] for e in events]
        assert "artifact" not in types

    @patch("services.agent.orchestrator.ArtifactAgent")
    @patch("services.agent.orchestrator.SubAgent")
    def test_artifact_failure_does_not_break_streaming(
        self, MockSubAgent, MockArtifactAgent, hormuz_ds, router, provider,
    ):
        """If artifact generation fails, streaming continues and result is still emitted."""
        mock_instance = MagicMock()
        mock_instance.run.return_value = _mock_sub_result("maritime", "Ships found")
        MockSubAgent.return_value = mock_instance

        mock_art = MagicMock()
        mock_art.run.return_value = ArtifactAgentResult(
            html="", title="", success=False, error="LLM timeout",
        )
        MockArtifactAgent.return_value = mock_art

        plan = router.classify("What ships and flights are near Hormuz?")
        orch = Orchestrator(provider=provider, ds=hormuz_ds, generate_artifact=True)
        events = list(orch.run_streaming(plan.original_query, plan))

        types = [_parse_sse(e)[0] for e in events]
        assert "artifact" not in types  # no artifact event on failure
        assert types[-1] == "result"  # result still emitted
        _, result_data = _parse_sse(events[-1])
        assert "artifact_id" not in result_data

    @patch("services.agent.orchestrator.ArtifactAgent")
    @patch("services.agent.orchestrator.get_artifact_store")
    @patch("services.agent.orchestrator.SubAgent")
    def test_artifact_event_order(
        self, MockSubAgent, mock_get_store, MockArtifactAgent, hormuz_ds, router, provider,
    ):
        """Event order should be: plan → sub_results → artifact → result."""
        mock_instance = MagicMock()
        mock_instance.run.return_value = _mock_sub_result("maritime", "Ships found")
        MockSubAgent.return_value = mock_instance

        mock_art = MagicMock()
        mock_art.run.return_value = ArtifactAgentResult(
            html="<div>viz</div>", title="Viz",
            success=True, artifact_type="analysis",
        )
        MockArtifactAgent.return_value = mock_art

        mock_store = MagicMock()
        mock_store.save.return_value = "art-789"
        mock_get_store.return_value = mock_store

        plan = router.classify("What ships and flights are near Hormuz?")
        orch = Orchestrator(provider=provider, ds=hormuz_ds, generate_artifact=True)
        events = list(orch.run_streaming(plan.original_query, plan))

        types = [_parse_sse(e)[0] for e in events]
        assert types[0] == "plan"
        assert types[-1] == "result"
        assert types[-2] == "artifact"
        # Everything in between is sub_results
        for t in types[1:-2]:
            assert t == "sub_result"
