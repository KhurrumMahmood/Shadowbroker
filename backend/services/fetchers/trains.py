"""Train tracking via Amtrak (amtraker.com) + Finnish DigiTraffic.

Both APIs are free, no authentication required.
Ported from upstream BigBodyCobain/Shadowbroker v0.9.6.
"""

import logging

from services.network_utils import fetch_with_curl
from services.fetchers._store import latest_data, _data_lock, _mark_fresh
from services.fetchers.retry import with_retry

logger = logging.getLogger(__name__)


def _fetch_amtrak() -> list[dict]:
    """Fetch Amtrak train positions from amtraker.com API."""
    trains = []
    try:
        resp = fetch_with_curl("https://api.amtraker.com/v2/trains", timeout=15)
        if not resp or resp.status_code != 200:
            return []

        data = resp.json()
        # API returns {trainNum: [trainData, ...], ...}
        for train_num, train_list in data.items():
            if not isinstance(train_list, list):
                continue
            for t in train_list:
                lat = t.get("lat")
                lon = t.get("lon")
                if lat is None or lon is None:
                    continue
                try:
                    lat, lon = float(lat), float(lon)
                except (ValueError, TypeError):
                    continue

                trains.append({
                    "id": f"amtrak-{t.get('trainNum', train_num)}-{t.get('objectID', '')}",
                    "name": t.get("routeName", f"Amtrak {train_num}"),
                    "train_num": str(t.get("trainNum", train_num)),
                    "operator": "Amtrak",
                    "country": "US",
                    "lat": lat,
                    "lng": lon,
                    "speed": t.get("velocity"),
                    "heading": t.get("heading"),
                    "status": t.get("trainState", ""),
                    "origin": t.get("origName", ""),
                    "destination": t.get("destName", ""),
                    "stations_left": t.get("stationsLeft"),
                    "_source": "trains",
                })
    except Exception as e:
        logger.warning(f"Trains: Amtrak fetch failed: {e}")

    return trains


def _fetch_digitraffic() -> list[dict]:
    """Fetch Finnish train positions from DigiTraffic open API."""
    trains = []
    try:
        resp = fetch_with_curl(
            "https://rata.digitraffic.fi/api/v1/train-locations/latest",
            timeout=15,
        )
        if not resp or resp.status_code != 200:
            return []

        data = resp.json()
        for t in data:
            loc = t.get("location")
            if not loc:
                continue
            coords = loc.get("coordinates", [])
            if len(coords) < 2:
                continue

            lng, lat = coords[0], coords[1]
            trains.append({
                "id": f"fi-{t.get('trainNumber', '')}",
                "name": f"FI Train {t.get('trainNumber', '')}",
                "train_num": str(t.get("trainNumber", "")),
                "operator": "Finnish Railways",
                "country": "FI",
                "lat": lat,
                "lng": lng,
                "speed": t.get("speed"),
                "heading": t.get("bearing"),
                "status": "",
                "origin": "",
                "destination": "",
                "stations_left": None,
                "_source": "trains",
            })
    except Exception as e:
        logger.warning(f"Trains: DigiTraffic fetch failed: {e}")

    return trains


@with_retry(max_retries=1, base_delay=5)
def fetch_trains():
    """Fetch train positions from all sources and merge."""
    amtrak = _fetch_amtrak()
    digi = _fetch_digitraffic()

    all_trains = amtrak + digi
    logger.info(f"Trains: {len(amtrak)} Amtrak + {len(digi)} Finnish = {len(all_trains)} total")

    with _data_lock:
        latest_data["trains"] = all_trains
    _mark_fresh("trains")
