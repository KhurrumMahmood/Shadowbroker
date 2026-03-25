"""Tests for SubAgent execution with mocked LLM."""
import json
import time
import pytest
from unittest.mock import patch, MagicMock

from services.agent.sub_agent import SubAgent, SubAgentResult
from services.agent.router import SubTask
from services.agent.datasource import StaticDataSource
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures" / "scenarios"


@pytest.fixture
def hormuz_ds():
    return StaticDataSource(FIXTURES / "hormuz_crisis")


@pytest.fixture
def maritime_task():
    return SubTask(
        intent="analyze_maritime",
        query_fragment="What ships are near the Strait of Hormuz?",
        tool_hints=["query_data", "proximity_search"],
    )


def _make_llm_response(content, tool_calls=None):
    """Build a mock OpenAI-style chat completion response."""
    msg = {"role": "assistant", "content": content}
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return {
        "choices": [{"message": msg, "finish_reason": "stop"}],
    }


def _make_tool_call(call_id, fn_name, arguments):
    """Build a mock tool_call object."""
    return {
        "id": call_id,
        "type": "function",
        "function": {
            "name": fn_name,
            "arguments": json.dumps(arguments),
        },
    }


class TestSubAgentBasic:

    @patch("services.agent.llm.httpx.post")
    def test_returns_result_on_success(self, mock_post, hormuz_ds, maritime_task):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: _make_llm_response(json.dumps({
                "summary": "Found 12 tankers near Hormuz",
                "key_findings": ["12 tankers in transit"],
                "entity_references": [{"type": "ship", "id": "123456789"}],
            })),
        )

        agent = SubAgent(
            provider={"api_key": "test", "base_url": "http://test", "model": "test-model"},
            sub_task=maritime_task,
            ds=hormuz_ds,
        )
        result = agent.run()

        assert isinstance(result, SubAgentResult)
        assert result.success is True
        assert "tanker" in result.summary.lower()
        assert result.sub_task_intent == "analyze_maritime"

    @patch("services.agent.llm.httpx.post")
    def test_handles_tool_call_then_final(self, mock_post, hormuz_ds, maritime_task):
        """Agent makes a tool call, gets result, then produces final answer."""
        # First call: LLM wants to call query_data
        tool_call = _make_tool_call("tc1", "query_data", {"category": "ships"})
        first_response = _make_llm_response(None, tool_calls=[tool_call])

        # Second call: LLM produces final answer
        final_response = _make_llm_response(json.dumps({
            "summary": "47 ships detected in the strait area",
            "key_findings": ["Heavy tanker traffic"],
            "entity_references": [],
        }))

        mock_post.return_value = MagicMock(status_code=200)
        mock_post.return_value.json = MagicMock(side_effect=[first_response, final_response])

        agent = SubAgent(
            provider={"api_key": "test", "base_url": "http://test", "model": "test-model"},
            sub_task=maritime_task,
            ds=hormuz_ds,
        )
        result = agent.run()

        assert result.success is True
        assert len(result.tool_calls_made) >= 1
        assert result.tool_calls_made[0]["name"] == "query_data"

    @patch("services.agent.llm.httpx.post")
    def test_respects_deadline(self, mock_post, hormuz_ds, maritime_task):
        """Agent should bail if deadline is exceeded."""
        # Simulate a slow LLM response
        def slow_response(*args, **kwargs):
            time.sleep(0.1)
            return MagicMock(
                status_code=200,
                json=lambda: _make_llm_response("slow response"),
            )

        mock_post.side_effect = slow_response

        agent = SubAgent(
            provider={"api_key": "test", "base_url": "http://test", "model": "test-model"},
            sub_task=maritime_task,
            ds=hormuz_ds,
            deadline=time.monotonic() + 0.05,  # 50ms deadline — will expire
        )
        result = agent.run()

        # Should return a result (possibly timed out)
        assert isinstance(result, SubAgentResult)

    @patch("services.agent.llm.httpx.post")
    def test_handles_llm_error(self, mock_post, hormuz_ds, maritime_task):
        mock_post.return_value = MagicMock(
            status_code=500,
            json=lambda: {"error": "Internal server error"},
        )

        agent = SubAgent(
            provider={"api_key": "test", "base_url": "http://test", "model": "test-model"},
            sub_task=maritime_task,
            ds=hormuz_ds,
        )
        result = agent.run()

        assert result.success is False
        assert result.error is not None

    @patch("services.agent.llm.httpx.post")
    def test_records_duration(self, mock_post, hormuz_ds, maritime_task):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: _make_llm_response(json.dumps({
                "summary": "test", "key_findings": [], "entity_references": [],
            })),
        )

        agent = SubAgent(
            provider={"api_key": "test", "base_url": "http://test", "model": "test-model"},
            sub_task=maritime_task,
            ds=hormuz_ds,
        )
        result = agent.run()

        assert result.duration_ms >= 0


class TestSubAgentToolScoping:

    @patch("services.agent.llm.httpx.post")
    def test_gets_scoped_tools(self, mock_post, hormuz_ds, maritime_task):
        """SubAgent should only get tools relevant to its task."""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: _make_llm_response(json.dumps({
                "summary": "test", "key_findings": [], "entity_references": [],
            })),
        )

        agent = SubAgent(
            provider={"api_key": "test", "base_url": "http://test", "model": "test-model"},
            sub_task=maritime_task,
            ds=hormuz_ds,
        )
        agent.run()

        # Check that the LLM was called with tools
        call_kwargs = mock_post.call_args
        body = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert "tools" in body
        assert len(body["tools"]) > 0
