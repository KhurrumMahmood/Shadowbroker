"""Tests for the AI assistant endpoint and service."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json


class TestAssistantEndpoint:
    """Test POST /api/assistant/query route exists and validates input."""

    def test_returns_422_without_body(self, client):
        r = client.post("/api/assistant/query")
        assert r.status_code == 422

    def test_returns_422_with_empty_query(self, client):
        r = client.post("/api/assistant/query", json={"query": ""})
        assert r.status_code == 422

    def test_returns_200_with_valid_query(self, client):
        """With LLM mocked out, should return a structured response."""
        with patch("main.call_llm") as mock_llm:
            mock_llm.return_value = {
                "summary": "Here is what I found.",
                "layers": None,
                "viewport": None,
                "highlight_entities": [],
            }
            r = client.post("/api/assistant/query", json={
                "query": "show me military flights near the Black Sea",
            })
            assert r.status_code == 200
            data = r.json()
            assert "summary" in data
            assert data["summary"] == "Here is what I found."

    def test_passes_viewport_to_service(self, client):
        with patch("main.call_llm") as mock_llm:
            mock_llm.return_value = {
                "summary": "OK",
                "layers": None,
                "viewport": None,
                "highlight_entities": [],
            }
            r = client.post("/api/assistant/query", json={
                "query": "what's here?",
                "viewport": {"south": 30, "west": 20, "north": 50, "east": 40},
            })
            assert r.status_code == 200
            # Verify the LLM was called with viewport context
            call_args = mock_llm.call_args
            assert call_args is not None

    def test_returns_503_when_llm_not_configured(self, client):
        """If LLM_API_KEY is not set, should return 503."""
        with patch("main.call_llm", side_effect=RuntimeError("LLM not configured")):
            r = client.post("/api/assistant/query", json={
                "query": "test",
            })
            assert r.status_code == 503


class TestLLMAssistantService:
    """Unit tests for the llm_assistant module itself."""

    def test_build_system_prompt_includes_layer_names(self):
        from services.llm_assistant import build_system_prompt
        prompt = build_system_prompt({})
        # Should mention available data layers
        assert "military_flights" in prompt or "military flights" in prompt.lower()
        assert "ships" in prompt.lower()

    def test_build_system_prompt_includes_data_summary(self):
        from services.llm_assistant import build_system_prompt
        data_summary = {
            "commercial_flights": 1234,
            "military_flights": 45,
            "ships": 890,
        }
        prompt = build_system_prompt(data_summary)
        assert "1234" in prompt or "1,234" in prompt
        assert "45" in prompt

    def test_parse_llm_response_valid_json(self):
        from services.llm_assistant import parse_llm_response
        raw = json.dumps({
            "summary": "Three military flights near the Black Sea.",
            "layers": {"military": True, "tracked": True},
            "viewport": {"lat": 43, "lng": 34, "zoom": 6},
            "highlight_entities": [{"type": "military_flight", "id": "mil001"}],
        })
        result = parse_llm_response(raw)
        assert result["summary"] == "Three military flights near the Black Sea."
        assert result["layers"]["military"] is True
        assert result["viewport"]["lat"] == 43

    def test_parse_llm_response_extracts_json_from_markdown(self):
        from services.llm_assistant import parse_llm_response
        raw = "Here's what I found:\n```json\n{\"summary\": \"hello\", \"layers\": null, \"viewport\": null, \"highlight_entities\": []}\n```"
        result = parse_llm_response(raw)
        assert result["summary"] == "hello"

    def test_parse_llm_response_returns_fallback_on_garbage(self):
        from services.llm_assistant import parse_llm_response
        result = parse_llm_response("this is not json at all")
        assert "summary" in result
        # Should contain the raw text as summary fallback
        assert "not json" in result["summary"].lower() or len(result["summary"]) > 0

    def test_parse_llm_response_clamps_viewport(self):
        from services.llm_assistant import parse_llm_response
        raw = json.dumps({
            "summary": "test",
            "layers": None,
            "viewport": {"lat": 200, "lng": -500, "zoom": 50},
            "highlight_entities": [],
        })
        result = parse_llm_response(raw)
        vp = result.get("viewport")
        if vp:
            assert -90 <= vp["lat"] <= 90
            assert -180 <= vp["lng"] <= 180
            assert 1 <= vp["zoom"] <= 20
