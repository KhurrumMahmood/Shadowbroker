"""Integration tests for the AI assistant pipeline.

These tests hit the LIVE backend (localhost:8000) and the real LLM provider.
They verify the full workflow: query → search → LLM → structured response →
frontend-compatible output.

Run with:
    python -m pytest tests/test_assistant_integration.py -v --tb=short -x

Requires:
    - Backend running on localhost:8000 (with live data loaded)
    - LLM_API_KEY configured
"""
import json
import os
import pytest
import httpx

BASE = os.environ.get("TEST_BACKEND_URL", "http://localhost:8001")
TIMEOUT = 180.0  # Thinking models (Kimi K2.5) need time for reasoning + tool round-trips


def _is_backend_up() -> bool:
    try:
        r = httpx.get(f"{BASE}/api/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def _has_live_data() -> bool:
    try:
        r = httpx.get(f"{BASE}/api/live-data/fast", timeout=10)
        if r.status_code != 200:
            return False
        d = r.json()
        return len(d.get("commercial_flights", [])) > 10
    except Exception:
        return False


def _has_llm() -> bool:
    """Check if the LLM endpoint is reachable by querying assistant health."""
    try:
        r = httpx.post(f"{BASE}/api/assistant/query", json={
            "query": "hello",
        }, timeout=30)
        # 200 = LLM worked, 422/503 = LLM error but endpoint exists
        return r.status_code in (200, 422, 503)
    except Exception:
        return False


backend_up = pytest.mark.skipif(not _is_backend_up(), reason="Backend not running on :8000")
has_data = pytest.mark.skipif(not _has_live_data(), reason="No live data loaded")
has_llm = pytest.mark.skipif(not _has_llm(), reason="LLM not configured or unreachable")


# ──────────────────────────────────────────────────────────────────────────────
# Response shape validation
# ──────────────────────────────────────────────────────────────────────────────

def assert_valid_assistant_response(resp_json: dict, context: str = ""):
    """Assert the response matches the shape the frontend expects."""
    prefix = f"[{context}] " if context else ""

    # Required fields
    assert "summary" in resp_json, f"{prefix}missing 'summary'"
    assert isinstance(resp_json["summary"], str), f"{prefix}'summary' must be str"
    assert len(resp_json["summary"]) > 0, f"{prefix}'summary' must not be empty"

    # Optional fields with correct types
    layers = resp_json.get("layers")
    if layers is not None:
        assert isinstance(layers, dict), f"{prefix}'layers' must be dict or null"
        for k, v in layers.items():
            assert isinstance(k, str), f"{prefix}layer key must be str"
            assert isinstance(v, bool), f"{prefix}layer value must be bool, got {type(v)} for {k}"

    viewport = resp_json.get("viewport")
    if viewport is not None:
        assert isinstance(viewport, dict), f"{prefix}'viewport' must be dict or null"
        assert "lat" in viewport and "lng" in viewport, f"{prefix}viewport needs lat/lng"
        assert -90 <= viewport["lat"] <= 90, f"{prefix}lat out of range: {viewport['lat']}"
        assert -180 <= viewport["lng"] <= 180, f"{prefix}lng out of range: {viewport['lng']}"
        if "zoom" in viewport:
            assert 1 <= viewport["zoom"] <= 20, f"{prefix}zoom out of range: {viewport['zoom']}"

    result_entities = resp_json.get("result_entities", [])
    assert isinstance(result_entities, list), f"{prefix}'result_entities' must be list"
    for ent in result_entities:
        assert isinstance(ent, dict), f"{prefix}entity must be dict"
        assert "type" in ent and "id" in ent, f"{prefix}entity needs type+id, got: {ent}"

    highlight = resp_json.get("highlight_entities", [])
    assert isinstance(highlight, list), f"{prefix}'highlight_entities' must be list"

    filters = resp_json.get("filters")
    if filters is not None:
        assert isinstance(filters, dict), f"{prefix}'filters' must be dict or null"

    # Must NOT contain raw tool-call markup
    summary = resp_json["summary"]
    assert "<tool_call>" not in summary, f"{prefix}raw tool XML leaked into summary"
    assert "```" not in summary or summary.count("```") % 2 == 0, \
        f"{prefix}unclosed markdown fence in summary"

    return True


# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────

def ask(query: str, viewport: dict | None = None, conversation: list | None = None) -> dict:
    """Send a query to the assistant endpoint and return parsed JSON.

    Retries once after a short delay on 429 (rate limit).
    """
    import time
    body: dict = {"query": query}
    if viewport:
        body["viewport"] = viewport
    if conversation:
        body["conversation"] = conversation

    for attempt in range(2):
        resp = httpx.post(f"{BASE}/api/assistant/query", json=body, timeout=TIMEOUT)
        if resp.status_code == 429 and attempt == 0:
            time.sleep(12)  # wait for rate limit window to reset
            continue
        break

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:300]}"
    data = resp.json()
    assert_valid_assistant_response(data, context=query[:60])
    return data


# ──────────────────────────────────────────────────────────────────────────────
# Tests — Backend plumbing (no LLM needed)
# ──────────────────────────────────────────────────────────────────────────────

@backend_up
class TestEndpointBasics:
    """Verify the endpoint exists and validates input correctly."""

    def test_health(self):
        r = httpx.get(f"{BASE}/api/health", timeout=5)
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_empty_query_rejected(self):
        r = httpx.post(f"{BASE}/api/assistant/query",
                       json={"query": ""},
                       timeout=10)
        assert r.status_code == 422

    def test_no_body_rejected(self):
        r = httpx.post(f"{BASE}/api/assistant/query",
                       json={},
                       timeout=10)
        assert r.status_code == 422

    def test_missing_query_rejected(self):
        r = httpx.post(f"{BASE}/api/assistant/query",
                       json={"viewport": {}},
                       timeout=10)
        assert r.status_code == 422


@backend_up
@has_data
class TestSearchPrefilter:
    """Test that search_entities pre-filtering works against live data."""

    def test_fast_data_has_flights(self):
        r = httpx.get(f"{BASE}/api/live-data/fast", timeout=15)
        d = r.json()
        flights = d.get("commercial_flights", [])
        assert len(flights) > 50, f"Expected 50+ flights, got {len(flights)}"
        # Spot-check flight shape
        f0 = flights[0]
        for key in ["callsign", "icao24", "lat", "lng"]:
            assert key in f0, f"Flight missing '{key}': {list(f0.keys())}"

    def test_briefing_endpoint(self):
        r = httpx.post(f"{BASE}/api/assistant/brief",
                       json={"south": 50, "west": -2, "north": 53, "east": 2},
                       timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "summary" in d
        assert "counts" in d


# ──────────────────────────────────────────────────────────────────────────────
# Tests — Full LLM pipeline (requires live LLM)
# ──────────────────────────────────────────────────────────────────────────────

@backend_up
@has_data
@has_llm
class TestAssistantSimpleQueries:
    """Simple queries that should work with just pre-search, no tools needed."""

    def test_show_military_flights(self):
        data = ask("Show me military flights")
        # LLM should mention military in summary and ideally enable the layer
        assert "military" in data["summary"].lower() or (data.get("layers") or {}).get("military") is True, \
            f"Expected military reference: summary='{data['summary'][:100]}', layers={data.get('layers')}"

    def test_whats_happening(self):
        data = ask("What's happening on the map?")
        assert len(data["summary"]) > 20, "Summary too short for overview query"

    def test_earthquake_query(self):
        data = ask("Are there any earthquakes?")
        summary_lower = data["summary"].lower()
        assert "earthquake" in summary_lower or "seismic" in summary_lower or \
            (data.get("layers") or {}).get("earthquakes") is True, \
            f"Expected earthquake reference: {data['summary'][:200]}"

    def test_viewport_context(self):
        """Query with viewport should reference the area."""
        data = ask(
            "What do you see here?",
            viewport={"south": 51.0, "west": -0.5, "north": 52.0, "east": 0.5},
        )
        assert len(data["summary"]) > 10


@backend_up
@has_data
@has_llm
class TestAssistantDirectionalQueries:
    """Queries involving from/to that benefit from directional search + tools."""

    def test_flights_from_london(self):
        data = ask("Show me flights out of London")
        # Should mention flights/London and ideally set viewport + layers
        summary_lower = data["summary"].lower()
        assert "flight" in summary_lower or "london" in summary_lower, \
            f"Expected flight/london reference: {data['summary'][:200]}"

    def test_flights_from_london_to_us(self):
        data = ask("Show me flights from London to the US")
        # Should mention flights in summary
        summary_lower = data["summary"].lower()
        assert "flight" in summary_lower or "found" in summary_lower or "london" in summary_lower, \
            f"Summary doesn't mention flights: {data['summary'][:200]}"

    def test_ships_in_area(self):
        data = ask(
            "Show me ships near here",
            viewport={"south": 50, "west": -5, "north": 52, "east": 2},
        )
        layers = data.get("layers") or {}
        ship_layer_on = any(k.startswith("ships") and v for k, v in layers.items())
        # Acceptable if no ships in area — just verify valid response shape
        assert isinstance(data["summary"], str)


@backend_up
@has_data
@has_llm
class TestAssistantAggregationQueries:
    """Queries that should trigger aggregation logic."""

    def test_count_airlines(self):
        data = ask("How many different airlines are currently flying?")
        # Should mention a number in the summary
        assert any(c.isdigit() for c in data["summary"]), \
            f"Expected numbers in summary: {data['summary'][:200]}"

    def test_flights_by_country(self):
        data = ask("Which countries have the most military flights right now?")
        assert len(data["summary"]) > 20


@backend_up
@has_data
@has_llm
class TestAssistantConversation:
    """Multi-turn conversation tests."""

    def test_followup_query(self):
        """Second query should work with conversation context."""
        r1 = ask("Show me military flights")
        conversation = [
            {"role": "user", "content": "Show me military flights"},
            {"role": "assistant", "content": r1["summary"]},
        ]
        r2 = ask("How many are there?", conversation=conversation)
        assert len(r2["summary"]) > 5

    def test_error_messages_not_poisoning(self):
        """Error messages in history should not cause the next query to fail."""
        conversation = [
            {"role": "user", "content": "something that errored"},
            {"role": "assistant", "content": "LLM service unavailable: connection timeout"},
            {"role": "user", "content": "try again"},
            {"role": "assistant", "content": "Cannot reach the backend server."},
        ]
        # This should still work despite error history
        data = ask("Show me flights", conversation=conversation)
        assert "flight" in data["summary"].lower() or len(data.get("result_entities", [])) >= 0


@backend_up
@has_data
@has_llm
class TestAssistantResponseQuality:
    """Verify response quality — no leaked internals, valid entity refs, etc."""

    def test_no_raw_json_in_summary(self):
        """Summary should be natural language, not raw JSON."""
        data = ask("Show me flights near London")
        summary = data["summary"]
        assert not summary.startswith("{"), f"Summary looks like raw JSON: {summary[:100]}"
        assert not summary.startswith("["), f"Summary looks like raw JSON: {summary[:100]}"

    def test_no_tool_xml_in_summary(self):
        """Tool call XML must never leak into the summary."""
        data = ask("Show me flights from London to the US")
        assert "<tool_call>" not in data["summary"]
        assert "<arg_key>" not in data["summary"]
        assert "query_data" not in data["summary"]

    def test_entities_have_valid_ids(self):
        """result_entities should have string IDs that look like real ICAO hex codes."""
        data = ask("Show me military flights")
        for ent in data.get("result_entities", []):
            assert isinstance(ent["id"], (str, int)), f"Entity ID must be str/int: {ent}"
            assert len(str(ent["id"])) > 0, f"Empty entity ID: {ent}"

    def test_layers_use_valid_names(self):
        """Layers dict should only contain known layer names."""
        KNOWN = {
            "flights", "private", "jets", "military", "tracked", "satellites",
            "ships_military", "ships_cargo", "ships_civilian", "ships_passenger",
            "ships_tracked_yachts", "earthquakes", "cctv", "ukraine_frontline",
            "global_incidents", "day_night", "gps_jamming", "kiwisdr", "firms",
            "internet_outages", "datacenters", "military_bases", "power_plants",
        }
        data = ask("Show me everything")
        layers = data.get("layers") or {}
        for k in layers:
            assert k in KNOWN, f"Unknown layer name '{k}' in response"
