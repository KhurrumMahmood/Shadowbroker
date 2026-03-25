"""Tests for the ToolRegistry — extensible tool dispatcher."""
import json
import pytest

from services.agent.registry import ToolRegistry, ToolDef


def _echo_handler(args, ds):
    return json.dumps({"echo": args})


class TestRegistration:

    def test_register_and_list(self):
        reg = ToolRegistry()
        reg.register(ToolDef(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object", "properties": {}},
            handler=_echo_handler,
        ))
        assert "test_tool" in [t.name for t in reg.list_tools()]

    def test_duplicate_name_overwrites(self):
        reg = ToolRegistry()
        reg.register(ToolDef(
            name="test_tool",
            description="v1",
            parameters={"type": "object", "properties": {}},
            handler=_echo_handler,
        ))
        reg.register(ToolDef(
            name="test_tool",
            description="v2",
            parameters={"type": "object", "properties": {}},
            handler=_echo_handler,
        ))
        tools = reg.list_tools()
        assert len(tools) == 1
        assert tools[0].description == "v2"


class TestGetToolSchemas:

    def test_returns_openai_format(self):
        reg = ToolRegistry()
        reg.register(ToolDef(
            name="my_tool",
            description="Does stuff",
            parameters={
                "type": "object",
                "properties": {"x": {"type": "number"}},
                "required": ["x"],
            },
            handler=_echo_handler,
        ))
        schemas = reg.get_tool_schemas()
        assert len(schemas) == 1
        schema = schemas[0]
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "my_tool"
        assert schema["function"]["description"] == "Does stuff"
        assert schema["function"]["parameters"]["properties"]["x"]["type"] == "number"

    def test_filter_by_categories(self):
        reg = ToolRegistry()
        reg.register(ToolDef(
            name="geo_tool",
            description="geo",
            parameters={"type": "object", "properties": {}},
            handler=_echo_handler,
            categories=["geointel"],
        ))
        reg.register(ToolDef(
            name="osint_tool",
            description="osint",
            parameters={"type": "object", "properties": {}},
            handler=_echo_handler,
            categories=["osint"],
        ))
        geo_schemas = reg.get_tool_schemas(agent_type="geointel")
        assert len(geo_schemas) == 1
        assert geo_schemas[0]["function"]["name"] == "geo_tool"

    def test_all_returns_everything(self):
        reg = ToolRegistry()
        reg.register(ToolDef(
            name="a", description="a",
            parameters={"type": "object", "properties": {}},
            handler=_echo_handler, categories=["geointel"],
        ))
        reg.register(ToolDef(
            name="b", description="b",
            parameters={"type": "object", "properties": {}},
            handler=_echo_handler, categories=["osint"],
        ))
        assert len(reg.get_tool_schemas(agent_type="all")) == 2


class TestExecute:

    def test_dispatches_to_handler(self):
        reg = ToolRegistry()
        reg.register(ToolDef(
            name="echo",
            description="echoes",
            parameters={"type": "object", "properties": {}},
            handler=_echo_handler,
        ))
        result = reg.execute("echo", {"msg": "hello"}, ds=None)
        assert json.loads(result) == {"echo": {"msg": "hello"}}

    def test_unknown_tool_returns_error(self):
        reg = ToolRegistry()
        result = reg.execute("nonexistent", {}, ds=None)
        parsed = json.loads(result)
        assert "error" in parsed

    def test_handler_exception_returns_error(self):
        def _bad_handler(args, ds):
            raise ValueError("boom")

        reg = ToolRegistry()
        reg.register(ToolDef(
            name="bad",
            description="will fail",
            parameters={"type": "object", "properties": {}},
            handler=_bad_handler,
        ))
        result = reg.execute("bad", {}, ds=None)
        parsed = json.loads(result)
        assert "error" in parsed
        assert "boom" in parsed["error"]


class TestDefaultRegistry:
    """Test that create_default_registry() wires up all tools."""

    def test_includes_new_tools(self):
        from services.agent.registry import create_default_registry

        reg = create_default_registry()
        names = {t.name for t in reg.list_tools()}
        assert "proximity_search" in names
        assert "corridor_analysis" in names
        assert "temporal_compare" in names
        assert "anomaly_scan" in names
        assert "pattern_detect" in names
        assert "cross_correlate" in names

    def test_new_tools_are_executable(self):
        from services.agent.registry import create_default_registry
        from services.agent.datasource import StaticDataSource
        from pathlib import Path

        reg = create_default_registry()
        ds = StaticDataSource(
            Path(__file__).parent / "fixtures" / "scenarios" / "hormuz_crisis"
        )
        result = reg.execute(
            "proximity_search",
            {"lat": 26.5, "lng": 56.3, "radius_km": 100},
            ds=ds,
        )
        parsed = json.loads(result)
        assert "_summary" in parsed
        assert parsed["_summary"]["total_entities"] > 0

    def test_schemas_have_valid_format(self):
        from services.agent.registry import create_default_registry

        reg = create_default_registry()
        schemas = reg.get_tool_schemas()
        for schema in schemas:
            assert schema["type"] == "function"
            assert "name" in schema["function"]
            assert "description" in schema["function"]
            assert "parameters" in schema["function"]
