"""LLM assistant service — OpenAI-compatible chat completions for OSINT queries.

Supports multi-provider routing: Cerebras (fast, primary) → OpenRouter (fallback).
Uses env vars: CEREBRAS_API_KEY/BASE_URL/MODEL, LLM_API_KEY/BASE_URL/MODEL
"""
import os
import re
import json
import logging
import httpx

logger = logging.getLogger(__name__)


class ContentFilterError(Exception):
    """Raised when the LLM refuses a query due to content policy."""
    pass


class LLMConnectionError(Exception):
    """Raised when the LLM API is unreachable or returns a server error."""
    pass


# Provider configs — tried in order. First available provider with a valid API key is used.
def _build_providers() -> list[dict]:
    providers = []
    # Primary: Cerebras (fast inference)
    cerebras_key = os.environ.get("CEREBRAS_API_KEY", "")
    if cerebras_key:
        providers.append({
            "name": "cerebras",
            "api_key": cerebras_key,
            "base_url": os.environ.get("CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1"),
            "model": os.environ.get("CEREBRAS_MODEL", "zai-glm-4.7"),
        })
    # Fallback: OpenRouter / generic OpenAI-compatible
    llm_key = os.environ.get("LLM_API_KEY", "")
    if llm_key:
        providers.append({
            "name": "openrouter",
            "api_key": llm_key,
            "base_url": os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1"),
            "model": os.environ.get("LLM_MODEL", "gpt-4o-mini"),
        })
    return providers

_PROVIDERS = _build_providers()

# All data layers the frontend can control
_LAYER_NAMES = [
    "flights", "private", "jets", "military", "tracked", "satellites",
    "ships_military", "ships_cargo", "ships_civilian", "ships_passenger",
    "ships_tracked_yachts", "earthquakes", "cctv", "ukraine_frontline",
    "global_incidents", "day_night", "gps_jamming", "kiwisdr", "firms",
    "internet_outages", "datacenters", "military_bases", "power_plants",
]

# Filter keys the frontend supports
_FILTER_KEYS = [
    "commercial_departure", "commercial_arrival", "commercial_airline",
    "private_callsign", "private_aircraft_type",
    "military_country", "military_aircraft_type",
    "tracked_category", "tracked_owner",
    "ship_name", "ship_type",
]


def build_system_prompt(data_summary: dict, search_results: dict | None = None) -> str:
    """Build the system prompt describing available data and expected response format."""
    counts = "\n".join(
        f"  - {k}: {v}" for k, v in data_summary.items() if isinstance(v, (int, float)) and v > 0
    )

    # Format search results if present
    search_section = ""
    if search_results:
        parts = []
        for category, items in search_results.items():
            if category.startswith("_"):
                continue
            if not items:
                continue
            total = search_results.get("_totals", {}).get(category, len(items))
            header = f"{category} ({total} matches, showing {len(items)}):"
            lines = []
            for item in items[:30]:  # max 30 per category in prompt
                if "callsign" in item:
                    origin = item.get("origin_name", "?")
                    dest = item.get("dest_name", "?")
                    lines.append(
                        f"  {item.get('callsign','?')} | {origin}→{dest} | "
                        f"{item.get('model','?')} | alt:{item.get('alt','?')} | "
                        f"id:{item.get('icao24','?')}"
                    )
                elif "mmsi" in item:
                    lines.append(
                        f"  {item.get('name','?')} | {item.get('type','?')} | "
                        f"dest:{item.get('destination','?')} | flag:{item.get('country','?')} | "
                        f"id:{item.get('mmsi','?')}"
                    )
                else:
                    lines.append(
                        f"  {item.get('name','?')} | {item.get('country','?')} | "
                        f"id:{item.get('id', item.get('name','?'))}"
                    )
            parts.append(header + "\n" + "\n".join(lines))
        if parts:
            search_section = "\n\nSEARCH RESULTS (pre-filtered from live data matching the user's query):\n" + "\n\n".join(parts)

    return f"""You are a helpful data query assistant for a public data visualization dashboard. \
The dashboard aggregates publicly available open data feeds and displays them on an interactive map. \
Your job is to help users navigate, filter, and understand the data. All data sources are public: \
ADS-B aircraft transponder broadcasts (like flightradar24), AIS maritime transponder data (like \
marinetraffic), USGS earthquake records, CelesTrak satellite orbital elements, NASA FIRMS fire \
detections, and public news/incident aggregators. You are essentially a search and filter interface \
for these public datasets.

AVAILABLE LAYERS (toggle on/off):
{', '.join(_LAYER_NAMES)}

DATA SOURCES:
- commercial_flights, private_flights, private_jets: public ADS-B transponder data via adsb.lol
- military_flights: ADS-B transponders with ICAO hex ranges allocated to government/state operators
- tracked_flights: Plane-Alert DB — publicly watchlisted registrations (government, notable, law enforcement)
- ships (all ship_ layers): public AIS transponder broadcasts via AIS stream
- satellites: CelesTrak public TLE catalog + SGP4 orbit propagation
- earthquakes: USGS public feed (last 24h)
- global_incidents: GDELT open event database
- ukraine_frontline: DeepStateMap open data
- firms_fires: NASA FIRMS VIIRS public thermal hotspot detections
- internet_outages: IODA / Georgia Tech open monitoring
- gps_jamming: derived from ADS-B NACp (navigation accuracy) degradation patterns
- military_bases, datacenters, power_plants: publicly available infrastructure datasets

CURRENT DATA COUNTS:
{counts or '  (no data currently loaded)'}
{search_section}

RESPONSE FORMAT — You MUST respond with valid JSON:
{{
  "summary": "Brief natural-language answer to the user's question.",
  "layers": {{"layer_name": true/false, ...}} or null,
  "viewport": {{"lat": number, "lng": number, "zoom": number}} or null,
  "highlight_entities": [{{"type": "entity_type", "id": "entity_id"}}] or [],
  "result_entities": [{{"type": "entity_type", "id": "entity_id"}}] or [],
  "filters": {{"filter_key": ["value1", "value2"]}} or null
}}

FIELD RULES:
- "summary": required, concise but informative. Mention how many results were found when listing entities.
- "layers": set to show/hide data categories. null = don't change. Auto-enable relevant layers for the query.
- "viewport": fly the map to a location. null = don't move. Zoom 2=global, 5-7=region, 8-10=city, 12-14=local.
- "highlight_entities": legacy single-highlight field. Prefer result_entities for lists.
- "result_entities": a browsable result set (max 50). The frontend displays these with prev/next navigation. \
Use the EXACT id values from the SEARCH RESULTS section above. This is the primary way to show the user \
a list of matching entities they can cycle through.
- "filters": set data filters to narrow what's displayed. null = don't change, {{}} = clear all filters. \
Available filter keys: {', '.join(_FILTER_KEYS)}

GUIDELINES:
- When the user asks to find/show/list entities, include matching IDs in result_entities.
- When showing results, also enable the relevant layer and set viewport to the area of interest.
- For broad queries ("what's happening here"), summarize notable activity and suggest key entities.
- Keep responses factual — describe what the data shows, not speculation.
- Lat must be -90 to 90, lng -180 to 180, zoom 2 to 14.

TOOLS — you have query_data and aggregate_data functions:
- Use query_data to filter entities by specific field values (case-insensitive substring match) and/or \
by geographic proximity. Prefer this over the SEARCH RESULTS when the query needs precise field matching \
(e.g. origin vs destination), or when results above show UNKNOWN fields.
- Use aggregate_data to count/group entities (e.g. "how many airlines fly from London", "top destination \
countries"). Returns grouped counts.
- You may call multiple tools in parallel to gather data, then produce the final JSON response.
- For simple queries, the SEARCH RESULTS above may be sufficient — use tools when you need precision.

QUERYABLE FIELDS PER CATEGORY:
{chr(10).join(f"- {{k}}: {{', '.join(v)}}" for k, v in _QUERYABLE_FIELDS.items())}

origin_name / dest_name format: "IATA: Airport Name" (e.g. "LHR: London Heathrow", "JFK: John F Kennedy Intl")
Filter with substrings: {{"origin_name": "london"}} matches any origin containing "london"."""


_STOP_WORDS = frozenset([
    "the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "or", "is",
    "are", "was", "were", "be", "been", "being", "have", "has", "had", "do",
    "does", "did", "will", "would", "shall", "should", "may", "might", "can",
    "could", "from", "with", "by", "about", "into", "through", "during",
    "before", "after", "above", "below", "between", "out", "off", "over",
    "under", "again", "further", "then", "once", "here", "there", "all",
    "each", "every", "both", "few", "more", "most", "other", "some", "such",
    "no", "nor", "not", "only", "same", "so", "than", "too", "very",
    "just", "because", "as", "until", "while", "that", "this", "these",
    "those", "it", "its", "i", "me", "my", "we", "our", "you", "your",
    "he", "she", "they", "them", "what", "which", "who", "whom", "how",
    "when", "where", "why", "show", "get", "find", "list", "display",
    "give", "tell", "near", "around", "currently", "right", "now",
])

# Map of data keys → (field lists to search, entity type, compact field extractor)
_SEARCH_CONFIG = {
    "commercial_flights": {
        "fields": ["callsign", "icao24", "registration", "origin_name", "dest_name",
                    "airline_code", "country", "model"],
        "entity_type": "flight",
        "compact": lambda f: {
            "icao24": f.get("icao24", ""),
            "callsign": f.get("callsign", ""),
            "origin_name": f.get("origin_name", ""),
            "dest_name": f.get("dest_name", ""),
            "country": f.get("country", ""),
            "model": f.get("model", ""),
            "lat": f.get("lat"), "lng": f.get("lng"),
            "alt": f.get("alt", 0),
        },
    },
    "military_flights": {
        "fields": ["callsign", "icao24", "registration", "country", "model",
                    "military_type", "origin_name", "dest_name"],
        "entity_type": "military_flight",
        "compact": lambda f: {
            "icao24": f.get("icao24", ""),
            "callsign": f.get("callsign", ""),
            "country": f.get("country", ""),
            "model": f.get("model", ""),
            "lat": f.get("lat"), "lng": f.get("lng"),
            "alt": f.get("alt", 0),
            "origin_name": f.get("origin_name", ""),
            "dest_name": f.get("dest_name", ""),
        },
    },
    "tracked_flights": {
        "fields": ["callsign", "icao24", "registration", "tracked_name",
                    "alert_category", "alert_operator", "country", "model"],
        "entity_type": "tracked_flight",
        "compact": lambda f: {
            "icao24": f.get("icao24", ""),
            "callsign": f.get("callsign", ""),
            "tracked_name": f.get("tracked_name", ""),
            "country": f.get("country", ""),
            "model": f.get("model", ""),
            "lat": f.get("lat"), "lng": f.get("lng"),
            "alt": f.get("alt", 0),
        },
    },
    "private_flights": {
        "fields": ["callsign", "icao24", "registration", "country", "model"],
        "entity_type": "private_flight",
        "compact": lambda f: {
            "icao24": f.get("icao24", ""),
            "callsign": f.get("callsign", ""),
            "country": f.get("country", ""),
            "model": f.get("model", ""),
            "lat": f.get("lat"), "lng": f.get("lng"),
            "alt": f.get("alt", 0),
        },
    },
    "private_jets": {
        "fields": ["callsign", "icao24", "registration", "country", "model"],
        "entity_type": "private_jet",
        "compact": lambda f: {
            "icao24": f.get("icao24", ""),
            "callsign": f.get("callsign", ""),
            "country": f.get("country", ""),
            "model": f.get("model", ""),
            "lat": f.get("lat"), "lng": f.get("lng"),
            "alt": f.get("alt", 0),
        },
    },
    "ships": {
        "fields": ["name", "mmsi", "type", "destination", "country", "callsign"],
        "entity_type": "ship",
        "compact": lambda s: {
            "mmsi": s.get("mmsi", ""),
            "name": s.get("name", ""),
            "type": s.get("type", ""),
            "destination": s.get("destination", ""),
            "country": s.get("country", ""),
            "lat": s.get("lat"), "lng": s.get("lng"),
            "sog": s.get("sog", 0),
        },
    },
    "military_bases": {
        "fields": ["name", "country", "branch"],
        "entity_type": "military_base",
        "compact": lambda b: {
            "id": b.get("name", ""),
            "name": b.get("name", ""),
            "country": b.get("country", ""),
            "branch": b.get("branch", ""),
            "lat": b.get("lat"), "lng": b.get("lng"),
        },
    },
    "datacenters": {
        "fields": ["name", "company", "country"],
        "entity_type": "datacenter",
        "compact": lambda d: {
            "id": d.get("name", ""),
            "name": d.get("name", ""),
            "company": d.get("company", ""),
            "country": d.get("country", ""),
            "lat": d.get("lat"), "lng": d.get("lng"),
        },
    },
    "power_plants": {
        "fields": ["name", "country", "fuel_type"],
        "entity_type": "power_plant",
        "compact": lambda p: {
            "id": p.get("name", ""),
            "name": p.get("name", ""),
            "country": p.get("country", ""),
            "fuel_type": p.get("fuel_type", ""),
            "lat": p.get("lat"), "lng": p.get("lng"),
        },
    },
    "earthquakes": {
        "fields": ["place", "id"],
        "entity_type": "earthquake",
        "compact": lambda e: {
            "id": e.get("id", ""),
            "name": e.get("place", ""),
            "lat": e.get("lat"), "lng": e.get("lng"),
            "mag": e.get("mag", 0),
        },
    },
}

_MAX_PER_CATEGORY = 100

# ---------------------------------------------------------------------------
# Tool calling — structured data queries the LLM can invoke
# ---------------------------------------------------------------------------

# Fields the LLM can filter/group on per category
_QUERYABLE_FIELDS = {
    "commercial_flights": ["callsign", "icao24", "origin_name", "dest_name",
                           "airline_code", "country", "model", "aircraft_category"],
    "military_flights": ["callsign", "icao24", "country", "model",
                         "military_type", "origin_name", "dest_name"],
    "tracked_flights": ["callsign", "icao24", "tracked_name",
                        "alert_category", "alert_operator", "country", "model"],
    "private_flights": ["callsign", "icao24", "country", "model"],
    "private_jets": ["callsign", "icao24", "country", "model"],
    "ships": ["name", "mmsi", "type", "destination", "country", "callsign"],
    "military_bases": ["name", "country", "branch"],
    "datacenters": ["name", "company", "country"],
    "power_plants": ["name", "country", "fuel_type"],
    "earthquakes": ["place", "id", "mag"],
}


def _build_tools() -> list:
    """Build OpenAI-compatible function calling tool definitions."""
    categories = list(_QUERYABLE_FIELDS.keys())
    return [
        {
            "type": "function",
            "function": {
                "name": "query_data",
                "description": (
                    "Search and filter live entities by field values and/or location. "
                    "Returns matching entities with full details. Use for finding specific "
                    "entities (e.g. flights with origin_name containing 'london')."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": categories,
                        },
                        "filters": {
                            "type": "object",
                            "description": (
                                "Field filters (AND logic). Keys = field names, "
                                "values = match strings (case-insensitive substring). "
                                "Example: {\"origin_name\": \"london\", \"dest_name\": \"kennedy\"}"
                            ),
                            "additionalProperties": {"type": "string"},
                        },
                        "near": {
                            "type": "object",
                            "properties": {
                                "lat": {"type": "number"},
                                "lng": {"type": "number"},
                                "radius_km": {"type": "number"},
                            },
                            "required": ["lat", "lng"],
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max results (1-100, default 50)",
                        },
                    },
                    "required": ["category"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "aggregate_data",
                "description": (
                    "Count entities grouped by a field. Use for questions like "
                    "'how many flights per airline' or 'top destination countries'."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": categories,
                        },
                        "group_by": {
                            "type": "string",
                            "description": "Field to group by (e.g. 'airline_code', 'country', 'model', 'dest_name')",
                        },
                        "filters": {
                            "type": "object",
                            "description": "Optional pre-filters (same syntax as query_data)",
                            "additionalProperties": {"type": "string"},
                        },
                        "near": {
                            "type": "object",
                            "properties": {
                                "lat": {"type": "number"},
                                "lng": {"type": "number"},
                                "radius_km": {"type": "number"},
                            },
                            "required": ["lat", "lng"],
                        },
                        "top_n": {
                            "type": "integer",
                            "description": "Top N groups to return (default 20)",
                        },
                    },
                    "required": ["category", "group_by"],
                },
            },
        },
    ]


def _apply_filters(items: list, filters: dict | None, near: dict | None) -> list:
    """Apply field filters (AND, case-insensitive contains) and geo filter."""
    from services.geo_gazetteer import entities_in_radius

    result = items
    if filters:
        for field, match_val in filters.items():
            ml = str(match_val).lower()
            result = [e for e in result if ml in str(e.get(field, "")).lower()]
    if near:
        result = entities_in_radius(
            result, near.get("lat", 0), near.get("lng", 0),
            near.get("radius_km", 200),
        )
    return result


def _exec_query_data(args: dict, data: dict) -> str:
    """Execute a query_data tool call against live data."""
    category = args.get("category", "")
    config = _SEARCH_CONFIG.get(category)
    if not config:
        return json.dumps({"error": f"Unknown category: {category}", "total": 0, "results": []})

    items = data.get(category)
    if not items or not isinstance(items, list):
        return json.dumps({"total": 0, "showing": 0, "results": []})

    filtered = _apply_filters(items, args.get("filters"), args.get("near"))
    limit = min(max(args.get("limit", 50), 1), 100)
    compact = config["compact"]
    results = [compact(e) for e in filtered[:limit]]

    return json.dumps({"total": len(filtered), "showing": len(results), "results": results})


def _exec_aggregate_data(args: dict, data: dict) -> str:
    """Execute an aggregate_data tool call against live data."""
    category = args.get("category", "")
    if category not in _SEARCH_CONFIG:
        return json.dumps({"error": f"Unknown category: {category}"})

    items = data.get(category)
    if not items or not isinstance(items, list):
        return json.dumps({"total_items": 0, "groups": {}})

    filtered = _apply_filters(items, args.get("filters"), args.get("near"))
    group_by = args.get("group_by", "")

    counts: dict[str, int] = {}
    for e in filtered:
        val = str(e.get(group_by, "UNKNOWN")).strip() or "UNKNOWN"
        counts[val] = counts.get(val, 0) + 1

    top_n = min(args.get("top_n", 20), 50)
    sorted_groups = dict(sorted(counts.items(), key=lambda x: -x[1])[:top_n])

    return json.dumps({
        "total_items": len(filtered),
        "unique_values": len(counts),
        "top_groups": sorted_groups,
    })


def _parse_inline_tool_calls(text: str) -> list[tuple[str, dict]]:
    """Parse XML-style tool calls that some models emit as plain text.

    Detects patterns like:
      <tool_call>query_data<arg_key>category</arg_key><arg_value>commercial_flights</arg_value>...</tool_call>

    Returns list of (function_name, args_dict) tuples.
    """
    calls = []
    for m in re.finditer(r'<tool_call>(.*?)</tool_call>', text, re.DOTALL):
        block = m.group(1).strip()
        # First token is the function name
        parts = re.split(r'<arg_key>', block, maxsplit=1)
        fn_name = parts[0].strip()
        if not fn_name or fn_name not in ("query_data", "aggregate_data"):
            continue

        # Parse key-value pairs
        args: dict = {}
        for kv in re.finditer(r'<arg_key>(.*?)</arg_key>\s*<arg_value>(.*?)</arg_value>', block, re.DOTALL):
            key = kv.group(1).strip()
            val = kv.group(2).strip()
            # Try to parse JSON values (dicts, numbers)
            try:
                args[key] = json.loads(val)
            except (json.JSONDecodeError, ValueError):
                args[key] = val
        calls.append((fn_name, args))
    return calls


def execute_tool_call(name: str, args: dict, data: dict) -> str:
    """Route a tool call to the right handler."""
    if name == "query_data":
        return _exec_query_data(args, data)
    elif name == "aggregate_data":
        return _exec_aggregate_data(args, data)
    return json.dumps({"error": f"Unknown tool: {name}"})


def _parse_directional_hints(query: str) -> dict:
    """Extract origin/destination hints from natural language.

    Recognises patterns like:
      "from London to New York"
      "flights out of Heathrow"
      "going to JFK"
      "departing Tokyo heading to Sydney"
      "ships bound for Rotterdam"

    Returns {"origin_terms": [...], "dest_terms": [...]} — lowercase token lists.
    """
    q = query.lower()
    origin_terms: list[str] = []
    dest_terms: list[str] = []

    # "from X" / "out of X" / "departing X" / "leaving X" → origin
    for m in re.finditer(r'(?:from|out of|departing|leaving)\s+([a-z][a-z\s]{1,40}?)(?=\s+(?:to|toward|towards|heading|going|bound|into)\b|$)', q):
        origin_terms.extend(t for t in m.group(1).split() if t not in _STOP_WORDS and len(t) > 1)

    # "to X" / "heading to X" / "going to X" / "bound for X" / "into X" → dest
    for m in re.finditer(r'(?:to|toward|towards|heading to|going to|bound for|into|arriving|landing)\s+([a-z][a-z\s]{1,40}?)(?=\s*$|[,.])', q):
        dest_terms.extend(t for t in m.group(1).split() if t not in _STOP_WORDS and len(t) > 1)

    return {"origin_terms": origin_terms, "dest_terms": dest_terms}


# Fields that represent origin vs destination for directional scoring
_ORIGIN_FIELDS = {"origin_name", "origin_country"}
_DEST_FIELDS = {"dest_name", "destination", "dest_country"}


def search_entities(query: str, data: dict, viewport: dict | None = None) -> dict:
    """Search entity data using keyword + geographic + directional matching.

    Returns dict with category keys mapping to compact entity lists,
    plus '_totals' with full match counts per category.
    """
    from services.geo_gazetteer import find_location, entities_in_radius

    if not query or not query.strip():
        return {}

    # Tokenize query
    tokens = [t for t in query.lower().split() if t not in _STOP_WORDS and len(t) > 1]

    # Parse directional hints ("from X to Y")
    hints = _parse_directional_hints(query)
    has_direction = bool(hints["origin_terms"] or hints["dest_terms"])

    # Geographic filter: check if query references a known location
    geo_loc = find_location(query.lower())

    results: dict = {}
    totals: dict = {}

    for data_key, config in _SEARCH_CONFIG.items():
        items = data.get(data_key)
        if not items or not isinstance(items, list):
            continue

        # Build geo proximity set for bonus scoring
        geo_set: set | None = None
        if geo_loc:
            geo_filtered = entities_in_radius(
                items, geo_loc["lat"], geo_loc["lng"], geo_loc["radius_km"]
            )
            geo_set = set(id(e) for e in geo_filtered) if geo_filtered else set()

        # Score each entity by keyword + geo + directional match
        scored = []
        for entity in items:
            score = 0

            # Directional scoring — boost origin/dest field matches heavily
            if has_direction:
                for field_name in config["fields"]:
                    val = str(entity.get(field_name, "")).lower()
                    if not val:
                        continue
                    is_origin_field = field_name in _ORIGIN_FIELDS
                    is_dest_field = field_name in _DEST_FIELDS
                    for token in hints["origin_terms"]:
                        if is_origin_field and token in val:
                            score += 20  # strong origin match
                        elif not is_dest_field and token in val:
                            score += 2   # weak match in non-dest field
                    for token in hints["dest_terms"]:
                        if is_dest_field and token in val:
                            score += 20  # strong dest match
                        elif not is_origin_field and token in val:
                            score += 2   # weak match in non-origin field

            # General keyword scoring
            for field_name in config["fields"]:
                val = str(entity.get(field_name, "")).lower()
                if not val:
                    continue
                for token in tokens:
                    if val == token:
                        score += 10
                    elif val.startswith(token):
                        score += 5
                    elif token in val:
                        score += 2

            # Geo bonus: entities in the geographic area get extra score
            is_geo_match = geo_set is not None and id(entity) in geo_set
            if is_geo_match:
                score += 5  # geo proximity bonus

            # Include if keyword matched, or geo-only (when no keyword tokens)
            if score > 0:
                scored.append((score, entity))
            elif is_geo_match and not tokens:
                scored.append((1, entity))  # geo-only match

        if not scored:
            continue

        # Sort by score descending
        scored.sort(key=lambda x: -x[0])
        totals[data_key] = len(scored)
        results[data_key] = [config["compact"](e) for _, e in scored[:_MAX_PER_CATEGORY]]

    results["_totals"] = totals
    return results


def parse_llm_response(raw: str) -> dict:
    """Parse LLM output into structured response, handling markdown fences and invalid JSON."""
    # Try to extract JSON from markdown code fences
    fence_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', raw, re.DOTALL)
    text = fence_match.group(1).strip() if fence_match else raw.strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        # Truncated JSON — try to salvage the summary field
        summary_match = re.search(r'"summary"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
        if summary_match:
            return {
                "summary": summary_match.group(1),
                "layers": None,
                "viewport": None,
                "highlight_entities": [],
                "result_entities": [],
                "filters": None,
            }
        # Fallback: return the raw text as summary
        return {
            "summary": raw.strip()[:500],
            "layers": None,
            "viewport": None,
            "highlight_entities": [],
            "result_entities": [],
            "filters": None,
        }

    # Ensure required keys exist with defaults
    result.setdefault("summary", "")
    result.setdefault("layers", None)
    result.setdefault("viewport", None)
    result.setdefault("highlight_entities", [])
    result.setdefault("result_entities", [])
    result.setdefault("filters", None)

    # Clamp viewport to valid ranges
    vp = result.get("viewport")
    if vp and isinstance(vp, dict):
        if "lat" in vp:
            vp["lat"] = max(-90, min(90, vp["lat"]))
        if "lng" in vp:
            vp["lng"] = max(-180, min(180, vp["lng"]))
        if "zoom" in vp:
            vp["zoom"] = max(1, min(20, vp["zoom"]))

    # Filter layers to only known keys
    layers = result.get("layers")
    if layers and isinstance(layers, dict):
        result["layers"] = {k: bool(v) for k, v in layers.items() if k in _LAYER_NAMES}

    # Validate result_entities — max 50, must have type and id
    re_list = result.get("result_entities")
    if isinstance(re_list, list):
        validated = []
        for e in re_list[:50]:
            if isinstance(e, dict) and "type" in e and "id" in e:
                validated.append({"type": str(e["type"]), "id": e["id"]})
        result["result_entities"] = validated
    else:
        result["result_entities"] = []

    # Validate filters — keys must be known filter keys
    filters = result.get("filters")
    if isinstance(filters, dict):
        validated_filters = {}
        for k, v in filters.items():
            if k in _FILTER_KEYS and isinstance(v, list):
                validated_filters[k] = [str(x) for x in v]
        result["filters"] = validated_filters  # {} means clear all, non-empty means set
    else:
        result["filters"] = None

    return result


def _build_messages(query: str, data_summary: dict, viewport: dict | None,
                     conversation: list | None, search_results: dict | None) -> list:
    """Build the messages array for an LLM call (shared across providers)."""
    system_prompt = build_system_prompt(data_summary, search_results=search_results)
    if viewport:
        system_prompt += (
            f"\n\nThe user's current map viewport: south={viewport.get('south')}, "
            f"west={viewport.get('west')}, north={viewport.get('north')}, east={viewport.get('east')}"
        )

    messages = [{"role": "system", "content": system_prompt}]

    if conversation:
        _ERROR_MARKERS = ("Cannot reach", "LLM service unavailable", "Query filtered",
                          "Connection error", "Error:", "content_filter")
        cleaned = []
        skip_prior_user = False
        for msg in reversed(conversation[-12:]):
            role = msg.get("role", "")
            content = msg.get("content", "")
            if not role or not content:
                continue
            if role == "assistant" and any(m in content for m in _ERROR_MARKERS):
                skip_prior_user = True
                continue
            if role == "user" and skip_prior_user:
                skip_prior_user = False
                continue
            skip_prior_user = False
            cleaned.append(msg)
        for msg in reversed(cleaned[-10:]):
            messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": query})
    return messages


def _call_provider(provider: dict, messages: list, live_data: dict | None) -> dict:
    """Run the tool-calling loop against a single provider. Returns parsed response.

    Raises ContentFilterError, LLMConnectionError on failure.
    """
    url = f"{provider['base_url'].rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {provider['api_key']}",
        "Content-Type": "application/json",
    }
    model = provider["model"]
    pname = provider["name"]
    tools = _build_tools() if live_data else None
    # Work on a copy of messages so tool-loop appends don't leak across providers
    msgs = list(messages)

    for _round in range(3):
        payload: dict = {
            "model": model,
            "messages": msgs,
            "temperature": 0.3,
        }
        # Cerebras renamed max_tokens → max_completion_tokens (includes reasoning tokens)
        if pname == "cerebras":
            payload["max_completion_tokens"] = 8192  # higher budget for interleaved thinking
        else:
            payload["max_tokens"] = 4096
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            resp = httpx.post(url, json=payload, headers=headers, timeout=60.0)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            body = e.response.text[:300]
            logger.error(f"[{pname}] LLM API error: {status} — {body}")
            if tools and status == 400:
                logger.warning(f"[{pname}] Retrying without tools")
                tools = None
                continue
            if status in (400, 422) and ("content" in body.lower() or "moderation" in body.lower() or "filter" in body.lower()):
                raise ContentFilterError(f"The LLM provider rejected this query (HTTP {status}).")
            raise LLMConnectionError(f"[{pname}] LLM API returned {status}")
        except httpx.TimeoutException:
            logger.error(f"[{pname}] LLM API request timed out")
            raise LLMConnectionError(f"[{pname}] LLM request timed out")
        except (httpx.ConnectError, httpx.NetworkError, ConnectionError, OSError) as e:
            logger.error(f"[{pname}] LLM connection failed: {e}")
            raise LLMConnectionError(f"[{pname}] Cannot reach LLM API: {e}")
        except Exception as e:
            logger.error(f"[{pname}] LLM call failed: {e}")
            raise LLMConnectionError(f"[{pname}] LLM call failed: {e}")

        resp_data = resp.json()
        choice = resp_data["choices"][0]
        message = choice.get("message", {})

        # --- Structured tool_calls (OpenAI-native) ---
        tool_calls = message.get("tool_calls")
        if tool_calls and live_data:
            msgs.append(message)
            for tc in tool_calls:
                fn_name = tc["function"]["name"]
                try:
                    fn_args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    fn_args = {}
                logger.info(f"[{pname}] Tool call (native): {fn_name}({json.dumps(fn_args)[:200]})")
                result_str = execute_tool_call(fn_name, fn_args, live_data)
                msgs.append({"role": "tool", "tool_call_id": tc["id"], "content": result_str})
            tools = None
            continue

        # --- XML-style tool calls in text content ---
        raw_content = message.get("content", "")
        inline_calls = _parse_inline_tool_calls(raw_content)
        if inline_calls and live_data and _round < 2:
            tool_results = []
            for fn_name, fn_args in inline_calls:
                logger.info(f"[{pname}] Tool call (inline XML): {fn_name}({json.dumps(fn_args)[:200]})")
                result_str = execute_tool_call(fn_name, fn_args, live_data)
                tool_results.append(f"[{fn_name}] {result_str}")
            msgs.append({"role": "assistant", "content": raw_content})
            msgs.append({
                "role": "user",
                "content": (
                    "Here are the results from the data queries you requested:\n\n"
                    + "\n\n".join(tool_results)
                    + "\n\nNow produce the final JSON response using these results. "
                    "Remember: respond ONLY with the JSON object containing summary, layers, "
                    "viewport, result_entities, etc. Do NOT output any tool calls."
                ),
            })
            continue

        # --- Normal text response ---
        finish = choice.get("finish_reason", "")
        if finish == "content_filter":
            raise ContentFilterError("The query was filtered by the LLM provider's content policy.")
        refusal = message.get("refusal")
        if refusal:
            raise ContentFilterError(refusal)
        if not raw_content:
            raise ContentFilterError("The LLM returned an empty response — the query may have been filtered.")
        if finish == "length":
            logger.warning(f"[{pname}] LLM response truncated (finish_reason=length)")
        logger.info(f"[{pname}] LLM responded successfully")
        return parse_llm_response(raw_content)

    logger.warning(f"[{pname}] Tool-calling loop exhausted")
    return {
        "summary": "The analysis is taking too long. Please try a simpler query.",
        "layers": None, "viewport": None,
        "highlight_entities": [], "result_entities": [], "filters": None,
    }


def call_llm(query: str, data_summary: dict, viewport: dict | None = None,
             conversation: list | None = None,
             search_results: dict | None = None,
             live_data: dict | None = None) -> dict:
    """Call the LLM with optional tool use and return a parsed structured response.

    Tries providers in order (Cerebras → OpenRouter). Falls back on connection/timeout
    errors. Content-filter errors are NOT retried (they'll fail on any provider).

    Raises RuntimeError if no LLM is configured.
    """
    if not _PROVIDERS:
        raise RuntimeError("LLM not configured — set CEREBRAS_API_KEY or LLM_API_KEY")

    messages = _build_messages(query, data_summary, viewport, conversation, search_results)

    last_error = None
    for provider in _PROVIDERS:
        try:
            return _call_provider(provider, messages, live_data)
        except ContentFilterError:
            raise  # don't retry content filters on another provider
        except LLMConnectionError as e:
            last_error = e
            if len(_PROVIDERS) > 1:
                logger.warning(f"[{provider['name']}] failed, falling back to next provider: {e}")
            continue

    raise LLMConnectionError(f"All LLM providers failed. Last error: {last_error}")


# --- Viewport Briefing ---

# Map data keys → (layer name to suggest, entity type, notable predicate)
_BRIEF_CONFIG = {
    "commercial_flights": {
        "layer": "flights",
        "entity_type": "flight",
        "id_key": "icao24",
        "name_key": "callsign",
    },
    "military_flights": {
        "layer": "military",
        "entity_type": "military_flight",
        "id_key": "icao24",
        "name_key": "callsign",
        "always_notable": True,
        "notable_why": "government/state operator aircraft (public ADS-B)",
    },
    "tracked_flights": {
        "layer": "tracked",
        "entity_type": "tracked_flight",
        "id_key": "icao24",
        "name_key": "callsign",
        "always_notable": True,
        "notable_why": "watchlisted registration (Plane-Alert DB)",
    },
    "private_flights": {
        "layer": "private",
        "entity_type": "private_flight",
        "id_key": "icao24",
        "name_key": "callsign",
    },
    "private_jets": {
        "layer": "jets",
        "entity_type": "private_jet",
        "id_key": "icao24",
        "name_key": "callsign",
    },
    "ships": {
        "layer": None,  # ships have sub-layers, handled specially
        "entity_type": "ship",
        "id_key": "mmsi",
        "name_key": "name",
    },
    "earthquakes": {
        "layer": "earthquakes",
        "entity_type": "earthquake",
        "id_key": "id",
        "name_key": "place",
    },
    "military_bases": {
        "layer": "military_bases",
        "entity_type": "military_base",
        "id_key": "name",
        "name_key": "name",
    },
    "satellites": {
        "layer": "satellites",
        "entity_type": "satellite",
        "id_key": "id",
        "name_key": "name",
    },
}

# Ship types that are always notable
_NOTABLE_SHIP_TYPES = {"carrier", "military_vessel"}


def _in_bbox(item: dict, viewport: dict) -> bool:
    """Check if an item is within viewport bounds (with 20% padding)."""
    lat = item.get("lat")
    lng = item.get("lng")
    if lat is None or lng is None:
        return False
    s, n = viewport["south"], viewport["north"]
    w, e = viewport["west"], viewport["east"]
    pad_lat = (n - s) * 0.2
    pad_lng = (e - w) * 0.2 if e > w else ((e + 360 - w) * 0.2)
    s2, n2 = s - pad_lat, n + pad_lat
    w2, e2 = w - pad_lng, e + pad_lng
    if not (s2 <= lat <= n2):
        return False
    if w2 > e2:  # antimeridian
        return lng >= w2 or lng <= e2
    return w2 <= lng <= e2


def build_briefing_context(data: dict, viewport: dict) -> dict:
    """Build a structured briefing of what's visible in the current viewport.

    Returns dict with: counts, notable, suggested_layers, summary_text.
    """
    counts: dict[str, int] = {}
    notable: list[dict] = []
    suggested_layers: dict[str, bool] = {}

    for data_key, cfg in _BRIEF_CONFIG.items():
        items = data.get(data_key)
        if not items or not isinstance(items, list):
            counts[data_key] = 0
            continue

        in_view = [i for i in items if _in_bbox(i, viewport)]
        counts[data_key] = len(in_view)

        # Suggest enabling layers that have data
        if in_view and cfg["layer"]:
            suggested_layers[cfg["layer"]] = True

        # Ship sub-layers
        if data_key == "ships" and in_view:
            ship_types_seen = set(s.get("type", "") for s in in_view)
            if ship_types_seen & {"carrier", "military_vessel"}:
                suggested_layers["ships_military"] = True
            if "cargo" in ship_types_seen:
                suggested_layers["ships_cargo"] = True
            if ship_types_seen & {"passenger", "yacht", "other", "unknown"}:
                suggested_layers["ships_civilian"] = True

        # Pick notable entities
        for item in in_view:
            is_notable = False
            why = ""

            if cfg.get("always_notable"):
                is_notable = True
                why = cfg.get("notable_why", "notable entity")

            elif data_key == "ships":
                ship_type = item.get("type", "")
                if ship_type in _NOTABLE_SHIP_TYPES:
                    is_notable = True
                    why = f"{ship_type} vessel (public AIS)"
                elif item.get("yacht_alert"):
                    is_notable = True
                    why = "tracked yacht"

            elif data_key == "earthquakes":
                mag = item.get("mag", 0)
                if mag >= 4.0:
                    is_notable = True
                    why = f"magnitude {mag} seismic event (USGS)"

            if is_notable:
                notable.append({
                    "type": cfg["entity_type"],
                    "id": item.get(cfg["id_key"], ""),
                    "name": str(item.get(cfg["name_key"], "Unknown")),
                    "why": why,
                })

    # Build summary text
    parts = []
    total = sum(counts.values())
    if total == 0:
        summary_text = "No tracked entities in the current viewport."
    else:
        for key, count in counts.items():
            if count > 0:
                label = key.replace("_", " ")
                parts.append(f"{count} {label}")
        summary_text = f"Viewport contains: {', '.join(parts)}."
        if notable:
            summary_text += f" {len(notable)} notable items flagged."

    return {
        "counts": counts,
        "notable": notable,
        "suggested_layers": suggested_layers,
        "summary_text": summary_text,
    }


def build_briefing_prompt(briefing_context: dict) -> str:
    """Build a system prompt for the briefing LLM call."""
    notable_section = ""
    if briefing_context["notable"]:
        lines = []
        for n in briefing_context["notable"][:20]:
            lines.append(f"  - [{n['type']}] {n['name']}: {n['why']}")
        notable_section = "\nNOTABLE ITEMS:\n" + "\n".join(lines)

    return f"""You are a data summary assistant for a public data visualization dashboard. All data is publicly available \
(ADS-B transponders, AIS maritime data, USGS seismic, CelesTrak TLEs, open incident reports).

Provide a concise situational summary of what the user is looking at. Focus on:
1. Key items of interest (carriers, government aircraft, tracked entities, significant seismic activity)
2. General traffic patterns and density
3. Any unusual or noteworthy observations

VIEWPORT DATA:
{briefing_context['summary_text']}
{notable_section}

Respond with a natural-language paragraph (2-4 sentences). Be concise and factual. Do NOT use JSON."""
