"""Adapter handlers for old tools (query_data, aggregate_data, web_search).

These wrap the existing execution logic from llm_assistant.py but accept
the (args, ds) signature expected by ToolRegistry. Internally they access
ds._data for backward compatibility with the compact formatters.
"""
from __future__ import annotations

import json
import logging
import os

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Re-exported from llm_assistant — the canonical search config lives there
# but we need it here for the handlers.
# ---------------------------------------------------------------------------

_SEARCH_CONFIG = {
    "commercial_flights": {
        "fields": ["callsign", "icao24", "registration", "origin_name", "dest_name",
                    "origin_country", "dest_country",
                    "airline_code", "airline_name", "country", "model"],
        "entity_type": "flight",
        "compact": lambda f: {
            "icao24": f.get("icao24", ""),
            "callsign": f.get("callsign", ""),
            "airline_name": f.get("airline_name", ""),
            "origin_name": f.get("origin_name", ""),
            "dest_name": f.get("dest_name", ""),
            "origin_country": f.get("origin_country", ""),
            "dest_country": f.get("dest_country", ""),
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

_QUERYABLE_FIELDS = {
    "commercial_flights": ["callsign", "icao24", "origin_name", "dest_name",
                           "origin_country", "dest_country",
                           "airline_code", "airline_name", "country", "model", "aircraft_category"],
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

# Also used by scenario fixtures that have additional categories
_EXTRA_CATEGORIES = {
    "gps_jamming", "news", "gdelt", "firms_fires", "internet_outages",
    "satellites", "oil", "defense_stocks",
}

_MAX_PER_CATEGORY = 100


# ---------------------------------------------------------------------------
# Internal helpers (mirrored from llm_assistant.py)
# ---------------------------------------------------------------------------

def _fuzzy_contains(haystack: str, needle: str) -> bool:
    return needle.lower() in haystack.lower()


def _apply_filters(items: list, filters: dict | None, near: dict | None) -> list:
    from services.geo_gazetteer import entities_in_radius

    result = items
    if filters:
        for field, match_val in filters.items():
            ml = str(match_val)
            result = [e for e in result if _fuzzy_contains(str(e.get(field, "")), ml)]
    if near:
        result = entities_in_radius(
            result, near.get("lat", 0), near.get("lng", 0),
            near.get("radius_km", 200),
        )
    return result


def _get_data_dict(ds) -> dict:
    """Extract raw data dict from a DataSource."""
    if hasattr(ds, "_data"):
        return ds._data
    return {}


# ---------------------------------------------------------------------------
# Handler functions — (args, ds) -> str
# ---------------------------------------------------------------------------

def handle_query_data(args: dict, ds) -> str:
    """Execute a query_data tool call through the registry."""
    data = _get_data_dict(ds)
    category = args.get("category", "")
    config = _SEARCH_CONFIG.get(category)

    # For categories not in _SEARCH_CONFIG (like gps_jamming, news, etc.),
    # return raw items without compact formatting
    items = data.get(category)
    if items is None or not isinstance(items, list):
        if config is None:
            return json.dumps({"error": f"Unknown category: {category}", "total": 0, "results": []})
        return json.dumps({"total": 0, "showing": 0, "results": []})

    # Validate filter keys
    raw_filters = args.get("filters")
    if raw_filters and isinstance(raw_filters, dict):
        valid_fields = set(_QUERYABLE_FIELDS.get(category, []))
        if valid_fields:
            cleaned = {k: v for k, v in raw_filters.items() if k in valid_fields}
            dropped = set(raw_filters) - set(cleaned)
            if dropped:
                logger.warning(f"[query_data] Dropped unknown filter keys for {category}: {dropped}")
            raw_filters = cleaned or None
        # If no valid_fields defined, allow all filter keys through

    filtered = _apply_filters(items, raw_filters, args.get("near"))
    limit = min(max(args.get("limit", 50), 1), 100)

    if config:
        compact = config["compact"]
        results = [compact(e) for e in filtered[:limit]]
    else:
        results = filtered[:limit]

    return json.dumps({"total": len(filtered), "showing": len(results), "results": results})


def handle_aggregate_data(args: dict, ds) -> str:
    """Execute an aggregate_data tool call through the registry."""
    data = _get_data_dict(ds)
    category = args.get("category", "")

    # Allow categories in _SEARCH_CONFIG or present in the data
    if category not in _SEARCH_CONFIG and category not in data:
        return json.dumps({"error": f"Unknown category: {category}"})

    items = data.get(category)
    if not items or not isinstance(items, list):
        return json.dumps({"total_items": 0, "groups": {}})

    # Validate filter keys
    raw_filters = args.get("filters")
    if raw_filters and isinstance(raw_filters, dict):
        valid_fields = set(_QUERYABLE_FIELDS.get(category, []))
        if valid_fields:
            cleaned = {k: v for k, v in raw_filters.items() if k in valid_fields}
            dropped = set(raw_filters) - set(cleaned)
            if dropped:
                logger.warning(f"[aggregate_data] Dropped unknown filter keys for {category}: {dropped}")
            raw_filters = cleaned or None

    filtered = _apply_filters(items, raw_filters, args.get("near"))
    group_by = args.get("group_by", "")

    # Validate group_by field only if we have a known field list
    valid_fields = set(_QUERYABLE_FIELDS.get(category, []))
    if group_by and valid_fields and group_by not in valid_fields:
        return json.dumps({"error": f"Unknown group_by field '{group_by}' for {category}. Valid: {sorted(valid_fields)}"})

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


def _exec_web_search(args: dict) -> str:
    """Call Perplexity sonar via OpenRouter for web search."""
    query = args.get("query", "").strip()
    if not query:
        return json.dumps({"error": "Empty search query"})

    api_key = os.environ.get("LLM_API_KEY", "")
    base_url = os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    if not api_key:
        return json.dumps({"error": "No API key configured for web search"})

    try:
        resp = httpx.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "perplexity/sonar",
                "messages": [{"role": "user", "content": query}],
                "max_tokens": 1024,
            },
            timeout=15,
        )
        if resp.status_code != 200:
            return json.dumps({"error": f"Search failed: HTTP {resp.status_code}"})

        content = resp.json()["choices"][0]["message"]["content"]
        if len(content) > 3000:
            content = content[:3000] + "... [truncated]"
        return json.dumps({"result": content})
    except Exception as e:
        logger.warning(f"web_search failed: {e}")
        return json.dumps({"error": f"Search failed: {str(e)}"})


def handle_web_search(args: dict, ds) -> str:
    """Web search adapter for ToolRegistry — ds is ignored."""
    return _exec_web_search(args)
