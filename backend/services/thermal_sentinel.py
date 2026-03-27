"""Thermal anomaly detection via Sentinel-2 SWIR bands + FIRMS corroboration.

On-demand analysis at a lat/lng point. Uses Microsoft Planetary Computer
STAC API (free, no key) to find recent Sentinel-2 scenes, then cross-references
with existing FIRMS fire data for confidence scoring.

If rasterio is available, performs actual SWIR band analysis for thermal index.
Without rasterio, provides STAC metadata + FIRMS corroboration only.

Ported from upstream BigBodyCobain/Shadowbroker v0.9.6.
"""

import logging
from datetime import datetime, timedelta, timezone
from math import radians, sin, cos, sqrt, atan2

from cachetools import TTLCache

logger = logging.getLogger(__name__)

# Cache by rounded lat/lng (0.05° grid ~= 5km), TTL 30 minutes
_thermal_cache = TTLCache(maxsize=100, ttl=1800)

# FIRMS corroboration radius in km
_FIRMS_RADIUS_KM = 25


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in km."""
    R = 6371
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def _get_firms_nearby(lat: float, lng: float, radius_km: float) -> list[dict]:
    """Find FIRMS fire hotspots near the target point from in-memory data."""
    from services.fetchers._store import latest_data, _data_lock

    with _data_lock:
        fires = list(latest_data.get("firms_fires", []))

    nearby = []
    for fire in fires:
        flat = fire.get("lat")
        flng = fire.get("lng")
        if flat is None or flng is None:
            continue
        dist = _haversine_km(lat, lng, flat, flng)
        if dist <= radius_km:
            nearby.append({
                "lat": flat,
                "lng": flng,
                "frp": fire.get("frp", 0),
                "confidence": fire.get("confidence", ""),
                "distance_km": round(dist, 1),
                "acq_date": fire.get("acq_date", ""),
            })

    nearby.sort(key=lambda x: x["distance_km"])
    return nearby[:20]


def _search_swir_scenes(lat: float, lng: float, days: int = 14) -> list[dict]:
    """Search Planetary Computer for Sentinel-2 scenes with SWIR bands."""
    try:
        from pystac_client import Client

        catalog = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)

        search = catalog.search(
            collections=["sentinel-2-l2a"],
            intersects={"type": "Point", "coordinates": [lng, lat]},
            datetime=f"{start.isoformat()}/{end.isoformat()}",
            sortby=[{"field": "datetime", "direction": "desc"}],
            max_items=5,
            query={"eo:cloud_cover": {"lt": 40}},
        )

        scenes = []
        for item in search.items():
            has_swir = "B12" in item.assets or "B11" in item.assets
            scenes.append({
                "scene_id": item.id,
                "datetime": item.datetime.isoformat() if item.datetime else None,
                "cloud_cover": item.properties.get("eo:cloud_cover"),
                "platform": item.properties.get("platform", "Sentinel-2"),
                "has_swir_bands": has_swir,
                "sun_elevation": item.properties.get("s2:mean_solar_zenith_angle"),
            })

        return scenes

    except ImportError:
        logger.debug("pystac-client not installed — SWIR scene search unavailable")
        return []
    except Exception as e:
        logger.warning(f"SWIR scene search failed for ({lat}, {lng}): {e}")
        return []


def _try_swir_analysis(lat: float, lng: float, scenes: list[dict]) -> dict | None:
    """Attempt SWIR band analysis with rasterio if available.

    Returns thermal index dict or None if rasterio unavailable.
    """
    try:
        import rasterio  # noqa: F401
        import planetary_computer
        from pystac_client import Client
    except ImportError:
        return None

    # Find scene with SWIR bands
    swir_scene_id = None
    for s in scenes:
        if s.get("has_swir_bands"):
            swir_scene_id = s["scene_id"]
            break

    if not swir_scene_id:
        return None

    try:
        catalog = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
        results = catalog.search(
            collections=["sentinel-2-l2a"],
            ids=[swir_scene_id],
        )
        items = list(results.items())
        if not items:
            return None

        item = planetary_computer.sign_item(items[0])

        b11_asset = item.assets.get("B11")
        b12_asset = item.assets.get("B12")
        if not b11_asset or not b12_asset:
            return None

        # Read a small window around the target point
        with rasterio.open(b12_asset.href) as src:
            row, col = src.index(lng, lat)
            window = rasterio.windows.Window(
                max(0, col - 5), max(0, row - 5), 10, 10
            )
            b12 = src.read(1, window=window).astype(float)

        with rasterio.open(b11_asset.href) as src:
            window = rasterio.windows.Window(
                max(0, col - 5), max(0, row - 5), 10, 10
            )
            b11 = src.read(1, window=window).astype(float)

        if b12.size == 0 or b11.size == 0:
            return None

        # Thermal index: (B12 - B11) / (B12 + B11 + 1e-10)
        thermal_idx = (b12 - b11) / (b12 + b11 + 1e-10)
        mean_ti = float(thermal_idx.mean())
        max_ti = float(thermal_idx.max())

        return {
            "thermal_index_mean": round(mean_ti, 4),
            "thermal_index_max": round(max_ti, 4),
            "scene_id": swir_scene_id,
            "method": "swir_band_analysis",
        }

    except Exception as e:
        logger.warning(f"SWIR analysis failed: {e}")
        return None


def analyze_thermal(lat: float, lng: float) -> dict:
    """Run thermal anomaly analysis at a point.

    Combines:
    1. Sentinel-2 SWIR scene availability
    2. Optional SWIR band analysis (if rasterio available)
    3. FIRMS fire hotspot corroboration
    4. Composite confidence score
    """
    cache_key = f"{round(lat, 2)}_{round(lng, 2)}"
    if cache_key in _thermal_cache:
        return _thermal_cache[cache_key]

    # 1. Search for SWIR scenes
    scenes = _search_swir_scenes(lat, lng)

    # 2. Try band analysis
    swir_result = _try_swir_analysis(lat, lng, scenes) if scenes else None

    # 3. FIRMS corroboration
    firms_nearby = _get_firms_nearby(lat, lng, _FIRMS_RADIUS_KM)

    # 4. Compute confidence score
    confidence = 0.0
    indicators = []

    # FIRMS corroboration (strongest signal)
    if firms_nearby:
        closest = firms_nearby[0]
        frp_max = max(f["frp"] for f in firms_nearby)
        firms_score = min(0.5, len(firms_nearby) * 0.1)
        if frp_max > 50:
            firms_score += 0.2
        if closest["distance_km"] < 5:
            firms_score += 0.1
        confidence += firms_score
        indicators.append(f"{len(firms_nearby)} FIRMS hotspots within {_FIRMS_RADIUS_KM}km "
                          f"(closest: {closest['distance_km']}km, max FRP: {frp_max})")

    # SWIR band analysis
    if swir_result:
        ti_max = swir_result["thermal_index_max"]
        if ti_max > 0.2:
            confidence += 0.3
            indicators.append(f"High SWIR thermal index: {ti_max}")
        elif ti_max > 0.1:
            confidence += 0.15
            indicators.append(f"Moderate SWIR thermal index: {ti_max}")

    # Scene availability bonus
    if scenes:
        swir_count = sum(1 for s in scenes if s.get("has_swir_bands"))
        if swir_count > 0:
            confidence += 0.05
            indicators.append(f"{swir_count} SWIR-capable scenes in last 14 days")

    confidence = min(1.0, confidence)

    # Determine severity
    if confidence >= 0.7:
        severity = "high"
    elif confidence >= 0.4:
        severity = "medium"
    elif confidence > 0:
        severity = "low"
    else:
        severity = "none"

    result = {
        "lat": lat,
        "lng": lng,
        "confidence": round(confidence, 2),
        "severity": severity,
        "indicators": indicators,
        "firms_hotspots": firms_nearby,
        "sentinel_scenes": scenes[:3],
        "swir_analysis": swir_result,
        "analysis_method": "swir_band_analysis" if swir_result else "firms_corroboration",
        "_source": "thermal_sentinel",
    }

    _thermal_cache[cache_key] = result
    return result
