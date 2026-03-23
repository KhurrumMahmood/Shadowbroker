"""LLM assistant service — OpenAI-compatible chat completions for OSINT queries.

Uses env vars: LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
"""
import os
import re
import json
import logging
import httpx

logger = logging.getLogger(__name__)

_API_KEY = os.environ.get("LLM_API_KEY", "")
_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")

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

    return f"""You are the ShadowBroker analyst — an open-source intelligence (OSINT) monitoring assistant \
embedded in a real-time global situational awareness dashboard. All data shown is publicly available: \
ADS-B aircraft transponder broadcasts, AIS maritime transponder data, USGS seismic records, \
CelesTrak satellite TLEs, and open incident reports. Your role is to help analysts navigate, filter, \
and understand this public data efficiently.

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
- Lat must be -90 to 90, lng -180 to 180, zoom 2 to 14."""


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
        "entity_type": "commercial_flight",
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


def search_entities(query: str, data: dict, viewport: dict | None = None) -> dict:
    """Search entity data using keyword + geographic matching.

    Returns dict with category keys mapping to compact entity lists,
    plus '_totals' with full match counts per category.
    """
    from services.geo_gazetteer import find_location, entities_in_radius

    if not query or not query.strip():
        return {}

    # Tokenize query
    tokens = [t for t in query.lower().split() if t not in _STOP_WORDS and len(t) > 1]

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

        # Score each entity by keyword + geo match
        scored = []
        for entity in items:
            score = 0

            # Keyword scoring
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
        # Fallback: return the raw text as summary
        return {
            "summary": raw.strip(),
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
        result["filters"] = validated_filters if validated_filters else None
    else:
        result["filters"] = None

    return result


def call_llm(query: str, data_summary: dict, viewport: dict | None = None,
             conversation: list | None = None,
             search_results: dict | None = None) -> dict:
    """Call the LLM and return a parsed structured response.

    Raises RuntimeError if LLM is not configured.
    """
    if not _API_KEY:
        raise RuntimeError("LLM not configured — set LLM_API_KEY environment variable")

    system_prompt = build_system_prompt(data_summary, search_results=search_results)
    if viewport:
        system_prompt += f"\n\nThe user's current map viewport: south={viewport.get('south')}, west={viewport.get('west')}, north={viewport.get('north')}, east={viewport.get('east')}"

    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history if provided
    if conversation:
        for msg in conversation[-10:]:  # Last 10 messages max
            if msg.get("role") in ("user", "assistant") and msg.get("content"):
                messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": query})

    url = f"{_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": _MODEL,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 2048,
    }

    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()
        raw_content = data["choices"][0]["message"]["content"]
        return parse_llm_response(raw_content)
    except httpx.HTTPStatusError as e:
        logger.error(f"LLM API error: {e.response.status_code} — {e.response.text[:200]}")
        raise RuntimeError(f"LLM API returned {e.response.status_code}")
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise RuntimeError(f"LLM call failed: {e}")


# --- Viewport Briefing ---

# Map data keys → (layer name to suggest, entity type, notable predicate)
_BRIEF_CONFIG = {
    "commercial_flights": {
        "layer": "flights",
        "entity_type": "commercial_flight",
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

    return f"""You are the ShadowBroker analyst providing a viewport briefing. All data is publicly available \
(ADS-B transponders, AIS maritime data, USGS seismic, CelesTrak TLEs, open incident reports).

Provide a concise situational summary of what the user is looking at. Focus on:
1. Key items of interest (carriers, government aircraft, tracked entities, significant seismic activity)
2. General traffic patterns and density
3. Any unusual or noteworthy observations

VIEWPORT DATA:
{briefing_context['summary_text']}
{notable_section}

Respond with a natural-language paragraph (2-4 sentences). Be concise and factual. Do NOT use JSON."""
