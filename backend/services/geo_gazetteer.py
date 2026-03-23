"""Lightweight strategic location gazetteer for geographic entity search."""
import math

# ~200 named locations: maritime chokepoints, seas, conflict zones, major cities/regions
# Each entry: {lat, lng, radius_km}
STRATEGIC_LOCATIONS: dict[str, dict] = {
    # ── Maritime chokepoints ──
    "strait of hormuz": {"lat": 26.5, "lng": 56.3, "radius_km": 150},
    "strait of malacca": {"lat": 2.5, "lng": 101.0, "radius_km": 300},
    "suez canal": {"lat": 30.5, "lng": 32.3, "radius_km": 100},
    "bab el-mandeb": {"lat": 12.6, "lng": 43.3, "radius_km": 100},
    "bosphorus": {"lat": 41.1, "lng": 29.05, "radius_km": 50},
    "dardanelles": {"lat": 40.2, "lng": 26.4, "radius_km": 50},
    "turkish straits": {"lat": 40.7, "lng": 28.0, "radius_km": 150},
    "panama canal": {"lat": 9.1, "lng": -79.7, "radius_km": 80},
    "strait of gibraltar": {"lat": 35.96, "lng": -5.5, "radius_km": 80},
    "strait of taiwan": {"lat": 24.0, "lng": 119.5, "radius_km": 200},
    "taiwan strait": {"lat": 24.0, "lng": 119.5, "radius_km": 200},
    "strait of dover": {"lat": 51.0, "lng": 1.5, "radius_km": 60},
    "english channel": {"lat": 50.0, "lng": -1.0, "radius_km": 200},
    "strait of sicily": {"lat": 37.0, "lng": 11.5, "radius_km": 150},
    "mozambique channel": {"lat": -17.0, "lng": 41.0, "radius_km": 400},
    "denmark strait": {"lat": 66.0, "lng": -26.0, "radius_km": 200},
    "strait of korea": {"lat": 34.5, "lng": 129.5, "radius_km": 150},
    "tsushima strait": {"lat": 34.5, "lng": 129.5, "radius_km": 150},
    "lombok strait": {"lat": -8.5, "lng": 115.7, "radius_km": 100},
    "sunda strait": {"lat": -6.1, "lng": 105.8, "radius_km": 80},
    "cape of good hope": {"lat": -34.4, "lng": 18.5, "radius_km": 200},

    # ── Seas and oceans ──
    "black sea": {"lat": 43.0, "lng": 34.0, "radius_km": 600},
    "mediterranean": {"lat": 35.0, "lng": 18.0, "radius_km": 1500},
    "mediterranean sea": {"lat": 35.0, "lng": 18.0, "radius_km": 1500},
    "south china sea": {"lat": 12.0, "lng": 114.0, "radius_km": 1000},
    "east china sea": {"lat": 28.0, "lng": 125.0, "radius_km": 500},
    "persian gulf": {"lat": 26.0, "lng": 52.0, "radius_km": 500},
    "arabian gulf": {"lat": 26.0, "lng": 52.0, "radius_km": 500},
    "gulf of oman": {"lat": 24.5, "lng": 58.5, "radius_km": 300},
    "red sea": {"lat": 20.0, "lng": 38.5, "radius_km": 600},
    "sea of japan": {"lat": 40.0, "lng": 135.0, "radius_km": 500},
    "baltic sea": {"lat": 58.0, "lng": 20.0, "radius_km": 500},
    "north sea": {"lat": 56.0, "lng": 3.0, "radius_km": 500},
    "caspian sea": {"lat": 41.0, "lng": 51.0, "radius_km": 500},
    "sea of azov": {"lat": 46.0, "lng": 36.5, "radius_km": 200},
    "adriatic sea": {"lat": 43.0, "lng": 15.0, "radius_km": 300},
    "aegean sea": {"lat": 38.5, "lng": 25.0, "radius_km": 250},
    "gulf of mexico": {"lat": 25.0, "lng": -90.0, "radius_km": 800},
    "caribbean sea": {"lat": 15.0, "lng": -75.0, "radius_km": 1000},
    "arabian sea": {"lat": 15.0, "lng": 65.0, "radius_km": 800},
    "bay of bengal": {"lat": 14.0, "lng": 88.0, "radius_km": 700},
    "gulf of aden": {"lat": 12.0, "lng": 47.0, "radius_km": 300},
    "gulf of guinea": {"lat": 3.0, "lng": 2.0, "radius_km": 500},
    "barents sea": {"lat": 75.0, "lng": 38.0, "radius_km": 500},
    "norwegian sea": {"lat": 67.0, "lng": 3.0, "radius_km": 500},
    "indian ocean": {"lat": -10.0, "lng": 75.0, "radius_km": 2000},
    "pacific ocean": {"lat": 0.0, "lng": -150.0, "radius_km": 3000},
    "atlantic ocean": {"lat": 30.0, "lng": -40.0, "radius_km": 3000},
    "arctic ocean": {"lat": 85.0, "lng": 0.0, "radius_km": 1500},

    # ── Conflict zones / hotspots ──
    "ukraine": {"lat": 48.5, "lng": 31.5, "radius_km": 600},
    "crimea": {"lat": 45.0, "lng": 34.0, "radius_km": 200},
    "donbas": {"lat": 48.0, "lng": 38.0, "radius_km": 200},
    "gaza": {"lat": 31.4, "lng": 34.4, "radius_km": 50},
    "west bank": {"lat": 31.9, "lng": 35.2, "radius_km": 80},
    "israel": {"lat": 31.5, "lng": 34.8, "radius_km": 150},
    "lebanon": {"lat": 33.9, "lng": 35.8, "radius_km": 100},
    "syria": {"lat": 35.0, "lng": 38.0, "radius_km": 300},
    "iraq": {"lat": 33.0, "lng": 44.0, "radius_km": 400},
    "iran": {"lat": 32.5, "lng": 53.0, "radius_km": 600},
    "yemen": {"lat": 15.5, "lng": 48.0, "radius_km": 400},
    "somalia": {"lat": 5.0, "lng": 46.0, "radius_km": 500},
    "libya": {"lat": 27.0, "lng": 17.0, "radius_km": 500},
    "sudan": {"lat": 15.0, "lng": 30.0, "radius_km": 600},
    "ethiopia": {"lat": 9.0, "lng": 38.5, "radius_km": 500},
    "myanmar": {"lat": 19.5, "lng": 96.5, "radius_km": 400},
    "north korea": {"lat": 40.0, "lng": 127.0, "radius_km": 200},
    "south korea": {"lat": 36.0, "lng": 128.0, "radius_km": 200},
    "korean peninsula": {"lat": 38.0, "lng": 127.5, "radius_km": 350},
    "taiwan": {"lat": 23.7, "lng": 121.0, "radius_km": 200},
    "kashmir": {"lat": 34.5, "lng": 76.0, "radius_km": 200},
    "sahel": {"lat": 15.0, "lng": 0.0, "radius_km": 1500},
    "horn of africa": {"lat": 8.0, "lng": 45.0, "radius_km": 500},
    "afghanistan": {"lat": 33.5, "lng": 66.0, "radius_km": 400},
    "nagorno-karabakh": {"lat": 39.8, "lng": 46.8, "radius_km": 100},

    # ── Major cities / capitals ──
    "london": {"lat": 51.5, "lng": -0.12, "radius_km": 80},
    "paris": {"lat": 48.86, "lng": 2.35, "radius_km": 60},
    "berlin": {"lat": 52.52, "lng": 13.4, "radius_km": 60},
    "moscow": {"lat": 55.75, "lng": 37.62, "radius_km": 80},
    "washington": {"lat": 38.9, "lng": -77.04, "radius_km": 80},
    "washington dc": {"lat": 38.9, "lng": -77.04, "radius_km": 80},
    "new york": {"lat": 40.71, "lng": -74.0, "radius_km": 80},
    "beijing": {"lat": 39.9, "lng": 116.4, "radius_km": 80},
    "tokyo": {"lat": 35.68, "lng": 139.69, "radius_km": 80},
    "kyiv": {"lat": 50.45, "lng": 30.52, "radius_km": 80},
    "kiev": {"lat": 50.45, "lng": 30.52, "radius_km": 80},
    "tel aviv": {"lat": 32.08, "lng": 34.78, "radius_km": 50},
    "tehran": {"lat": 35.69, "lng": 51.39, "radius_km": 80},
    "riyadh": {"lat": 24.71, "lng": 46.68, "radius_km": 80},
    "ankara": {"lat": 39.93, "lng": 32.86, "radius_km": 60},
    "istanbul": {"lat": 41.01, "lng": 28.98, "radius_km": 60},
    "cairo": {"lat": 30.04, "lng": 31.24, "radius_km": 60},
    "dubai": {"lat": 25.2, "lng": 55.27, "radius_km": 60},
    "singapore": {"lat": 1.35, "lng": 103.82, "radius_km": 50},
    "shanghai": {"lat": 31.23, "lng": 121.47, "radius_km": 80},
    "taipei": {"lat": 25.03, "lng": 121.57, "radius_km": 50},
    "seoul": {"lat": 37.57, "lng": 126.98, "radius_km": 60},
    "pyongyang": {"lat": 39.04, "lng": 125.76, "radius_km": 60},
    "mumbai": {"lat": 19.08, "lng": 72.88, "radius_km": 60},
    "delhi": {"lat": 28.61, "lng": 77.21, "radius_km": 60},
    "new delhi": {"lat": 28.61, "lng": 77.21, "radius_km": 60},
    "rome": {"lat": 41.9, "lng": 12.5, "radius_km": 50},
    "brussels": {"lat": 50.85, "lng": 4.35, "radius_km": 40},
    "warsaw": {"lat": 52.23, "lng": 21.01, "radius_km": 60},
    "bucharest": {"lat": 44.43, "lng": 26.1, "radius_km": 60},
    "sydney": {"lat": -33.87, "lng": 151.21, "radius_km": 80},
    "los angeles": {"lat": 34.05, "lng": -118.24, "radius_km": 80},
    "san francisco": {"lat": 37.77, "lng": -122.42, "radius_km": 60},
    "beijing": {"lat": 39.9, "lng": 116.4, "radius_km": 80},
    "hong kong": {"lat": 22.32, "lng": 114.17, "radius_km": 50},
    "sao paulo": {"lat": -23.55, "lng": -46.63, "radius_km": 80},
    "johannesburg": {"lat": -26.2, "lng": 28.04, "radius_km": 60},
    "nairobi": {"lat": -1.29, "lng": 36.82, "radius_km": 60},
    "addis ababa": {"lat": 9.02, "lng": 38.75, "radius_km": 60},
    "lagos": {"lat": 6.52, "lng": 3.38, "radius_km": 60},
    "kabul": {"lat": 34.53, "lng": 69.17, "radius_km": 60},
    "baghdad": {"lat": 33.31, "lng": 44.37, "radius_km": 60},
    "damascus": {"lat": 33.51, "lng": 36.29, "radius_km": 50},
    "minsk": {"lat": 53.9, "lng": 27.57, "radius_km": 60},
    "tbilisi": {"lat": 41.69, "lng": 44.8, "radius_km": 50},
    "baku": {"lat": 40.41, "lng": 49.87, "radius_km": 50},
    "kaliningrad": {"lat": 54.71, "lng": 20.51, "radius_km": 80},
    "sevastopol": {"lat": 44.62, "lng": 33.52, "radius_km": 50},
    "odesa": {"lat": 46.48, "lng": 30.73, "radius_km": 60},
    "odessa": {"lat": 46.48, "lng": 30.73, "radius_km": 60},
    "kharkiv": {"lat": 49.99, "lng": 36.23, "radius_km": 60},
    "mariupol": {"lat": 47.1, "lng": 37.55, "radius_km": 40},

    # ── Strategic military areas ──
    "guam": {"lat": 13.44, "lng": 144.79, "radius_km": 100},
    "diego garcia": {"lat": -7.32, "lng": 72.42, "radius_km": 100},
    "okinawa": {"lat": 26.5, "lng": 127.8, "radius_km": 100},
    "pearl harbor": {"lat": 21.35, "lng": -157.95, "radius_km": 50},
    "norfolk": {"lat": 36.85, "lng": -76.3, "radius_km": 80},
    "san diego": {"lat": 32.72, "lng": -117.16, "radius_km": 80},
    "ramstein": {"lat": 49.44, "lng": 7.6, "radius_km": 40},
    "incirlik": {"lat": 37.0, "lng": 35.43, "radius_km": 40},
    "al udeid": {"lat": 25.12, "lng": 51.32, "radius_km": 40},
    "camp lemonnier": {"lat": 11.55, "lng": 43.15, "radius_km": 40},
    "yokosuka": {"lat": 35.28, "lng": 139.67, "radius_km": 40},
    "vladivostok": {"lat": 43.12, "lng": 131.89, "radius_km": 60},
    "murmansk": {"lat": 68.97, "lng": 33.07, "radius_km": 80},
    "tartus": {"lat": 34.89, "lng": 35.87, "radius_km": 40},
    "hmeimim": {"lat": 35.41, "lng": 35.95, "radius_km": 30},
    "djibouti": {"lat": 11.55, "lng": 43.15, "radius_km": 60},

    # ── Regions ──
    "europe": {"lat": 50.0, "lng": 10.0, "radius_km": 2500},
    "middle east": {"lat": 29.0, "lng": 42.0, "radius_km": 1500},
    "east asia": {"lat": 35.0, "lng": 120.0, "radius_km": 2000},
    "southeast asia": {"lat": 5.0, "lng": 110.0, "radius_km": 1500},
    "south asia": {"lat": 22.0, "lng": 78.0, "radius_km": 1500},
    "central asia": {"lat": 42.0, "lng": 65.0, "radius_km": 1000},
    "north africa": {"lat": 28.0, "lng": 10.0, "radius_km": 1500},
    "sub-saharan africa": {"lat": -5.0, "lng": 25.0, "radius_km": 3000},
    "west africa": {"lat": 10.0, "lng": -5.0, "radius_km": 1500},
    "east africa": {"lat": 0.0, "lng": 38.0, "radius_km": 1000},
    "north america": {"lat": 45.0, "lng": -100.0, "radius_km": 3000},
    "south america": {"lat": -15.0, "lng": -60.0, "radius_km": 3000},
    "central america": {"lat": 14.0, "lng": -87.0, "radius_km": 800},
    "oceania": {"lat": -20.0, "lng": 150.0, "radius_km": 2000},
    "scandinavia": {"lat": 63.0, "lng": 15.0, "radius_km": 800},
    "balkans": {"lat": 43.0, "lng": 21.0, "radius_km": 400},
    "caucasus": {"lat": 42.0, "lng": 44.0, "radius_km": 300},
    "arctic": {"lat": 80.0, "lng": 0.0, "radius_km": 2000},
    "antarctica": {"lat": -80.0, "lng": 0.0, "radius_km": 2000},
    "polynesia": {"lat": -15.0, "lng": -150.0, "radius_km": 2000},
}


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two points in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def find_location(query: str) -> dict | None:
    """Find a strategic location matching the query string.

    Tries exact match first, then substring match on location names.
    Returns {name, lat, lng, radius_km} or None.
    """
    q = query.lower().strip()
    if not q:
        return None

    # Exact match
    if q in STRATEGIC_LOCATIONS:
        return {"name": q.title(), **STRATEGIC_LOCATIONS[q]}

    # Substring: query is contained in a location name, or location name is contained in query
    best = None
    best_len = 0
    for name, loc in STRATEGIC_LOCATIONS.items():
        if name in q or q in name:
            # Prefer longer matches (more specific)
            if len(name) > best_len:
                best = {"name": name.title(), **loc}
                best_len = len(name)

    return best


def entities_in_radius(
    entities: list[dict],
    lat: float,
    lng: float,
    radius_km: float,
) -> list[dict]:
    """Filter entities to those within radius_km of (lat, lng)."""
    result = []
    for e in entities:
        elat = e.get("lat")
        elng = e.get("lng")
        if elat is None or elng is None:
            continue
        try:
            if _haversine_km(lat, lng, float(elat), float(elng)) <= radius_km:
                result.append(e)
        except (TypeError, ValueError):
            continue
    return result
