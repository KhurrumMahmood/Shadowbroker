"""Tests for registry-aware artifact generation in the orchestrator.

Tests the decision logic: reuse existing artifact, enhance, or create new.
"""
import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from services.agent.artifact_registry import ArtifactRegistry
from services.agent.artifact_agent import ArtifactAgent, ArtifactAgentResult


@pytest.fixture
def registry_dir():
    with tempfile.TemporaryDirectory() as tmp:
        reg_path = Path(tmp) / "registry.json"
        reg_path.write_text(json.dumps({"artifacts": []}))
        yield Path(tmp)


@pytest.fixture
def registry(registry_dir):
    return ArtifactRegistry(registry_dir)


@pytest.fixture
def populated_registry(registry):
    """Registry with two artifacts already saved."""
    registry.save_artifact(
        name="ship-chokepoint-map",
        title="Maritime Chokepoint Map",
        description="Ship positions near a chokepoint with flag coloring",
        tags=["maritime", "ships", "chokepoint", "map", "hormuz"],
        data_signature="ships + chokepoint_name",
        html="<div id='ship-map'>Ship map v1</div>",
        note="Initial version",
    )
    registry.save_artifact(
        name="military-convergence-overlay",
        title="Military Convergence Overlay",
        description="Multi-country military flight proximity map",
        tags=["military", "flights", "convergence", "multi-country"],
        data_signature="military_flights + countries",
        html="<div id='mil-conv'>Military convergence v1</div>",
        note="Initial version",
    )
    return registry


class TestRegistrySearch:
    def test_finds_matching_artifact(self, populated_registry):
        results = populated_registry.search(["maritime", "ships", "chokepoint"])
        assert len(results) >= 1
        assert results[0]["name"] == "ship-chokepoint-map"

    def test_no_match_for_unrelated_query(self, populated_registry):
        results = populated_registry.search(["nuclear", "submarine"])
        assert len(results) == 0


class TestRegistrySummaryForPrompt:
    def test_empty_registry_summary(self, registry):
        summary = registry.get_registry_summary()
        assert "No saved artifacts" in summary

    def test_populated_registry_summary(self, populated_registry):
        summary = populated_registry.get_registry_summary()
        assert "ship-chokepoint-map" in summary
        assert "military-convergence-overlay" in summary
        assert "Saved artifacts:" in summary

    def test_summary_includes_tags(self, populated_registry):
        summary = populated_registry.get_registry_summary()
        assert "maritime" in summary
        assert "military" in summary


class TestTagExtraction:
    """Test extract_tags_from_query utility."""

    def test_extracts_domain_tags(self):
        from services.agent.artifact_registry import extract_tags_from_query
        tags = extract_tags_from_query("What ships are near the Strait of Hormuz?")
        assert "ships" in tags or "maritime" in tags
        assert "hormuz" in tags

    def test_extracts_military_tags(self):
        from services.agent.artifact_registry import extract_tags_from_query
        tags = extract_tags_from_query("Show military flights converging near Taiwan")
        assert "military" in tags
        assert "flights" in tags
        assert "taiwan" in tags

    def test_extracts_viz_type_tags(self):
        from services.agent.artifact_registry import extract_tags_from_query
        tags = extract_tags_from_query("Compare earthquake activity with fire hotspots on a timeline")
        assert "timeline" in tags or "compare" in tags

    def test_handles_empty_query(self):
        from services.agent.artifact_registry import extract_tags_from_query
        tags = extract_tags_from_query("")
        assert isinstance(tags, list)


class TestArtifactAgentRegistryAwareness:
    """Test that ArtifactAgent includes registry info in its prompt."""

    @patch("services.agent.artifact_agent.call_llm_simple")
    def test_prompt_includes_registry_summary(self, mock_llm, populated_registry):
        mock_llm.return_value = {
            "content": "```html\n<div>new viz</div>\n```",
            "error": None,
        }
        agent = ArtifactAgent(
            provider={"model": "test"},
            query="Show ships near Hormuz",
            sub_results_summary="Found 12 ships",
            registry=populated_registry,
        )
        result = agent.run()
        # Check that the system prompt included registry info
        call_args = mock_llm.call_args
        messages = call_args[1]["messages"] if "messages" in call_args[1] else call_args[0][1]
        system_msg = messages[0]["content"]
        assert "ship-chokepoint-map" in system_msg

    @patch("services.agent.artifact_agent.call_llm_simple")
    def test_agent_returns_reuse_decision(self, mock_llm, populated_registry):
        """When LLM decides to reuse, the result should indicate reuse."""
        mock_llm.return_value = {
            "content": '{"action": "reuse", "artifact_name": "ship-chokepoint-map"}',
            "error": None,
        }
        agent = ArtifactAgent(
            provider={"model": "test"},
            query="Show ships near Hormuz",
            sub_results_summary="Found 12 ships",
            registry=populated_registry,
        )
        result = agent.run()
        assert result.reuse_artifact == "ship-chokepoint-map"

    @patch("services.agent.artifact_agent.call_llm_simple")
    def test_agent_generates_when_no_match(self, mock_llm, registry):
        """Empty registry → agent generates new artifact."""
        mock_llm.return_value = {
            "content": "```html\n<div>brand new</div>\n```",
            "error": None,
        }
        agent = ArtifactAgent(
            provider={"model": "test"},
            query="Show GDELT events on a timeline",
            sub_results_summary="Found 45 events",
            registry=registry,
        )
        result = agent.run()
        assert result.success
        assert result.html == "<div>brand new</div>"
        assert result.reuse_artifact is None

    @patch("services.agent.artifact_agent.call_llm_simple")
    def test_enhance_includes_existing_html(self, mock_llm, populated_registry):
        """When enhancing, the existing HTML should be in the prompt."""
        mock_llm.return_value = {
            "content": "```html\n<div>enhanced v2</div>\n```",
            "error": None,
        }
        agent = ArtifactAgent(
            provider={"model": "test"},
            query="Add speed indicators to the ship map",
            sub_results_summary="Enhancement request",
            registry=populated_registry,
            enhance_artifact="ship-chokepoint-map",
        )
        result = agent.run()
        call_args = mock_llm.call_args
        messages = call_args[1]["messages"] if "messages" in call_args[1] else call_args[0][1]
        user_msg = messages[1]["content"]
        assert "Ship map v1" in user_msg  # existing HTML included

    @patch("services.agent.artifact_agent.call_llm_simple")
    def test_backwards_compat_no_registry(self, mock_llm):
        """Agent still works without registry (backwards compatible)."""
        mock_llm.return_value = {
            "content": "```html\n<div>no registry</div>\n```",
            "error": None,
        }
        agent = ArtifactAgent(
            provider={"model": "test"},
            query="Show data",
            sub_results_summary="Data found",
        )
        result = agent.run()
        assert result.success
        assert result.html == "<div>no registry</div>"
