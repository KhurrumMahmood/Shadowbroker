"""Meshtastic LoRa mesh network node positions.

Fetches node positions from Liam Cottle's community API.
Free, no authentication. Large response (~37MB) so fetched very infrequently.
Ported from upstream BigBodyCobain/Shadowbroker v0.9.6.
"""

import logging
from datetime import datetime, timedelta, timezone

from services.network_utils import fetch_with_curl
from services.fetchers._store import latest_data, _data_lock, _mark_fresh
from services.fetchers.retry import with_retry

logger = logging.getLogger(__name__)

# Only include nodes seen in the last 7 days
_STALE_DAYS = 7


@with_retry(max_retries=1, base_delay=30)
def fetch_meshtastic():
    """Fetch Meshtastic node positions from community API."""
    resp = fetch_with_curl(
        "https://meshtastic.liamcottle.net/api/v1/nodes",
        timeout=60,  # large response
    )
    if not resp or resp.status_code != 200:
        logger.warning("Meshtastic: failed to fetch nodes")
        return

    try:
        data = resp.json()
    except ValueError:
        logger.warning("Meshtastic: invalid JSON response")
        return

    if not isinstance(data, list):
        # API might wrap in {"nodes": [...]}
        data = data.get("nodes", []) if isinstance(data, dict) else []

    cutoff = (datetime.now(timezone.utc) - timedelta(days=_STALE_DAYS)).isoformat()
    nodes = []

    for node in data:
        lat = node.get("latitude")
        lng = node.get("longitude")
        if lat is None or lng is None:
            continue
        try:
            lat, lng = float(lat), float(lng)
        except (ValueError, TypeError):
            continue

        # Skip obviously invalid coords
        if lat == 0 and lng == 0:
            continue
        if abs(lat) > 90 or abs(lng) > 180:
            continue

        last_seen = node.get("last_seen") or node.get("updated_at") or ""
        if last_seen and last_seen < cutoff:
            continue

        node_id = node.get("node_id") or node.get("id", "")
        nodes.append({
            "id": f"mesh-{node_id}",
            "node_id": str(node_id),
            "long_name": node.get("long_name", ""),
            "short_name": node.get("short_name", ""),
            "lat": lat,
            "lng": lng,
            "last_seen": last_seen,
            "hardware": node.get("hardware", ""),
            "_source": "meshtastic",
        })

    logger.info(f"Meshtastic: {len(nodes)} active nodes (from {len(data)} total)")

    with _data_lock:
        latest_data["meshtastic"] = nodes
    _mark_fresh("meshtastic")
