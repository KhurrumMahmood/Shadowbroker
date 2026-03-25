"""Tests for the ArtifactAgent — generates HTML visualizations from sub-agent data."""
import json
import pytest
from unittest.mock import patch, MagicMock

from services.agent.artifact_agent import ArtifactAgent, ArtifactAgentResult
from services.agent.artifacts import Artifact


class TestArtifactAgentResult:
    def test_defaults(self):
        r = ArtifactAgentResult(html="<p>hi</p>", title="Test")
        assert r.success is True
        assert r.error is None
        assert r.artifact_type == ""

    def test_failure(self):
        r = ArtifactAgentResult(html="", title="", success=False, error="LLM died")
        assert not r.success


class TestArtifactAgent:
    def _mock_llm_response(self, html_content: str):
        """Helper: create a mock LLM response that returns HTML in a code block."""
        return {
            "content": f"```html\n{html_content}\n```",
            "tool_calls_made": [],
            "error": None,
        }

    @patch("services.agent.artifact_agent.call_llm_simple")
    def test_generates_artifact_html(self, mock_llm):
        html = '<div class="sb-card"><h1>Risk Dashboard</h1></div>'
        mock_llm.return_value = self._mock_llm_response(html)

        agent = ArtifactAgent(
            provider={"api_key": "test", "base_url": "http://test", "model": "test"},
            query="Show me Hormuz risk",
            sub_results_summary="Found 12 tankers, 2 military flights",
        )
        result = agent.run()

        assert result.success
        assert "<h1>Risk Dashboard</h1>" in result.html
        assert result.title  # should have a generated title
        mock_llm.assert_called_once()

    @patch("services.agent.artifact_agent.call_llm_simple")
    def test_includes_design_tokens_instruction(self, mock_llm):
        mock_llm.return_value = self._mock_llm_response("<p>test</p>")

        agent = ArtifactAgent(
            provider={"api_key": "test", "base_url": "http://test", "model": "test"},
            query="Show ships",
            sub_results_summary="10 ships found",
        )
        agent.run()

        # Check that the system prompt mentions ShadowBroker tokens
        call_args = mock_llm.call_args
        messages = call_args[1]["messages"] if "messages" in call_args[1] else call_args[0][1]
        system_msg = messages[0]["content"]
        assert "sb-" in system_msg or "shadowbroker" in system_msg.lower()

    @patch("services.agent.artifact_agent.call_llm_simple")
    def test_handles_llm_error(self, mock_llm):
        mock_llm.return_value = {
            "content": "",
            "tool_calls_made": [],
            "error": "LLM timeout",
        }

        agent = ArtifactAgent(
            provider={"api_key": "test", "base_url": "http://test", "model": "test"},
            query="test",
            sub_results_summary="data",
        )
        result = agent.run()

        assert not result.success
        assert "LLM timeout" in result.error

    @patch("services.agent.artifact_agent.call_llm_simple")
    def test_handles_no_html_in_response(self, mock_llm):
        mock_llm.return_value = {
            "content": "Sorry, I can't generate HTML right now.",
            "tool_calls_made": [],
            "error": None,
        }

        agent = ArtifactAgent(
            provider={"api_key": "test", "base_url": "http://test", "model": "test"},
            query="test",
            sub_results_summary="data",
        )
        result = agent.run()

        # Should still succeed but use the raw content wrapped in basic HTML
        assert result.success
        assert result.html  # should have something

    @patch("services.agent.artifact_agent.call_llm_simple")
    def test_extracts_html_from_code_block(self, mock_llm):
        full_response = """Here's your dashboard:

```html
<!DOCTYPE html>
<html>
<head><title>Risk</title></head>
<body><div class="sb-card">Content</div></body>
</html>
```

Hope this helps!"""
        mock_llm.return_value = {
            "content": full_response,
            "tool_calls_made": [],
            "error": None,
        }

        agent = ArtifactAgent(
            provider={"api_key": "test", "base_url": "http://test", "model": "test"},
            query="test",
            sub_results_summary="data",
        )
        result = agent.run()

        assert result.success
        assert "<!DOCTYPE html>" in result.html
        assert "sb-card" in result.html
        # Should NOT include the surrounding text
        assert "Hope this helps" not in result.html

    @patch("services.agent.artifact_agent.call_llm_simple")
    def test_passes_data_context(self, mock_llm):
        mock_llm.return_value = self._mock_llm_response("<p>chart</p>")

        data_context = {
            "ships": [{"name": "Tanker1", "lat": 26.5, "lng": 56.3}],
            "risk_level": 7,
        }
        agent = ArtifactAgent(
            provider={"api_key": "test", "base_url": "http://test", "model": "test"},
            query="Show risk chart",
            sub_results_summary="Risk level 7",
            data_context=data_context,
        )
        agent.run()

        call_args = mock_llm.call_args
        messages = call_args[1]["messages"] if "messages" in call_args[1] else call_args[0][1]
        user_msg = messages[1]["content"]
        assert "Tanker1" in user_msg or "risk_level" in user_msg
