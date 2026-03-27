"""FIMI (Foreign Information Manipulation and Interference) tracker.

Fetches disinformation narratives from EUvsDisinfo RSS feed.
Extracts threat actors, target countries, and narrative summaries.
No API key required.

Ported from upstream BigBodyCobain/Shadowbroker v0.9.6.
"""

import hashlib
import logging
import re
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime

from services.network_utils import fetch_with_curl
from services.fetchers._store import latest_data, _data_lock, _mark_fresh
from services.fetchers.retry import with_retry

logger = logging.getLogger(__name__)

# Threat actor keywords → canonical names
_THREAT_ACTORS = {
    "russia": "Russia", "russian": "Russia", "kremlin": "Russia", "moscow": "Russia",
    "china": "China", "chinese": "China", "beijing": "China", "prc": "China",
    "iran": "Iran", "iranian": "Iran", "tehran": "Iran",
    "north korea": "North Korea", "dprk": "North Korea", "pyongyang": "North Korea",
    "belarus": "Belarus", "belarusian": "Belarus", "minsk": "Belarus",
}

# Target country keywords → canonical names + centroids for map rendering
_COUNTRY_CENTROIDS: dict[str, dict] = {
    "Ukraine": {"lat": 48.38, "lng": 31.17},
    "United States": {"lat": 39.83, "lng": -98.58},
    "United Kingdom": {"lat": 55.38, "lng": -3.44},
    "Germany": {"lat": 51.17, "lng": 10.45},
    "France": {"lat": 46.23, "lng": 2.21},
    "Poland": {"lat": 51.92, "lng": 19.15},
    "Lithuania": {"lat": 55.17, "lng": 23.88},
    "Latvia": {"lat": 56.88, "lng": 24.60},
    "Estonia": {"lat": 58.60, "lng": 25.01},
    "EU": {"lat": 50.85, "lng": 4.35},  # Brussels
    "NATO": {"lat": 50.85, "lng": 4.35},
    "Moldova": {"lat": 47.41, "lng": 28.37},
    "Georgia": {"lat": 42.32, "lng": 43.36},
    "Romania": {"lat": 45.94, "lng": 24.97},
    "Czech Republic": {"lat": 49.82, "lng": 15.47},
    "Slovakia": {"lat": 48.67, "lng": 19.70},
    "Finland": {"lat": 61.92, "lng": 25.75},
    "Sweden": {"lat": 60.13, "lng": 18.64},
    "Norway": {"lat": 60.47, "lng": 8.47},
    "Spain": {"lat": 40.46, "lng": -3.75},
    "Italy": {"lat": 41.87, "lng": 12.57},
    "Netherlands": {"lat": 52.13, "lng": 5.29},
    "Belgium": {"lat": 50.50, "lng": 4.47},
    "Japan": {"lat": 36.20, "lng": 138.25},
    "South Korea": {"lat": 35.91, "lng": 127.77},
    "Taiwan": {"lat": 23.70, "lng": 120.96},
    "Australia": {"lat": -25.27, "lng": 133.78},
    "Canada": {"lat": 56.13, "lng": -106.35},
    "India": {"lat": 20.59, "lng": 78.96},
    "Syria": {"lat": 34.80, "lng": 38.99},
}

_COUNTRY_KEYWORDS: dict[str, str] = {name.lower(): name for name in _COUNTRY_CENTROIDS}

# Threat actor → color for map rendering
ACTOR_COLORS = {
    "Russia": "#e53e3e",      # red
    "China": "#d69e2e",       # yellow/gold
    "Iran": "#38a169",        # green
    "North Korea": "#805ad5", # purple
    "Belarus": "#ed8936",     # orange
}
DEFAULT_COLOR = "#718096"     # gray


def _extract_threat_actors(text: str) -> list[str]:
    """Extract threat actor names from narrative text."""
    text_lower = text.lower()
    found = set()
    for keyword, actor in _THREAT_ACTORS.items():
        if keyword in text_lower:
            found.add(actor)
    return sorted(found)


def _extract_target_countries(text: str) -> list[str]:
    """Extract target country names from narrative text."""
    text_lower = text.lower()
    found = set()
    for keyword, country in _COUNTRY_KEYWORDS.items():
        # Word-boundary check to avoid false matches
        if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
            found.add(country)
    return sorted(found)


def _make_id(title: str) -> str:
    """Stable hash ID from title."""
    return hashlib.md5(title.encode()).hexdigest()[:12]


def _parse_rss(xml_text: str) -> list[dict]:
    """Parse EUvsDisinfo RSS feed into narrative dicts."""
    narratives = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        logger.warning("FIMI: failed to parse RSS XML")
        return []

    channel = root.find("channel")
    if channel is None:
        return []

    for item in channel.findall("item"):
        title = (item.findtext("title") or "").strip()
        description = (item.findtext("description") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()

        if not title:
            continue

        combined_text = f"{title} {description}"
        actors = _extract_threat_actors(combined_text)
        targets = _extract_target_countries(combined_text)
        primary_actor = actors[0] if actors else None
        color = ACTOR_COLORS.get(primary_actor, DEFAULT_COLOR) if primary_actor else DEFAULT_COLOR

        # Parse date
        parsed_date = None
        if pub_date:
            for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
                try:
                    parsed_date = datetime.strptime(pub_date, fmt).isoformat()
                    break
                except ValueError:
                    continue

        narrative = {
            "id": _make_id(title),
            "title": title,
            "description": description[:500],
            "link": link,
            "pub_date": parsed_date or pub_date,
            "threat_actors": actors,
            "target_countries": targets,
            "primary_actor": primary_actor,
            "color": color,
            "_source": "fimi",
        }

        # Geolocate: create one entry per target country with coordinates
        if targets:
            for country in targets:
                centroid = _COUNTRY_CENTROIDS.get(country)
                if centroid:
                    geo_narrative = {
                        **narrative,
                        "id": f"{narrative['id']}-{country.lower().replace(' ', '_')}",
                        "target_country": country,
                        "lat": centroid["lat"],
                        "lng": centroid["lng"],
                    }
                    narratives.append(geo_narrative)
        else:
            # No target country identified — still store for agent access
            narratives.append({**narrative, "target_country": None, "lat": None, "lng": None})

    return narratives


def _detect_major_waves(narratives: list[dict]) -> list[dict]:
    """Flag narratives that are part of a coordinated wave.

    Simple heuristic: if 3+ narratives share the same primary actor
    within the current batch, mark them as a wave.
    """
    actor_counts = Counter(n.get("primary_actor") for n in narratives if n.get("primary_actor"))
    wave_actors = {actor for actor, count in actor_counts.items() if count >= 3}

    for n in narratives:
        n["is_major_wave"] = n.get("primary_actor") in wave_actors

    return narratives


_EUVSDISINFO_RSS = "https://euvsdisinfo.eu/feed/"


@with_retry(max_retries=1, base_delay=10)
def fetch_fimi():
    """Fetch FIMI narratives from EUvsDisinfo RSS feed."""
    response = fetch_with_curl(_EUVSDISINFO_RSS, timeout=20)
    if not response or not response.text:
        logger.warning("FIMI: empty response from EUvsDisinfo")
        return

    narratives = _parse_rss(response.text)
    narratives = _detect_major_waves(narratives)

    logger.info(f"FIMI: fetched {len(narratives)} narrative entries")

    with _data_lock:
        latest_data["fimi"] = narratives
    _mark_fresh("fimi")
