"""Tests for llm_assistant search and parsing utilities."""
import json
import pytest
from unittest.mock import patch, MagicMock
from services.llm_assistant import _FIELDS_BLOCK
from services.llm_assistant import (
    _parse_directional_hints,
    _parse_inline_tool_calls,
    _fuzzy_contains,
    search_entities,
    parse_llm_response,
    _exec_query_data,
    _exec_aggregate_data,
    _exec_web_search,
    execute_tool_call,
    _apply_filters,
    _build_tools,
    _QUERYABLE_FIELDS,
    _SEARCH_CONFIG,
    _cache_key,
    _query_cache,
    _sse,
    _build_messages,
)


class TestParseDirectionalHints:
    def test_from_to(self):
        h = _parse_directional_hints("flights from London to New York")
        assert "london" in h["origin_terms"]
        assert "york" in h["dest_terms"] or "new" in h["dest_terms"]

    def test_out_of(self):
        h = _parse_directional_hints("flights out of Heathrow to Paris")
        assert "heathrow" in h["origin_terms"]
        assert "paris" in h["dest_terms"]

    def test_departing_heading(self):
        h = _parse_directional_hints("departing Tokyo heading to Sydney")
        assert "tokyo" in h["origin_terms"]
        assert "sydney" in h["dest_terms"]

    def test_bound_for(self):
        h = _parse_directional_hints("ships bound for Rotterdam")
        assert "rotterdam" in h["dest_terms"]

    def test_leaving(self):
        h = _parse_directional_hints("leaving Berlin to Munich")
        assert "berlin" in h["origin_terms"]
        assert "munich" in h["dest_terms"]

    def test_no_direction(self):
        h = _parse_directional_hints("show me military flights")
        assert h["origin_terms"] == []
        assert h["dest_terms"] == []

    def test_only_destination(self):
        h = _parse_directional_hints("flights going to JFK")
        assert h["origin_terms"] == []
        assert "jfk" in h["dest_terms"]

    def test_only_origin(self):
        h = _parse_directional_hints("flights from LAX")
        assert "lax" in h["origin_terms"]


class TestSearchEntitiesDirectional:
    """Verify directional hints boost the right entities."""

    FLIGHTS = [
        {"callsign": "BA100", "icao24": "a1", "origin_name": "LHR: London Heathrow",
         "dest_name": "JFK: John F Kennedy", "country": "UK", "model": "B777",
         "lat": 51.47, "lng": -0.46, "alt": 10000, "registration": "G-ABCD",
         "airline_code": "BAW"},
        {"callsign": "AA200", "icao24": "a2", "origin_name": "JFK: John F Kennedy",
         "dest_name": "LHR: London Heathrow", "country": "US", "model": "B787",
         "lat": 40.6, "lng": -73.7, "alt": 11000, "registration": "N-1234",
         "airline_code": "AAL"},
        {"callsign": "LH300", "icao24": "a3", "origin_name": "FRA: Frankfurt",
         "dest_name": "CDG: Paris Charles de Gaulle", "country": "DE", "model": "A320",
         "lat": 49.0, "lng": 8.5, "alt": 9000, "registration": "D-ABCD",
         "airline_code": "DLH"},
    ]

    def test_from_london_boosts_origin(self):
        data = {"commercial_flights": self.FLIGHTS}
        results = search_entities("flights from London to JFK", data)
        ids = [e["icao24"] for e in results.get("commercial_flights", [])]
        # BA100 (origin=London, dest=JFK) should rank above AA200 (dest=London)
        assert "a1" in ids
        if "a2" in ids:
            assert ids.index("a1") < ids.index("a2")

    def test_to_london_boosts_destination(self):
        data = {"commercial_flights": self.FLIGHTS}
        results = search_entities("flights to London", data)
        ids = [e["icao24"] for e in results.get("commercial_flights", [])]
        # AA200 (dest=London) should rank above BA100 (origin=London)
        assert "a2" in ids
        if "a1" in ids:
            assert ids.index("a2") < ids.index("a1")

    def test_no_direction_matches_both(self):
        data = {"commercial_flights": self.FLIGHTS}
        results = search_entities("London flights", data)
        ids = [e["icao24"] for e in results.get("commercial_flights", [])]
        assert "a1" in ids
        assert "a2" in ids

    def test_unrelated_excluded(self):
        data = {"commercial_flights": self.FLIGHTS}
        results = search_entities("flights from London to JFK", data)
        ids = [e["icao24"] for e in results.get("commercial_flights", [])]
        # Frankfurt→Paris flight shouldn't match
        assert "a3" not in ids


class TestParseLlmResponse:
    def test_valid_json(self):
        raw = '{"summary": "Found 3 flights.", "layers": {"flights": true}}'
        r = parse_llm_response(raw)
        assert r["summary"] == "Found 3 flights."
        assert r["layers"] == {"flights": True}

    def test_markdown_fence(self):
        raw = '```json\n{"summary": "test"}\n```'
        r = parse_llm_response(raw)
        assert r["summary"] == "test"

    def test_truncated_json_salvages_summary(self):
        raw = '{"summary": "Found 88 flights near London.", "layers": {"flights": true}, "result_entities": [{"type": "flight", "id": "abc'
        r = parse_llm_response(raw)
        assert "88 flights" in r["summary"]
        assert r["result_entities"] == []

    def test_garbage_returns_raw(self):
        raw = "I cannot help with that request."
        r = parse_llm_response(raw)
        assert "cannot help" in r["summary"]

    def test_clamps_viewport(self):
        raw = '{"summary": "ok", "viewport": {"lat": 200, "lng": -300, "zoom": 50}}'
        r = parse_llm_response(raw)
        assert r["viewport"]["lat"] == 90
        assert r["viewport"]["lng"] == -180
        assert r["viewport"]["zoom"] == 20

    def test_filters_unknown_layers(self):
        raw = '{"summary": "ok", "layers": {"flights": true, "bogus_layer": true}}'
        r = parse_llm_response(raw)
        assert "flights" in r["layers"]
        assert "bogus_layer" not in r["layers"]

    def test_result_entities_max_50(self):
        entities = [{"type": "flight", "id": str(i)} for i in range(60)]
        raw = json.dumps({"summary": "ok", "result_entities": entities})
        r = parse_llm_response(raw)
        assert len(r["result_entities"]) == 50


# --- Tool execution tests ---

SAMPLE_FLIGHTS = [
    {"callsign": "BA100", "icao24": "a1", "origin_name": "LHR: London Heathrow",
     "dest_name": "JFK: John F Kennedy", "country": "UK", "model": "B777",
     "lat": 51.47, "lng": -0.46, "alt": 10000, "registration": "G-ABCD",
     "airline_code": "BAW", "aircraft_category": "plane"},
    {"callsign": "AA200", "icao24": "a2", "origin_name": "JFK: John F Kennedy",
     "dest_name": "LHR: London Heathrow", "country": "US", "model": "B787",
     "lat": 40.6, "lng": -73.7, "alt": 11000, "registration": "N-1234",
     "airline_code": "AAL", "aircraft_category": "plane"},
    {"callsign": "EZY300", "icao24": "a3", "origin_name": "LGW: London Gatwick",
     "dest_name": "CDG: Paris Charles de Gaulle", "country": "UK", "model": "A320",
     "lat": 50.5, "lng": 0.5, "alt": 9000, "registration": "G-EZAB",
     "airline_code": "EZY", "aircraft_category": "plane"},
    {"callsign": "UA400", "icao24": "a4", "origin_name": "LHR: London Heathrow",
     "dest_name": "ORD: Chicago O'Hare", "country": "US", "model": "B777",
     "lat": 52.0, "lng": -10.0, "alt": 12000, "registration": "N-5678",
     "airline_code": "UAL", "aircraft_category": "plane"},
]

SAMPLE_DATA = {"commercial_flights": SAMPLE_FLIGHTS}


class TestApplyFilters:
    def test_single_filter(self):
        result = _apply_filters(SAMPLE_FLIGHTS, {"origin_name": "london"}, None)
        assert len(result) == 3  # BA100, EZY300 (Gatwick), UA400

    def test_multiple_filters_and(self):
        result = _apply_filters(SAMPLE_FLIGHTS, {"origin_name": "london", "dest_name": "kennedy"}, None)
        assert len(result) == 1
        assert result[0]["callsign"] == "BA100"

    def test_no_match(self):
        result = _apply_filters(SAMPLE_FLIGHTS, {"origin_name": "tokyo"}, None)
        assert len(result) == 0

    def test_no_filters(self):
        result = _apply_filters(SAMPLE_FLIGHTS, None, None)
        assert len(result) == 4


class TestFuzzyContains:
    def test_exact_substring(self):
        assert _fuzzy_contains("AirSial", "airsial")

    def test_space_stripped(self):
        """'Air Sial' should match 'AirSial' via space removal."""
        assert _fuzzy_contains("AirSial", "air sial")

    def test_space_stripped_reverse(self):
        """'AirSial' query should match 'Air Sial Ltd' field."""
        assert _fuzzy_contains("Air Sial Ltd", "airsial")

    def test_token_containment(self):
        """'Turkish Air' should match 'Turkish Airlines' (both tokens present)."""
        assert _fuzzy_contains("Turkish Airlines", "Turkish Air")

    def test_token_containment_order(self):
        """Token order shouldn't matter."""
        assert _fuzzy_contains("Delta Air Lines", "lines delta")

    def test_single_token_substring(self):
        assert _fuzzy_contains("Pakistan International Airlines", "pakistan")

    def test_no_match(self):
        assert not _fuzzy_contains("Delta Air Lines", "qatar")

    def test_partial_token_no_false_positive(self):
        """Single token 'air' shouldn't match via token-containment on its own."""
        # But it DOES match via direct substring since "air" is in "AirSial"
        assert _fuzzy_contains("AirSial", "air")

    def test_token_no_cross_word_match(self):
        """'Air India' must NOT match 'Thai AirAsia India' — 'air' is inside 'airasia', not a whole word."""
        assert not _fuzzy_contains("Thai AirAsia India", "Air India")

    def test_apply_filters_uses_fuzzy(self):
        """_apply_filters should use fuzzy matching."""
        items = [
            {"airline_name": "AirSial", "callsign": "PF101"},
            {"airline_name": "Delta Air Lines", "callsign": "DAL200"},
        ]
        result = _apply_filters(items, {"airline_name": "air sial"}, None)
        assert len(result) == 1
        assert result[0]["callsign"] == "PF101"


class TestExecQueryData:
    def test_basic_query(self):
        raw = _exec_query_data({"category": "commercial_flights"}, SAMPLE_DATA)
        result = json.loads(raw)
        assert result["total"] == 4
        assert result["showing"] == 4

    def test_filtered_query(self):
        raw = _exec_query_data({
            "category": "commercial_flights",
            "filters": {"origin_name": "london heathrow"},
        }, SAMPLE_DATA)
        result = json.loads(raw)
        assert result["total"] == 2  # BA100, UA400
        assert all("london heathrow" in r["origin_name"].lower() for r in result["results"])

    def test_dest_filter(self):
        raw = _exec_query_data({
            "category": "commercial_flights",
            "filters": {"origin_name": "london", "dest_name": "kennedy"},
        }, SAMPLE_DATA)
        result = json.loads(raw)
        assert result["total"] == 1
        assert result["results"][0]["callsign"] == "BA100"

    def test_limit(self):
        raw = _exec_query_data({
            "category": "commercial_flights",
            "limit": 2,
        }, SAMPLE_DATA)
        result = json.loads(raw)
        assert result["showing"] == 2
        assert result["total"] == 4

    def test_unknown_category(self):
        raw = _exec_query_data({"category": "bogus"}, SAMPLE_DATA)
        result = json.loads(raw)
        assert "error" in result

    def test_empty_data(self):
        raw = _exec_query_data({"category": "commercial_flights"}, {})
        result = json.loads(raw)
        assert result["total"] == 0


class TestExecAggregateData:
    def test_group_by_airline(self):
        raw = _exec_aggregate_data({
            "category": "commercial_flights",
            "group_by": "airline_code",
        }, SAMPLE_DATA)
        result = json.loads(raw)
        assert result["total_items"] == 4
        assert result["top_groups"]["BAW"] == 1
        assert result["top_groups"]["AAL"] == 1

    def test_group_by_country(self):
        raw = _exec_aggregate_data({
            "category": "commercial_flights",
            "group_by": "country",
        }, SAMPLE_DATA)
        result = json.loads(raw)
        assert result["top_groups"]["UK"] == 2
        assert result["top_groups"]["US"] == 2

    def test_filtered_aggregate(self):
        raw = _exec_aggregate_data({
            "category": "commercial_flights",
            "group_by": "airline_code",
            "filters": {"origin_name": "london"},
        }, SAMPLE_DATA)
        result = json.loads(raw)
        assert result["total_items"] == 3  # BA100, EZY300, UA400
        assert "AAL" not in result["top_groups"]  # AA200 origin is JFK

    def test_top_n(self):
        raw = _exec_aggregate_data({
            "category": "commercial_flights",
            "group_by": "airline_code",
            "top_n": 2,
        }, SAMPLE_DATA)
        result = json.loads(raw)
        assert len(result["top_groups"]) == 2


class TestExecuteToolCall:
    def test_routes_query(self):
        raw = execute_tool_call("query_data", {"category": "commercial_flights"}, SAMPLE_DATA)
        assert json.loads(raw)["total"] == 4

    def test_routes_aggregate(self):
        raw = execute_tool_call("aggregate_data", {
            "category": "commercial_flights", "group_by": "country",
        }, SAMPLE_DATA)
        assert "top_groups" in json.loads(raw)

    def test_unknown_tool(self):
        raw = execute_tool_call("bogus_tool", {}, SAMPLE_DATA)
        assert "error" in json.loads(raw)


class TestParseInlineToolCalls:
    """Parse XML-style tool calls that some LLMs emit as text."""

    def test_single_query(self):
        text = '<tool_call>query_data<arg_key>category</arg_key><arg_value>commercial_flights</arg_value><arg_key>limit</arg_key><arg_value>10</arg_value></tool_call>'
        calls = _parse_inline_tool_calls(text)
        assert len(calls) == 1
        assert calls[0][0] == "query_data"
        assert calls[0][1]["category"] == "commercial_flights"
        assert calls[0][1]["limit"] == 10  # parsed as int

    def test_aggregate_call(self):
        text = 'None<tool_call>aggregate_data<arg_key>category</arg_key><arg_value>military_flights</arg_value><arg_key>group_by</arg_key><arg_value>country</arg_value></tool_call>'
        calls = _parse_inline_tool_calls(text)
        assert len(calls) == 1
        assert calls[0][0] == "aggregate_data"
        assert calls[0][1]["group_by"] == "country"

    def test_filters_as_json(self):
        text = '<tool_call>query_data<arg_key>category</arg_key><arg_value>commercial_flights</arg_value><arg_key>filters</arg_key><arg_value>{"origin_name": "london"}</arg_value></tool_call>'
        calls = _parse_inline_tool_calls(text)
        assert len(calls) == 1
        assert calls[0][1]["filters"] == {"origin_name": "london"}

    def test_no_tool_calls(self):
        text = '{"summary": "Here are some flights.", "layers": {"flights": true}}'
        calls = _parse_inline_tool_calls(text)
        assert len(calls) == 0

    def test_unknown_function_ignored(self):
        text = '<tool_call>evil_function<arg_key>x</arg_key><arg_value>y</arg_value></tool_call>'
        calls = _parse_inline_tool_calls(text)
        assert len(calls) == 0

    def test_multiple_calls(self):
        text = (
            '<tool_call>query_data<arg_key>category</arg_key><arg_value>commercial_flights</arg_value></tool_call>'
            'some text'
            '<tool_call>aggregate_data<arg_key>category</arg_key><arg_value>ships</arg_value><arg_key>group_by</arg_key><arg_value>type</arg_value></tool_call>'
        )
        calls = _parse_inline_tool_calls(text)
        assert len(calls) == 2
        assert calls[0][0] == "query_data"
        assert calls[1][0] == "aggregate_data"


# --- Reasoning steps preservation ---

class TestReasoningStepsPreservation:
    """parse_llm_response uses json.loads + setdefault — extra keys like reasoning_steps survive."""

    def test_reasoning_steps_preserved_in_parsed_response(self):
        raw = json.dumps({
            "summary": "Analysis complete.",
            "reasoning_steps": [
                {"type": "thinking", "content": "Analyzing query..."},
                {"type": "tool_call", "content": "query_data(category='flights')"},
                {"type": "tool_result", "content": "Found 5 flights"},
            ],
        })
        result = parse_llm_response(raw)
        assert "reasoning_steps" in result
        assert len(result["reasoning_steps"]) == 3
        assert result["reasoning_steps"][0]["type"] == "thinking"

    def test_no_reasoning_steps_when_absent(self):
        raw = json.dumps({"summary": "Simple response."})
        result = parse_llm_response(raw)
        assert "reasoning_steps" not in result


# --- Country enrichment field coverage ---

class TestCountryFieldsInConfig:
    def test_queryable_fields_has_country(self):
        fields = _QUERYABLE_FIELDS.get("commercial_flights", [])
        assert "origin_country" in fields
        assert "dest_country" in fields

    def test_search_config_has_country(self):
        config = _SEARCH_CONFIG.get("commercial_flights", {})
        search_fields = config.get("fields", [])
        assert "origin_country" in search_fields
        assert "dest_country" in search_fields

    def test_query_filters_by_country(self):
        flights = [
            {"callsign": "BA1", "icao24": "x1", "origin_name": "LHR",
             "dest_name": "JFK", "origin_country": "United Kingdom",
             "dest_country": "United States", "country": "UK", "model": "B777",
             "lat": 51.0, "lng": -0.5, "alt": 35000, "airline_code": "BAW",
             "aircraft_category": "plane"},
            {"callsign": "AF2", "icao24": "x2", "origin_name": "CDG",
             "dest_name": "NRT", "origin_country": "France",
             "dest_country": "Japan", "country": "FR", "model": "A380",
             "lat": 48.8, "lng": 2.3, "alt": 38000, "airline_code": "AFR",
             "aircraft_category": "plane"},
        ]
        data = {"commercial_flights": flights}
        raw = _exec_query_data({
            "category": "commercial_flights",
            "filters": {"dest_country": "United States"},
        }, data)
        result = json.loads(raw)
        assert result["total"] == 1
        assert result["results"][0]["callsign"] == "BA1"


# --- Field validation in tool execution ---

class TestFieldsBlock:
    def test_fields_block_contains_real_field_names(self):
        """Ensure the prompt field block has actual field names, not literal {k}."""
        assert "{k}" not in _FIELDS_BLOCK
        assert "commercial_flights" in _FIELDS_BLOCK
        assert "callsign" in _FIELDS_BLOCK
        assert "origin_country" in _FIELDS_BLOCK


class TestFieldValidation:
    def test_query_data_drops_unknown_filter_keys(self):
        raw = _exec_query_data({
            "category": "commercial_flights",
            "filters": {"departure_city": "London", "origin_name": "london"},
        }, SAMPLE_DATA)
        result = json.loads(raw)
        # "departure_city" is not a valid field — should be dropped, not filter everything out
        # "origin_name" is valid — should still match
        assert result["total"] > 0

    def test_query_data_all_unknown_filters_returns_all(self):
        raw = _exec_query_data({
            "category": "commercial_flights",
            "filters": {"bogus_field": "test"},
        }, SAMPLE_DATA)
        result = json.loads(raw)
        # All filters dropped → should return all items
        assert result["total"] == 4

    def test_aggregate_data_rejects_unknown_group_by(self):
        raw = _exec_aggregate_data({
            "category": "commercial_flights",
            "group_by": "nonexistent_field",
        }, SAMPLE_DATA)
        result = json.loads(raw)
        assert "error" in result

    def test_aggregate_data_drops_unknown_filter_keys(self):
        raw = _exec_aggregate_data({
            "category": "commercial_flights",
            "group_by": "country",
            "filters": {"bogus": "test", "origin_name": "london"},
        }, SAMPLE_DATA)
        result = json.loads(raw)
        # bogus filter dropped, origin_name=london applied → 3 items (BA100, EZY300, UA400)
        assert result["total_items"] == 3


class TestCacheKey:
    def test_normalizes_place_names(self):
        k1 = _cache_key("Show flights from London to Paris")
        k2 = _cache_key("Show flights from Tokyo to Sydney")
        assert k1 == k2

    def test_different_structure_different_key(self):
        k1 = _cache_key("Show flights from London to Paris")
        k2 = _cache_key("How many ships are near Rotterdam")
        assert k1 != k2

    def test_different_intent_different_key(self):
        """Show vs Count must not collide — only place names are normalized."""
        k1 = _cache_key("Show flights from London to Paris")
        k2 = _cache_key("Count flights from London to Paris")
        assert k1 != k2

    def test_collapses_whitespace(self):
        k1 = _cache_key("flights  from   London")
        k2 = _cache_key("flights from London")
        assert k1 == k2

    def test_lowercase(self):
        k = _cache_key("flights from London")
        assert k == k.lower()

    def test_preserves_sentence_initial_verb(self):
        """Sentence-initial verbs like Show/Count should NOT be replaced."""
        k = _cache_key("Show flights from London")
        assert "show" in k
        assert "_x_" not in k.split("from")[0]  # _x_ only after 'from'


class TestSseHelper:
    def test_formats_correctly(self):
        result = _sse("status", {"step": "thinking", "detail": "test"})
        assert result.startswith("event: status\n")
        assert "data: " in result
        assert result.endswith("\n\n")
        data = json.loads(result.split("data: ")[1].strip())
        assert data["step"] == "thinking"

    def test_result_event(self):
        result = _sse("result", {"summary": "hello"})
        assert "event: result" in result
        data = json.loads(result.split("data: ")[1].strip())
        assert data["summary"] == "hello"


class TestQueryCacheInjection:
    def test_cache_hit_injects_into_system_prompt(self):
        # Seed the cache
        _query_cache[_cache_key("flights from London to Paris")] = [
            {"type": "tool_call", "content": "query_data({\"category\": \"commercial_flights\"})"}
        ]
        try:
            msgs = _build_messages(
                "flights from Tokyo to Sydney",
                {"commercial_flights": 100},
                None, None, None,
            )
            system = msgs[0]["content"]
            assert "similar query previously succeeded" in system
            assert "query_data" in system
        finally:
            _query_cache.clear()

    def test_no_cache_hit_no_injection(self):
        _query_cache.clear()
        msgs = _build_messages(
            "a completely unique query 12345",
            {"commercial_flights": 100},
            None, None, None,
        )
        system = msgs[0]["content"]
        assert "similar query previously succeeded" not in system


# ---------------------------------------------------------------------------
# Retry + Fallback Tests
# ---------------------------------------------------------------------------

from services.llm_assistant import (
    _call_provider, refresh_providers, _PROVIDERS, _MAX_RETRIES,
    _OVERALL_BUDGET_S, _parse_retry_after,
    LLMConnectionError, ContentFilterError,
)
from unittest.mock import patch, MagicMock


class TestProviderRetry:
    """Tests for per-provider retry with backoff."""

    def _make_provider(self):
        return {
            "name": "test",
            "api_key": "key",
            "base_url": "https://test.example.com/v1",
            "model": "test-model",
        }

    def _make_ok_response(self):
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "choices": [{"message": {"content": '{"summary": "test"}'}, "finish_reason": "stop"}],
            "usage": {},
        }
        return resp

    def _make_error_response(self, status_code, body="Server Error"):
        resp = MagicMock()
        resp.status_code = status_code
        resp.text = body
        resp.headers = {}
        error = httpx.HTTPStatusError("error", request=MagicMock(), response=resp)
        return error

    @patch("services.llm_assistant.httpx.post")
    @patch("services.llm_assistant._time.sleep")
    def test_retries_on_500_then_succeeds(self, mock_sleep, mock_post):
        """500 on first attempt, success on retry."""
        err = self._make_error_response(500)
        ok = self._make_ok_response()
        mock_post.side_effect = [type(err)(str(err), request=MagicMock(), response=err.response), ok]
        # Make the first call raise, second succeed
        def side_effect(*args, **kwargs):
            r = mock_post.call_count
            if r == 1:
                raise httpx.HTTPStatusError("500", request=MagicMock(), response=err.response)
            return ok
        mock_post.side_effect = side_effect

        messages = [{"role": "user", "content": "test"}]
        result = _call_provider(self._make_provider(), messages, None)
        assert result["summary"] == "test"
        assert mock_post.call_count == 2
        mock_sleep.assert_called_once()

    @patch("services.llm_assistant.httpx.post")
    @patch("services.llm_assistant._time.sleep")
    def test_retries_on_429_respects_retry_after(self, mock_sleep, mock_post):
        """429 with Retry-After header should use that delay."""
        err_resp = MagicMock()
        err_resp.status_code = 429
        err_resp.text = "Rate limited"
        err_resp.headers = {"Retry-After": "2"}
        ok = self._make_ok_response()

        call_count = [0]
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise httpx.HTTPStatusError("429", request=MagicMock(), response=err_resp)
            return ok
        mock_post.side_effect = side_effect

        messages = [{"role": "user", "content": "test"}]
        result = _call_provider(self._make_provider(), messages, None)
        assert result["summary"] == "test"
        mock_sleep.assert_called_once_with(2.0)

    @patch("services.llm_assistant.httpx.post")
    @patch("services.llm_assistant._time.sleep")
    def test_raises_after_exhausting_retries(self, mock_sleep, mock_post):
        """After MAX_RETRIES+1 failures, should raise."""
        err_resp = MagicMock()
        err_resp.status_code = 500
        err_resp.text = "Server Error"
        err_resp.headers = {}
        mock_post.side_effect = httpx.HTTPStatusError("500", request=MagicMock(), response=err_resp)

        messages = [{"role": "user", "content": "test"}]
        with pytest.raises(LLMConnectionError):
            _call_provider(self._make_provider(), messages, None)
        assert mock_post.call_count == _MAX_RETRIES + 1

    @patch("services.llm_assistant.httpx.post")
    def test_content_filter_not_retried(self, mock_post):
        """Content filter errors should raise immediately without retry."""
        err_resp = MagicMock()
        err_resp.status_code = 400
        err_resp.text = "content moderation filter triggered"
        err_resp.headers = {}
        mock_post.side_effect = httpx.HTTPStatusError("400", request=MagicMock(), response=err_resp)

        messages = [{"role": "user", "content": "test"}]
        with pytest.raises(ContentFilterError):
            _call_provider(self._make_provider(), messages, None)
        assert mock_post.call_count == 1  # no retry


class TestRefreshProviders:
    """Tests for runtime provider refresh."""

    @patch.dict("os.environ", {"CEREBRAS_API_KEY": "new-key", "LLM_API_KEY": ""}, clear=False)
    def test_refresh_updates_provider_list(self):
        refresh_providers()
        from services.llm_assistant import _PROVIDERS as providers
        names = [p["name"] for p in providers]
        assert "cerebras" in names


class TestParseRetryAfter:
    """Tests for Retry-After header parsing."""

    def test_numeric_string(self):
        assert _parse_retry_after("5", 1.0) == 5.0

    def test_float_string(self):
        assert _parse_retry_after("2.5", 1.0) == 2.5

    def test_http_date_returns_default(self):
        assert _parse_retry_after("Fri, 31 Dec 2027 23:59:59 GMT", 3.0) == 3.0

    def test_garbage_returns_default(self):
        assert _parse_retry_after("not-a-number", 3.0) == 3.0

    def test_none_returns_default(self):
        assert _parse_retry_after(None, 2.0) == 2.0

    def test_empty_string_returns_default(self):
        assert _parse_retry_after("", 1.5) == 1.5


class TestDeadlineBudget:
    """Tests that the overall time budget prevents runaway retries."""

    def _make_provider(self):
        return {
            "name": "test",
            "api_key": "key",
            "base_url": "https://test.example.com/v1",
            "model": "test-model",
        }

    @patch("services.llm_assistant.httpx.post")
    @patch("services.llm_assistant._time.sleep")
    def test_deadline_caps_total_duration(self, mock_sleep, mock_post):
        """With a tight deadline, should bail out quickly, not exhaust all retries."""
        import time as real_time
        err_resp = MagicMock()
        err_resp.status_code = 500
        err_resp.text = "Server Error"
        err_resp.headers = {}
        mock_post.side_effect = httpx.HTTPStatusError("500", request=MagicMock(), response=err_resp)

        messages = [{"role": "user", "content": "test"}]
        # Set deadline 0.5s from now — should bail fast
        deadline = real_time.monotonic() + 0.5

        with pytest.raises(LLMConnectionError):
            _call_provider(self._make_provider(), messages, None, deadline=deadline)

    @patch("services.llm_assistant.httpx.post")
    @patch("services.llm_assistant._time.sleep")
    def test_per_call_timeout_clamped_by_deadline(self, mock_sleep, mock_post):
        """The per-call httpx timeout should be clamped to remaining budget."""
        import time as real_time
        ok = MagicMock()
        ok.status_code = 200
        ok.raise_for_status = MagicMock()
        ok.json.return_value = {
            "choices": [{"message": {"content": '{"summary": "test"}'}, "finish_reason": "stop"}],
            "usage": {},
        }
        mock_post.return_value = ok

        messages = [{"role": "user", "content": "test"}]
        deadline = real_time.monotonic() + 10.0  # 10s budget

        _call_provider(self._make_provider(), messages, None, deadline=deadline)

        # Verify the timeout kwarg was clamped below 60s
        call_kwargs = mock_post.call_args
        timeout_used = call_kwargs.kwargs.get("timeout", call_kwargs[1].get("timeout", 60.0))
        assert timeout_used <= 10.0, f"Expected timeout <= 10s, got {timeout_used}"


import httpx

from services.llm_assistant import _parse_xml_response


class TestParseXmlResponse:
    def test_summary_only(self):
        xml = "<response><summary>No flights found for AirSial.</summary></response>"
        result = _parse_xml_response(xml)
        assert result is not None
        assert result["summary"] == "No flights found for AirSial."

    def test_with_layers_and_viewport(self):
        xml = (
            '<response>'
            '<summary>Found 3 flights near Pakistan.</summary>'
            '<layers>{"commercial_flights": true}</layers>'
            '<viewport>{"lat": 30.3, "lng": 69.3, "zoom": 6}</viewport>'
            '<result_entities>[]</result_entities>'
            '</response>'
        )
        result = _parse_xml_response(xml)
        assert result is not None
        assert result["summary"] == "Found 3 flights near Pakistan."
        assert result["layers"] == {"commercial_flights": True}
        assert result["viewport"]["lat"] == 30.3
        assert result["viewport"]["zoom"] == 6

    def test_null_fields(self):
        xml = "<response><summary>Hello</summary><layers>null</layers><viewport>null</viewport></response>"
        result = _parse_xml_response(xml)
        assert result is not None
        assert result["layers"] is None
        assert result["viewport"] is None

    def test_result_entities_list(self):
        xml = (
            '<response><summary>2 results</summary>'
            '<result_entities>[{"type": "flight", "id": "abc123"}]</result_entities>'
            '</response>'
        )
        result = _parse_xml_response(xml)
        assert result is not None
        assert len(result["result_entities"]) == 1
        assert result["result_entities"][0]["id"] == "abc123"

    def test_garbage_returns_none(self):
        assert _parse_xml_response("just some random text") is None

    def test_no_summary_returns_none(self):
        assert _parse_xml_response("<response><layers>null</layers></response>") is None


class TestParseLlmResponseXmlFallback:
    def test_xml_response_parsed(self):
        xml = "<response><summary>No AirSial data available.</summary><layers>null</layers></response>"
        result = parse_llm_response(xml)
        assert result["summary"] == "No AirSial data available."
        assert result["layers"] is None

    def test_xml_with_entities(self):
        xml = (
            '<response><summary>Found flights</summary>'
            '<layers>{"flights": true}</layers>'
            '<viewport>{"lat": 25, "lng": 67, "zoom": 8}</viewport>'
            '<result_entities>[{"type": "flight", "id": "x1"}]</result_entities>'
            '</response>'
        )
        result = parse_llm_response(xml)
        assert result["summary"] == "Found flights"
        assert result["layers"] == {"flights": True}
        assert result["viewport"]["lat"] == 25
        assert len(result["result_entities"]) == 1

    def test_raw_xml_tags_stripped_in_fallback(self):
        """When XML has no <summary> tag, tags should be stripped from the fallback summary."""
        raw = "<data><info>something</info><detail>more</detail></data>"
        result = parse_llm_response(raw)
        # Should not contain XML tags in summary
        assert "<" not in result["summary"]


class TestWebSearch:
    def test_tool_in_definitions(self):
        tools = _build_tools()
        names = [t["function"]["name"] for t in tools]
        assert "web_search" in names

    def test_empty_query_returns_error(self):
        result = json.loads(_exec_web_search({"query": ""}))
        assert "error" in result

    def test_execute_tool_call_routes_web_search(self):
        """web_search should not return 'Unknown tool'."""
        with patch("services.llm_assistant._exec_web_search", return_value='{"result":"ok"}'):
            result = execute_tool_call("web_search", {"query": "test"}, {})
        assert "Unknown tool" not in result

    def test_success_returns_result(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Pakistan flights reduced due to fuel costs."}}]
        }
        with patch("services.llm_assistant.httpx.post", return_value=mock_resp), \
             patch.dict("os.environ", {"LLM_API_KEY": "test-key", "LLM_BASE_URL": "https://example.com/v1"}):
            result = json.loads(_exec_web_search({"query": "Pakistan flight reductions"}))
        assert "result" in result
        assert "Pakistan" in result["result"]

    def test_truncates_long_response(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "x" * 5000}}]
        }
        with patch("services.llm_assistant.httpx.post", return_value=mock_resp), \
             patch.dict("os.environ", {"LLM_API_KEY": "test-key", "LLM_BASE_URL": "https://example.com/v1"}):
            result = json.loads(_exec_web_search({"query": "test"}))
        assert result["result"].endswith("... [truncated]")
        assert len(result["result"]) < 3100

    def test_inline_parser_recognizes_web_search(self):
        text = '<tool_call>web_search<arg_key>query</arg_key><arg_value>Pakistan oil crisis</arg_value></tool_call>'
        calls = _parse_inline_tool_calls(text)
        assert len(calls) == 1
        assert calls[0][0] == "web_search"
        assert calls[0][1]["query"] == "Pakistan oil crisis"
