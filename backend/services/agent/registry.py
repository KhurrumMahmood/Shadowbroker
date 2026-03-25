"""Extensible tool registry for the agent system.

Replaces hardcoded tool definitions and dispatch with a registry pattern.
Tools register with their JSON schema and handler; the registry generates
OpenAI-compatible tool schemas and dispatches calls.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class ToolDef:
    """A registered tool definition."""
    name: str
    description: str
    parameters: dict          # JSON Schema for the tool's arguments
    handler: Callable         # (args: dict, ds: DataSource | None) -> str
    categories: list[str] = field(default_factory=lambda: ["all"])


class ToolRegistry:
    """Dynamic tool registry for agent tool dispatch."""

    def __init__(self):
        self._tools: dict[str, ToolDef] = {}

    def register(self, tool: ToolDef):
        """Register a tool (overwrites if name exists)."""
        self._tools[tool.name] = tool

    def list_tools(self) -> list[ToolDef]:
        """List all registered tools."""
        return list(self._tools.values())

    def get_tool_schemas(self, agent_type: str = "all") -> list[dict]:
        """Generate OpenAI-compatible tool schemas.

        If agent_type is specified, only returns tools whose categories
        include that agent type or "all".
        """
        schemas = []
        for tool in self._tools.values():
            if agent_type != "all" and "all" not in tool.categories and agent_type not in tool.categories:
                continue
            schemas.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            })
        return schemas

    def execute(self, name: str, args: dict, ds: Any = None) -> str:
        """Dispatch a tool call to its handler.

        Returns JSON string (either from handler or error).
        """
        tool = self._tools.get(name)
        if tool is None:
            return json.dumps({"error": f"Unknown tool: {name}"})
        try:
            return tool.handler(args, ds)
        except Exception as e:
            logger.warning(f"Tool {name} failed: {e}")
            return json.dumps({"error": f"Tool {name} failed: {str(e)}"})


def create_default_registry() -> ToolRegistry:
    """Create a registry with all 9 tools (3 old + 6 new) registered."""
    from services.agent.tools.query import (
        handle_query_data, handle_aggregate_data, handle_web_search,
        _QUERYABLE_FIELDS,
    )

    reg = ToolRegistry()

    # ── Old tools (query_data, aggregate_data, web_search) ────────────

    category_enum = sorted(_QUERYABLE_FIELDS.keys())

    reg.register(ToolDef(
        name="query_data",
        description=(
            "Query entities from a specific data category. Supports filtering "
            "by field values and geographic proximity. Returns compact entity list."
        ),
        parameters={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": category_enum,
                    "description": "Data category to query",
                },
                "filters": {
                    "type": "object",
                    "description": "Field-value filters (AND logic, case-insensitive contains)",
                },
                "near": {
                    "type": "object",
                    "properties": {
                        "lat": {"type": "number"},
                        "lng": {"type": "number"},
                        "radius_km": {"type": "number"},
                    },
                    "description": "Geographic proximity filter",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 50, max 100)",
                },
            },
            "required": ["category"],
        },
        handler=handle_query_data,
        categories=["all"],
    ))

    reg.register(ToolDef(
        name="aggregate_data",
        description=(
            "Aggregate and count entities in a category, grouped by a field. "
            "Returns top groups with counts. Use for questions like "
            "'how many ships by type?' or 'military flights by country'."
        ),
        parameters={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": category_enum,
                    "description": "Data category to aggregate",
                },
                "group_by": {
                    "type": "string",
                    "description": "Field to group by",
                },
                "filters": {
                    "type": "object",
                    "description": "Optional pre-filters before aggregation",
                },
                "near": {
                    "type": "object",
                    "properties": {
                        "lat": {"type": "number"},
                        "lng": {"type": "number"},
                        "radius_km": {"type": "number"},
                    },
                    "description": "Optional geographic filter before aggregation",
                },
                "top_n": {
                    "type": "integer",
                    "description": "Number of top groups to return (default 20, max 50)",
                },
            },
            "required": ["category", "group_by"],
        },
        handler=handle_aggregate_data,
        categories=["all"],
    ))

    reg.register(ToolDef(
        name="web_search",
        description=(
            "Search the web for current information using Perplexity. "
            "Use for recent events, context, or facts not in the dashboard data."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query",
                },
            },
            "required": ["query"],
        },
        handler=handle_web_search,
        categories=["all", "osint"],
    ))

    # ── New analysis tools ────────────────────────────────────────────

    # -- proximity_search --
    reg.register(ToolDef(
        name="proximity_search",
        description=(
            "Search ALL data categories for entities within a radius of a point. "
            "Returns entities per category plus a summary. Use for multi-domain "
            "spatial awareness (e.g. 'what's near the Strait of Hormuz?')."
        ),
        parameters={
            "type": "object",
            "properties": {
                "lat": {"type": "number", "description": "Center latitude"},
                "lng": {"type": "number", "description": "Center longitude"},
                "radius_km": {"type": "number", "description": "Search radius in km (default 200)"},
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Limit to specific categories (default: all)",
                },
            },
            "required": ["lat", "lng"],
        },
        handler=_handle_proximity_search,
        categories=["all", "geointel"],
    ))

    # -- corridor_analysis --
    reg.register(ToolDef(
        name="corridor_analysis",
        description=(
            "Find entities traveling in a heading band (e.g. eastbound 60-130 degrees). "
            "Detects airlift surges, migration corridors, or coordinated movements."
        ),
        parameters={
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Data category to search"},
                "heading_min": {"type": "number", "description": "Minimum heading (degrees)"},
                "heading_max": {"type": "number", "description": "Maximum heading (degrees)"},
                "model_filter": {
                    "type": "string",
                    "description": "Filter by model/type substring (e.g. 'C-17')",
                },
            },
            "required": ["category", "heading_min", "heading_max"],
        },
        handler=_handle_corridor_analysis,
        categories=["all", "geointel", "sigint"],
    ))

    # -- temporal_compare --
    reg.register(ToolDef(
        name="temporal_compare",
        description=(
            "Compare current entity counts and IDs to a historical snapshot. "
            "Shows what's new, what disappeared, and the % change. "
            "Use for questions like 'what changed in the last 4 hours?'"
        ),
        parameters={
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Data category to compare"},
                "hours_ago": {"type": "number", "description": "Compare against N hours ago"},
            },
            "required": ["category", "hours_ago"],
        },
        handler=_handle_temporal_compare,
        categories=["all", "temporal"],
    ))

    # -- anomaly_scan --
    reg.register(ToolDef(
        name="anomaly_scan",
        description=(
            "Scan data categories for statistical anomalies against rolling baselines. "
            "Returns z-scores and anomaly levels (normal/notable/elevated/critical). "
            "Use for 'what's unusual right now?' questions."
        ),
        parameters={
            "type": "object",
            "properties": {
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Categories to scan (default: all)",
                },
            },
        },
        handler=_handle_anomaly_scan,
        categories=["all", "sigint"],
    ))

    # -- pattern_detect --
    reg.register(ToolDef(
        name="pattern_detect",
        description=(
            "Detect behavioral patterns in entity data. "
            "Pattern types: 'dark_vessel' (ships with blank/suspicious destinations), "
            "'holding_pattern' (entities with very low speed/loitering)."
        ),
        parameters={
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Data category to analyze"},
                "pattern_type": {
                    "type": "string",
                    "enum": ["dark_vessel", "holding_pattern"],
                    "description": "Type of behavioral pattern to detect",
                },
            },
            "required": ["category", "pattern_type"],
        },
        handler=_handle_pattern_detect,
        categories=["all", "sigint"],
    ))

    # -- cross_correlate --
    reg.register(ToolDef(
        name="cross_correlate",
        description=(
            "Analyze co-location of entities across ALL data categories at a point. "
            "Identifies which categories have entities in the same area and which pairs "
            "are co-located. Use for detecting compound situations (conflict + outage + fire)."
        ),
        parameters={
            "type": "object",
            "properties": {
                "lat": {"type": "number", "description": "Center latitude"},
                "lng": {"type": "number", "description": "Center longitude"},
                "radius_km": {"type": "number", "description": "Search radius in km (default 100)"},
            },
            "required": ["lat", "lng"],
        },
        handler=_handle_cross_correlate,
        categories=["all", "geointel", "sigint"],
    ))

    return reg


# ── Handler functions ──────────────────────────────────────────────────
# Each takes (args: dict, ds: DataSource) and returns a JSON string.


def _handle_proximity_search(args: dict, ds) -> str:
    from services.agent.tools.spatial import proximity_search

    result = proximity_search(
        ds,
        lat=args["lat"],
        lng=args["lng"],
        radius_km=args.get("radius_km", 200),
        categories=args.get("categories"),
    )
    return json.dumps(result, default=str)


def _handle_corridor_analysis(args: dict, ds) -> str:
    from services.agent.tools.spatial import corridor_analysis

    result = corridor_analysis(
        ds,
        category=args["category"],
        heading_min=args["heading_min"],
        heading_max=args["heading_max"],
        model_filter=args.get("model_filter"),
    )
    return json.dumps(result, default=str)


def _handle_temporal_compare(args: dict, ds) -> str:
    from services.agent.tools.temporal import temporal_compare

    result = temporal_compare(
        ds,
        category=args["category"],
        hours_ago=args["hours_ago"],
    )
    if result is None:
        return json.dumps({"error": "No historical snapshot available for comparison"})
    return json.dumps(result, default=str)


def _handle_anomaly_scan(args: dict, ds) -> str:
    from services.agent.tools.anomaly import anomaly_scan

    result = anomaly_scan(ds, categories=args.get("categories"))
    return json.dumps(result, default=str)


def _handle_pattern_detect(args: dict, ds) -> str:
    from services.agent.tools.anomaly import pattern_detect

    result = pattern_detect(
        ds,
        category=args["category"],
        pattern_type=args["pattern_type"],
    )
    return json.dumps(result, default=str)


def _handle_cross_correlate(args: dict, ds) -> str:
    from services.agent.tools.correlation import cross_correlate

    result = cross_correlate(
        ds,
        lat=args["lat"],
        lng=args["lng"],
        radius_km=args.get("radius_km", 100),
    )
    return json.dumps(result, default=str)
