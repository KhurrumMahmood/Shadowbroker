"""Tests for unified tool dispatch — old and new tools through one ToolRegistry."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch

from services.agent.datasource import StaticDataSource, InMemoryDataSource

FIXTURES = Path(__file__).parent / "fixtures" / "scenarios"


@pytest.fixture
def hormuz_data():
    """Raw dict matching InMemoryDataSource input (like latest_data)."""
    ds = StaticDataSource(FIXTURES / "hormuz_crisis")
    return ds._data


@pytest.fixture
def hormuz_ds(hormuz_data):
    return InMemoryDataSource(hormuz_data)


class TestRegistryHasAllTools:

    def test_registry_has_9_tools(self):
        from services.agent.registry import create_default_registry

        reg = create_default_registry()
        names = {t.name for t in reg.list_tools()}
        assert len(names) == 9
        # Old tools
        assert "query_data" in names
        assert "aggregate_data" in names
        assert "web_search" in names
        # New tools
        assert "proximity_search" in names
        assert "corridor_analysis" in names
        assert "temporal_compare" in names
        assert "anomaly_scan" in names
        assert "pattern_detect" in names
        assert "cross_correlate" in names

    def test_schemas_have_valid_format(self):
        from services.agent.registry import create_default_registry

        reg = create_default_registry()
        schemas = reg.get_tool_schemas()
        assert len(schemas) == 9
        for schema in schemas:
            assert schema["type"] == "function"
            fn = schema["function"]
            assert "name" in fn
            assert "description" in fn
            assert "parameters" in fn

    def test_query_data_schema_has_category_enum(self):
        from services.agent.registry import create_default_registry

        reg = create_default_registry()
        schemas = reg.get_tool_schemas()
        qd_schema = next(s for s in schemas if s["function"]["name"] == "query_data")
        cat_prop = qd_schema["function"]["parameters"]["properties"]["category"]
        assert "enum" in cat_prop
        assert "ships" in cat_prop["enum"]
        assert "military_flights" in cat_prop["enum"]


class TestQueryDataThroughRegistry:

    def test_query_ships(self, hormuz_ds):
        from services.agent.registry import create_default_registry

        reg = create_default_registry()
        result = reg.execute("query_data", {"category": "ships"}, ds=hormuz_ds)
        parsed = json.loads(result)
        assert parsed["total"] > 0
        assert len(parsed["results"]) > 0

    def test_query_with_filters(self, hormuz_ds):
        from services.agent.registry import create_default_registry

        reg = create_default_registry()
        result = reg.execute(
            "query_data",
            {"category": "ships", "filters": {"country": "Iran"}},
            ds=hormuz_ds,
        )
        parsed = json.loads(result)
        assert parsed["total"] > 0
        for ship in parsed["results"]:
            assert "Iran" in ship.get("country", "")

    def test_query_with_near(self, hormuz_ds):
        from services.agent.registry import create_default_registry

        reg = create_default_registry()
        result = reg.execute(
            "query_data",
            {"category": "ships", "near": {"lat": 26.5, "lng": 56.3, "radius_km": 50}},
            ds=hormuz_ds,
        )
        parsed = json.loads(result)
        assert parsed["total"] > 0

    def test_query_unknown_category(self, hormuz_ds):
        from services.agent.registry import create_default_registry

        reg = create_default_registry()
        result = reg.execute("query_data", {"category": "nonexistent"}, ds=hormuz_ds)
        parsed = json.loads(result)
        assert "error" in parsed or parsed["total"] == 0

    def test_results_are_compact(self, hormuz_ds):
        from services.agent.registry import create_default_registry

        reg = create_default_registry()
        result = reg.execute("query_data", {"category": "ships"}, ds=hormuz_ds)
        parsed = json.loads(result)
        ship = parsed["results"][0]
        # Compact format should have these keys
        assert "mmsi" in ship
        assert "name" in ship
        assert "lat" in ship


class TestAggregateDataThroughRegistry:

    def test_aggregate_ships_by_type(self, hormuz_ds):
        from services.agent.registry import create_default_registry

        reg = create_default_registry()
        result = reg.execute(
            "aggregate_data",
            {"category": "ships", "group_by": "type"},
            ds=hormuz_ds,
        )
        parsed = json.loads(result)
        assert parsed["total_items"] > 0
        assert "top_groups" in parsed
        assert "tanker" in parsed["top_groups"]

    def test_aggregate_unknown_category(self, hormuz_ds):
        from services.agent.registry import create_default_registry

        reg = create_default_registry()
        result = reg.execute(
            "aggregate_data",
            {"category": "nonexistent", "group_by": "type"},
            ds=hormuz_ds,
        )
        parsed = json.loads(result)
        assert "error" in parsed or parsed["total_items"] == 0


class TestWebSearchThroughRegistry:

    @patch("services.agent.tools.query._exec_web_search")
    def test_web_search_dispatches(self, mock_ws):
        from services.agent.registry import create_default_registry

        mock_ws.return_value = json.dumps({"result": "test search result"})
        reg = create_default_registry()
        result = reg.execute("web_search", {"query": "test"}, ds=None)
        parsed = json.loads(result)
        assert parsed["result"] == "test search result"


class TestBackwardCompatExecuteToolCall:
    """Verify execute_tool_call() still works with old (name, args, data) signature."""

    def test_query_data_backward_compat(self, hormuz_data):
        from services.llm_assistant import execute_tool_call

        result = execute_tool_call("query_data", {"category": "ships"}, hormuz_data)
        parsed = json.loads(result)
        assert parsed["total"] > 0

    def test_aggregate_backward_compat(self, hormuz_data):
        from services.llm_assistant import execute_tool_call

        result = execute_tool_call(
            "aggregate_data",
            {"category": "ships", "group_by": "type"},
            hormuz_data,
        )
        parsed = json.loads(result)
        assert parsed["total_items"] > 0

    def test_unknown_tool_backward_compat(self, hormuz_data):
        from services.llm_assistant import execute_tool_call

        result = execute_tool_call("nonexistent", {}, hormuz_data)
        parsed = json.loads(result)
        assert "error" in parsed

    def test_new_tools_work_through_execute_tool_call(self, hormuz_data):
        from services.llm_assistant import execute_tool_call

        result = execute_tool_call(
            "proximity_search",
            {"lat": 26.5, "lng": 56.3, "radius_km": 100},
            hormuz_data,
        )
        parsed = json.loads(result)
        assert "_summary" in parsed
        assert parsed["_summary"]["total_entities"] > 0
