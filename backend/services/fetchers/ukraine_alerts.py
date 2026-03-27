"""Ukraine air raid alerts via alerts.in.ua API.

Polls active alerts, maps to oblast centroids for map rendering.
Requires ALERTS_IN_UA_TOKEN env var (free registration at alerts.in.ua).
Gracefully skips if token is not set.

Ported from upstream BigBodyCobain/Shadowbroker v0.9.6.
"""

import logging
import os

from services.network_utils import fetch_with_curl
from services.fetchers._store import latest_data, _data_lock, _mark_fresh
from services.fetchers.retry import with_retry

logger = logging.getLogger(__name__)

# Alert type → color mapping
ALERT_COLORS = {
    "air_raid": "#ef4444",            # red
    "artillery_shelling": "#f97316",  # orange
    "urban_fights": "#eab308",        # yellow
    "chemical": "#a855f7",            # purple
    "nuclear": "#dc2626",             # dark red
}

# Oblast centroid coordinates (approximate centers for map rendering)
_OBLAST_CENTROIDS: dict[str, dict] = {
    "Вінницька область": {"lat": 49.23, "lng": 28.47, "name_en": "Vinnytsia"},
    "Волинська область": {"lat": 50.75, "lng": 25.33, "name_en": "Volyn"},
    "Дніпропетровська область": {"lat": 48.46, "lng": 35.04, "name_en": "Dnipropetrovsk"},
    "Донецька область": {"lat": 48.00, "lng": 37.80, "name_en": "Donetsk"},
    "Житомирська область": {"lat": 50.45, "lng": 28.66, "name_en": "Zhytomyr"},
    "Закарпатська область": {"lat": 48.62, "lng": 22.29, "name_en": "Zakarpattia"},
    "Запорізька область": {"lat": 47.84, "lng": 35.14, "name_en": "Zaporizhzhia"},
    "Івано-Франківська область": {"lat": 48.92, "lng": 24.71, "name_en": "Ivano-Frankivsk"},
    "Київська область": {"lat": 50.05, "lng": 30.82, "name_en": "Kyiv Oblast"},
    "Кіровоградська область": {"lat": 48.51, "lng": 32.26, "name_en": "Kirovohrad"},
    "Луганська область": {"lat": 48.93, "lng": 39.31, "name_en": "Luhansk"},
    "Львівська область": {"lat": 49.84, "lng": 24.03, "name_en": "Lviv"},
    "Миколаївська область": {"lat": 47.62, "lng": 32.00, "name_en": "Mykolaiv"},
    "Одеська область": {"lat": 46.48, "lng": 30.73, "name_en": "Odesa"},
    "Полтавська область": {"lat": 49.59, "lng": 34.55, "name_en": "Poltava"},
    "Рівненська область": {"lat": 50.62, "lng": 26.25, "name_en": "Rivne"},
    "Сумська область": {"lat": 50.91, "lng": 34.80, "name_en": "Sumy"},
    "Тернопільська область": {"lat": 49.55, "lng": 25.59, "name_en": "Ternopil"},
    "Харківська область": {"lat": 49.99, "lng": 36.23, "name_en": "Kharkiv"},
    "Херсонська область": {"lat": 46.63, "lng": 33.48, "name_en": "Kherson"},
    "Хмельницька область": {"lat": 49.42, "lng": 26.98, "name_en": "Khmelnytskyi"},
    "Черкаська область": {"lat": 49.44, "lng": 32.06, "name_en": "Cherkasy"},
    "Чернівецька область": {"lat": 48.29, "lng": 25.94, "name_en": "Chernivtsi"},
    "Чернігівська область": {"lat": 51.49, "lng": 31.29, "name_en": "Chernihiv"},
    "м. Київ": {"lat": 50.45, "lng": 30.52, "name_en": "Kyiv City"},
    "Автономна Республіка Крим": {"lat": 44.95, "lng": 34.10, "name_en": "Crimea"},
    "м. Севастополь": {"lat": 44.62, "lng": 33.52, "name_en": "Sevastopol"},
}


def _find_oblast_centroid(location_title: str):
    """Find centroid coordinates for an oblast by Ukrainian name."""
    info = _OBLAST_CENTROIDS.get(location_title)
    if info:
        return info
    # Fuzzy: partial match
    for key, val in _OBLAST_CENTROIDS.items():
        if location_title in key or key in location_title:
            return val
    return None


@with_retry(max_retries=1, base_delay=2)
def fetch_ukraine_alerts():
    """Fetch active Ukraine air raid alerts from alerts.in.ua."""
    token = os.environ.get("ALERTS_IN_UA_TOKEN", "")
    if not token:
        logger.debug("ALERTS_IN_UA_TOKEN not set, skipping Ukraine alerts")
        return

    url = "https://api.alerts.in.ua/v1/alerts/active.json"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    response = fetch_with_curl(url, timeout=10, headers=headers)

    if not response:
        logger.warning("alerts.in.ua: no response (timeout or network error)")
        return
    if response.status_code == 401:
        logger.warning("alerts.in.ua returned 401 — check ALERTS_IN_UA_TOKEN")
        return
    if response.status_code == 429:
        logger.warning("alerts.in.ua rate-limited (429)")
        return
    if response.status_code != 200:
        logger.warning(f"alerts.in.ua returned HTTP {response.status_code}")
        return

    data = response.json()
    raw_alerts = data.get("alerts", [])
    alerts_out = []

    for alert in raw_alerts:
        if alert.get("location_type", "") != "oblast":
            continue

        location_title = alert.get("location_title", "")
        alert_type = alert.get("alert_type", "air_raid")
        centroid = _find_oblast_centroid(location_title)

        if not centroid:
            logger.debug(f"No centroid for oblast: {location_title}")
            continue

        alerts_out.append({
            "id": alert.get("id", 0),
            "alert_type": alert_type,
            "location_title": location_title,
            "location_uid": alert.get("location_uid", ""),
            "name_en": centroid["name_en"],
            "lat": centroid["lat"],
            "lng": centroid["lng"],
            "started_at": alert.get("started_at", ""),
            "color": ALERT_COLORS.get(alert_type, "#ef4444"),
            "_source": "ukraine_alerts",
        })

    logger.info(f"Ukraine alerts: {len(alerts_out)} active oblast-level alerts "
                f"(from {len(raw_alerts)} total)")

    with _data_lock:
        latest_data["ukraine_alerts"] = alerts_out
    _mark_fresh("ukraine_alerts")
