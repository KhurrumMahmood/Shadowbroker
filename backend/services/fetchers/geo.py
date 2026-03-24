"""Ship and geopolitics fetchers — AIS vessels, carriers, frontlines, GDELT, LiveUAmap."""
import csv
import io
import math
import logging
from services.network_utils import fetch_with_curl
from services.fetchers._store import latest_data, _data_lock, _mark_fresh
from services.fetchers.retry import with_retry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Ships (AIS + Carriers)
# ---------------------------------------------------------------------------
@with_retry(max_retries=1, base_delay=1)
def fetch_ships():
    """Fetch real-time AIS vessel data and combine with OSINT carrier positions."""
    from services.ais_stream import get_ais_vessels
    from services.carrier_tracker import get_carrier_positions

    ships = []
    try:
        carriers = get_carrier_positions()
        ships.extend(carriers)
    except Exception as e:
        logger.error(f"Carrier tracker error (non-fatal): {e}")
        carriers = []

    try:
        ais_vessels = get_ais_vessels()
        ships.extend(ais_vessels)
    except Exception as e:
        logger.error(f"AIS stream error (non-fatal): {e}")
        ais_vessels = []

    # Enrich ships with yacht alert data (tracked superyachts)
    from services.fetchers.yacht_alert import enrich_with_yacht_alert
    for ship in ships:
        enrich_with_yacht_alert(ship)

    # Enrich ships with PLAN/CCG vessel data
    from services.fetchers.plan_vessel_alert import enrich_with_plan_vessel
    for ship in ships:
        enrich_with_plan_vessel(ship)

    logger.info(f"Ships: {len(carriers)} carriers + {len(ais_vessels)} AIS vessels")
    with _data_lock:
        latest_data['ships'] = ships
    _mark_fresh("ships")


# ---------------------------------------------------------------------------
# Airports (ourairports.com)
# ---------------------------------------------------------------------------
cached_airports = []
# IATA code → { country_code, country_name, region_code } for flight enrichment
airport_country_lookup: dict[str, dict] = {}


def find_nearest_airport(lat, lng, max_distance_nm=200):
    """Find the nearest large airport to a given lat/lng using haversine distance."""
    if not cached_airports:
        return None

    best = None
    best_dist = float('inf')
    lat_r = math.radians(lat)
    lng_r = math.radians(lng)

    for apt in cached_airports:
        apt_lat_r = math.radians(apt['lat'])
        apt_lng_r = math.radians(apt['lng'])
        dlat = apt_lat_r - lat_r
        dlng = apt_lng_r - lng_r
        a = math.sin(dlat / 2) ** 2 + math.cos(lat_r) * math.cos(apt_lat_r) * math.sin(dlng / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        dist_nm = 3440.065 * c

        if dist_nm < best_dist:
            best_dist = dist_nm
            best = apt

    if best and best_dist <= max_distance_nm:
        return {
            "iata": best['iata'], "name": best['name'],
            "lat": best['lat'], "lng": best['lng'],
            "distance_nm": round(best_dist, 1)
        }
    return None


def _fetch_country_names() -> dict[str, str]:
    """Download OurAirports countries.csv → {iso_code: country_name}."""
    try:
        resp = fetch_with_curl("https://ourairports.com/data/countries.csv", timeout=10)
        if resp.status_code == 200:
            reader = csv.DictReader(io.StringIO(resp.text))
            return {row["code"]: row["name"] for row in reader if row.get("code")}
    except Exception as e:
        logger.warning(f"Could not fetch countries.csv: {e}")
    return {}


def fetch_airports():
    global cached_airports, airport_country_lookup
    if not cached_airports:
        logger.info("Downloading global airports database from ourairports.com...")
        country_names = _fetch_country_names()
        try:
            url = "https://ourairports.com/data/airports.csv"
            response = fetch_with_curl(url, timeout=15)
            if response.status_code == 200:
                f = io.StringIO(response.text)
                reader = csv.DictReader(f)
                for row in reader:
                    if row['type'] == 'large_airport' and row['iata_code']:
                        iso_country = row.get('iso_country', '')
                        iso_region = row.get('iso_region', '')
                        cached_airports.append({
                            "id": row['ident'],
                            "name": row['name'],
                            "iata": row['iata_code'],
                            "lat": float(row['latitude_deg']),
                            "lng": float(row['longitude_deg']),
                            "iso_country": iso_country,
                            "iso_region": iso_region,
                            "type": "airport"
                        })
                        airport_country_lookup[row['iata_code']] = {
                            "country_code": iso_country,
                            "country_name": country_names.get(iso_country, iso_country),
                            "region_code": iso_region,
                        }
                logger.info(f"Loaded {len(cached_airports)} large airports with country data.")
        except Exception as e:
            logger.error(f"Error fetching airports: {e}")

    with _data_lock:
        latest_data['airports'] = cached_airports


# ---------------------------------------------------------------------------
# Geopolitics & LiveUAMap
# ---------------------------------------------------------------------------
@with_retry(max_retries=1, base_delay=2)
def fetch_frontlines():
    """Fetch Ukraine frontline data (fast — single GitHub API call)."""
    try:
        from services.geopolitics import fetch_ukraine_frontlines
        frontlines = fetch_ukraine_frontlines()
        if frontlines:
            with _data_lock:
                latest_data['frontlines'] = frontlines
            _mark_fresh("frontlines")
    except Exception as e:
        logger.error(f"Error fetching frontlines: {e}")


@with_retry(max_retries=1, base_delay=3)
def fetch_gdelt():
    """Fetch GDELT global military incidents (slow — downloads 32 ZIP files)."""
    try:
        from services.geopolitics import fetch_global_military_incidents
        gdelt = fetch_global_military_incidents()
        if gdelt is not None:
            with _data_lock:
                latest_data['gdelt'] = gdelt
            _mark_fresh("gdelt")
    except Exception as e:
        logger.error(f"Error fetching GDELT: {e}")


def fetch_geopolitics():
    """Legacy wrapper — runs both sequentially. Used by recurring scheduler."""
    fetch_frontlines()
    fetch_gdelt()


def update_liveuamap():
    logger.info("Running scheduled Liveuamap scraper...")
    try:
        from services.liveuamap_scraper import fetch_liveuamap
        res = fetch_liveuamap()
        if res:
            with _data_lock:
                latest_data['liveuamap'] = res
            _mark_fresh("liveuamap")
    except Exception as e:
        logger.error(f"Liveuamap scraper error: {e}")
