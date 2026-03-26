"""Tests for artifact version lineage — Step 4 of artifact evolution.

Tests that:
- AssistantQuery accepts active_artifact field
- Orchestrator threads enhance_artifact_name to ArtifactAgent
- Orchestrator calls create_version() when enhancing (not save_artifact)
- SSE artifact event includes version and registry_name
- Default behavior unchanged when no active_artifact
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from services.agent.orchestrator import Orchestrator
from services.agent.router import QueryRouter
from services.agent.sub_agent import SubAgentResult
from services.agent.artifact_agent import ArtifactAgentResult

FIXTURES = Path(__file__).parent / "fixtures" / "scenarios"


@pytest.fixture
def provider():
    return {"api_key": "test", "base_url": "http://test", "model": "test-model"}


@pytest.fixture
def hormuz_ds():
    from services.agent.datasource import StaticDataSource
    return StaticDataSource(FIXTURES / "hormuz_crisis")


@pytest.fixture
def router():
    return QueryRouter()


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
    lines = event_str.strip().split("\n")
    event_type = None
    data = None
    for line in lines:
        if line.startswith("event: "):
            event_type = line[7:]
        elif line.startswith("data: "):
            data = json.loads(line[6:])
    return event_type, data


class TestAssistantQueryModel:
    """Test that AssistantQuery accepts active_artifact."""

    def test_accepts_active_artifact(self):
        """POST body with active_artifact should parse without error."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from main import AssistantQuery

        body = AssistantQuery(
            query="add filters to that map",
            active_artifact={"name": "ship-map", "version": 1},
        )
        assert body.active_artifact == {"name": "ship-map", "version": 1}

    def test_active_artifact_defaults_to_none(self):
        """active_artifact should be optional and default to None."""
        from main import AssistantQuery

        body = AssistantQuery(query="show ships near Hormuz")
        assert body.active_artifact is None


class TestOrchestratorEnhancement:
    """Test orchestrator version lineage wiring."""

    @pytest.fixture(autouse=True)
    def mock_registry(self):
        mock_reg = MagicMock()
        mock_reg.search.return_value = []
        mock_reg.get_registry_summary.return_value = "No saved artifacts."
        mock_reg.save_artifact.return_value = None
        mock_reg.create_version.return_value = 2
        mock_reg.get_latest_version.return_value = (
            "<div>existing viz</div>",
            {"title": "Ship Map", "current_version": 1},
        )
        with patch("services.agent.orchestrator.get_artifact_registry", return_value=mock_reg):
            with patch("services.agent.orchestrator.extract_tags_from_query", return_value=["maritime"]):
                yield mock_reg

    def test_orchestrator_accepts_enhance_artifact_name(self, provider, hormuz_ds):
        """Orchestrator.__init__ should accept enhance_artifact_name."""
        orch = Orchestrator(
            provider=provider,
            ds=hormuz_ds,
            generate_artifact=True,
            enhance_artifact_name="ship-map",
        )
        assert orch.enhance_artifact_name == "ship-map"

    def test_orchestrator_defaults_enhance_to_none(self, provider, hormuz_ds):
        """Without enhance_artifact_name, it defaults to None."""
        orch = Orchestrator(provider=provider, ds=hormuz_ds)
        assert orch.enhance_artifact_name is None

    @patch("services.agent.orchestrator.ArtifactAgent")
    @patch("services.agent.orchestrator.get_artifact_store")
    @patch("services.agent.orchestrator.SubAgent")
    def test_passes_enhance_to_artifact_agent(
        self, MockSubAgent, mock_get_store, MockArtifactAgent,
        hormuz_ds, router, provider, mock_registry,
    ):
        """When enhance_artifact_name is set, ArtifactAgent gets enhance_artifact kwarg."""
        mock_instance = MagicMock()
        mock_instance.run.return_value = _mock_sub_result("maritime", "Found 12 ships")
        MockSubAgent.return_value = mock_instance

        mock_art = MagicMock()
        mock_art.run.return_value = ArtifactAgentResult(
            html="<div>enhanced</div>", title="Enhanced Ship Map",
            success=True, artifact_type="dashboard",
        )
        MockArtifactAgent.return_value = mock_art

        mock_store = MagicMock()
        mock_store.save.return_value = "art-enhanced"
        mock_get_store.return_value = mock_store

        plan = router.classify("What ships and flights are near Hormuz?")
        orch = Orchestrator(
            provider=provider, ds=hormuz_ds,
            generate_artifact=True, enhance_artifact_name="ship-map",
        )
        list(orch.run_streaming(plan.original_query, plan))

        # Verify ArtifactAgent was constructed with enhance_artifact
        MockArtifactAgent.assert_called_once()
        call_kwargs = MockArtifactAgent.call_args
        assert call_kwargs.kwargs.get("enhance_artifact") == "ship-map" or \
               (len(call_kwargs.args) > 0 and "enhance_artifact" in str(call_kwargs))

    @patch("services.agent.orchestrator.ArtifactAgent")
    @patch("services.agent.orchestrator.get_artifact_store")
    @patch("services.agent.orchestrator.SubAgent")
    def test_calls_create_version_when_enhancing(
        self, MockSubAgent, mock_get_store, MockArtifactAgent,
        hormuz_ds, router, provider, mock_registry,
    ):
        """When enhancing, registry.create_version() should be called instead of save_artifact()."""
        mock_instance = MagicMock()
        mock_instance.run.return_value = _mock_sub_result("maritime", "Ships found")
        MockSubAgent.return_value = mock_instance

        mock_art = MagicMock()
        mock_art.run.return_value = ArtifactAgentResult(
            html="<div>v2</div>", title="Ship Map v2",
            success=True, artifact_type="dashboard",
        )
        MockArtifactAgent.return_value = mock_art

        mock_store = MagicMock()
        mock_store.save.return_value = "art-v2"
        mock_get_store.return_value = mock_store

        plan = router.classify("What ships and flights are near Hormuz?")
        orch = Orchestrator(
            provider=provider, ds=hormuz_ds,
            generate_artifact=True, enhance_artifact_name="ship-map",
        )
        list(orch.run_streaming(plan.original_query, plan))

        # create_version called, save_artifact NOT called
        mock_registry.create_version.assert_called_once()
        assert mock_registry.create_version.call_args.kwargs.get("name") == "ship-map" or \
               mock_registry.create_version.call_args[0][0] == "ship-map"
        mock_registry.save_artifact.assert_not_called()

    @patch("services.agent.orchestrator.ArtifactAgent")
    @patch("services.agent.orchestrator.get_artifact_store")
    @patch("services.agent.orchestrator.SubAgent")
    def test_artifact_sse_includes_version_and_registry_name(
        self, MockSubAgent, mock_get_store, MockArtifactAgent,
        hormuz_ds, router, provider, mock_registry,
    ):
        """SSE artifact event should include version and registry_name when enhancing."""
        mock_instance = MagicMock()
        mock_instance.run.return_value = _mock_sub_result("maritime", "Ships found")
        MockSubAgent.return_value = mock_instance

        mock_art = MagicMock()
        mock_art.run.return_value = ArtifactAgentResult(
            html="<div>v2</div>", title="Ship Map",
            success=True, artifact_type="dashboard",
        )
        MockArtifactAgent.return_value = mock_art

        mock_store = MagicMock()
        mock_store.save.return_value = "art-v2"
        mock_get_store.return_value = mock_store

        # create_version returns version number 2
        mock_registry.create_version.return_value = 2

        plan = router.classify("What ships and flights are near Hormuz?")
        orch = Orchestrator(
            provider=provider, ds=hormuz_ds,
            generate_artifact=True, enhance_artifact_name="ship-map",
        )
        events = list(orch.run_streaming(plan.original_query, plan))

        art_events = [(t, d) for t, d in (_parse_sse(e) for e in events) if t == "artifact"]
        assert len(art_events) == 1
        _, art_data = art_events[0]
        assert art_data["registry_name"] == "ship-map"
        assert art_data["version"] == 2

    @patch("services.agent.orchestrator.ArtifactAgent")
    @patch("services.agent.orchestrator.get_artifact_store")
    @patch("services.agent.orchestrator.SubAgent")
    def test_no_enhance_without_active_artifact(
        self, MockSubAgent, mock_get_store, MockArtifactAgent,
        hormuz_ds, router, provider, mock_registry,
    ):
        """Without enhance_artifact_name, save_artifact is called (not create_version)."""
        mock_instance = MagicMock()
        mock_instance.run.return_value = _mock_sub_result("maritime", "Ships found")
        MockSubAgent.return_value = mock_instance

        mock_art = MagicMock()
        mock_art.run.return_value = ArtifactAgentResult(
            html="<div>new</div>", title="New Viz",
            success=True, artifact_type="chart",
        )
        MockArtifactAgent.return_value = mock_art

        mock_store = MagicMock()
        mock_store.save.return_value = "art-new"
        mock_get_store.return_value = mock_store

        plan = router.classify("What ships and flights are near Hormuz?")
        orch = Orchestrator(
            provider=provider, ds=hormuz_ds,
            generate_artifact=True,  # no enhance_artifact_name
        )
        list(orch.run_streaming(plan.original_query, plan))

        # save_artifact called, NOT create_version
        mock_registry.save_artifact.assert_called_once()
        mock_registry.create_version.assert_not_called()
