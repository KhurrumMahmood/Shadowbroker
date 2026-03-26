"""Cross-domain post-processing pipeline.

Runs after slow-tier fetchers complete. Reads from latest_data, computes
coverage gaps, cross-domain correlations, and machine assessments on news items.
"""
import logging
from services.utils.geo import haversine, grid_cluster

logger = logging.getLogger(__name__)

# Configurable thresholds
COVERAGE_GAP_CELL_DEGREES = 4.0
COVERAGE_GAP_MIN_GDELT = 3
CORRELATION_RADIUS_KM = 500
FIRE_CORRELATION_RADIUS_KM = 300
ASSESSMENT_RADIUS_KM = 300


def _normalize_gdelt(gdelt: list[dict]) -> list[dict]:
    """Flatten GeoJSON Features into dicts with lat/lon keys.

    GDELT data is stored as GeoJSON Features: {type, properties, geometry}.
    The pipeline functions need flat dicts with 'lat' and 'lon' fields.
    Items already in flat format (e.g. from tests) are passed through unchanged.
    """
    flat = []
    for item in gdelt:
        if item.get("type") == "Feature":
            coords = (item.get("geometry") or {}).get("coordinates")
            if not coords or len(coords) < 2:
                continue
            props = item.get("properties", {})
            flat.append({
                "lat": coords[1],  # GeoJSON is [lon, lat]
                "lon": coords[0],
                "action_geo": props.get("name", ""),
                "event_root_code": props.get("event_root_code", ""),
                "count": props.get("count", 1),
            })
        elif item.get("lat") is not None:
            flat.append(item)
    return flat


def compute_coverage_gaps(
    gdelt: list[dict], news: list[dict]
) -> list[dict]:
    """Find regions with GDELT conflict events but zero news coverage.

    Buckets both GDELT events and news articles into geographic grid cells,
    then identifies cells where GDELT events exist but news articles don't.
    """
    if not gdelt:
        return []

    gdelt_grid = grid_cluster(gdelt, COVERAGE_GAP_CELL_DEGREES)
    # News items store coords as [lat, lon] — flatten for grid_cluster
    news_flat = []
    for n in news:
        nlat, nlon = _news_coords(n)
        if nlat is not None:
            news_flat.append({"lat": nlat, "lon": nlon})
    news_grid = grid_cluster(news_flat, COVERAGE_GAP_CELL_DEGREES)

    gaps = []
    for cell, events in gdelt_grid.items():
        news_in_cell = news_grid.get(cell, [])
        if len(events) >= COVERAGE_GAP_MIN_GDELT and len(news_in_cell) == 0:
            gaps.append({
                "lat": cell[0],
                "lon": cell[1],
                "gdelt_count": len(events),
                "news_count": 0,
                "top_event_codes": _top_event_codes(events),
            })

    gaps.sort(key=lambda g: g["gdelt_count"], reverse=True)
    return gaps


def compute_cross_domain_correlations(
    gdelt: list[dict],
    military: list[dict],
    fires: list[dict],
    outages: list[dict],
) -> list[dict]:
    """Find spatial correlations between conflict zones and other domains.

    Clusters GDELT events into hotspots, then checks for military aircraft,
    fires, and internet outages within configurable radius.
    """
    if not gdelt:
        return []

    hotspots = grid_cluster(gdelt, 2.0)
    # Sort by event count, take top 10
    ranked = sorted(hotspots.items(), key=lambda x: len(x[1]), reverse=True)[:10]

    correlations = []

    for (hlat, hlon), events in ranked:
        geo_label = _geo_label(events)

        # Military near conflict
        for ac in military:
            alat, alon = _coords(ac, "lat", "lng")
            if alat is None:
                continue
            d = haversine(hlat, hlon, alat, alon)
            if d <= CORRELATION_RADIUS_KM:
                correlations.append({
                    "type": "military_near_conflict",
                    "conflict_location": geo_label,
                    "conflict_lat": hlat,
                    "conflict_lon": hlon,
                    "gdelt_count": len(events),
                    "entity": {
                        "flight": ac.get("callsign", "?"),
                        "type": ac.get("type", ac.get("military_type", "?")),
                        "operator": ac.get("country", "?"),
                    },
                    "distance_km": round(d, 1),
                })

        # Fires near conflict
        fire_grid = grid_cluster(fires, 3.0, lat_key="lat", lon_key="lng")
        for (flat, flon), fire_list in fire_grid.items():
            d = haversine(hlat, hlon, flat, flon)
            if d <= FIRE_CORRELATION_RADIUS_KM:
                correlations.append({
                    "type": "fires_near_conflict",
                    "conflict_location": geo_label,
                    "conflict_lat": hlat,
                    "conflict_lon": hlon,
                    "gdelt_count": len(events),
                    "fire_count": len(fire_list),
                    "distance_km": round(d, 1),
                })

        # Outages near conflict
        for outage in outages:
            olat, olon = _coords(outage, "lat", "lng")
            if olat is None:
                continue
            d = haversine(hlat, hlon, olat, olon)
            if d <= CORRELATION_RADIUS_KM:
                correlations.append({
                    "type": "outage_near_conflict",
                    "conflict_location": geo_label,
                    "conflict_lat": hlat,
                    "conflict_lon": hlon,
                    "gdelt_count": len(events),
                    "entity_name": outage.get("region_name", "?"),
                    "severity": outage.get("severity", 0),
                    "distance_km": round(d, 1),
                })

    correlations.sort(key=lambda c: c.get("distance_km", 9999))
    return correlations


def populate_machine_assessments(
    news: list[dict],
    gdelt: list[dict],
    fires: list[dict],
    outages: list[dict],
) -> None:
    """Enrich news items in-place with cross-domain correlation data.

    Fills the machine_assessment field with nearby GDELT events, fires, and outages.
    """
    gdelt_grid = grid_cluster(gdelt, 2.0) if gdelt else {}
    fire_grid = grid_cluster(fires, 3.0, lat_key="lat", lon_key="lng") if fires else {}

    for item in news:
        nlat_f, nlon_f = _news_coords(item)
        if nlat_f is None:
            continue

        gdelt_nearby = 0
        fires_nearby = 0
        outages_nearby = 0

        # Check GDELT hotspots
        for (glat, glon), events in gdelt_grid.items():
            if haversine(nlat_f, nlon_f, glat, glon) <= ASSESSMENT_RADIUS_KM:
                gdelt_nearby += len(events)

        # Check fire clusters
        for (flat, flon), fire_list in fire_grid.items():
            if haversine(nlat_f, nlon_f, flat, flon) <= ASSESSMENT_RADIUS_KM:
                fires_nearby += len(fire_list)

        # Check outages
        for outage in outages:
            olat, olon = _coords(outage, "lat", "lng")
            if olat is None:
                continue
            if haversine(nlat_f, nlon_f, olat, olon) <= ASSESSMENT_RADIUS_KM:
                outages_nearby += 1

        if gdelt_nearby > 0 or fires_nearby > 0 or outages_nearby > 0:
            item["machine_assessment"] = {
                "gdelt_nearby": gdelt_nearby,
                "fires_nearby": fires_nearby,
                "outages_nearby": outages_nearby,
            }


def post_process_slow_data(store: dict) -> None:
    """Main entry point — runs all post-processing on the shared data store.

    Called from data_fetcher.py after slow-tier fetchers complete.
    Reads from and writes to the store dict (latest_data).
    """
    gdelt = _normalize_gdelt(store.get("gdelt", []))
    news = store.get("news", [])
    military = store.get("military_flights", [])
    fires = store.get("firms_fires", [])
    outages = store.get("internet_outages", [])

    try:
        store["coverage_gaps"] = compute_coverage_gaps(gdelt, news)
        logger.info(f"Post-processing: {len(store['coverage_gaps'])} coverage gaps detected")
    except Exception:
        logger.exception("Coverage gap computation failed")
        store["coverage_gaps"] = []

    try:
        store["correlations"] = compute_cross_domain_correlations(
            gdelt, military, fires, outages
        )
        logger.info(f"Post-processing: {len(store['correlations'])} correlations found")
    except Exception:
        logger.exception("Correlation computation failed")
        store["correlations"] = []

    try:
        populate_machine_assessments(news, gdelt, fires, outages)
        assessed = sum(1 for n in news if n.get("machine_assessment") is not None)
        logger.info(f"Post-processing: {assessed}/{len(news)} news items assessed")
    except Exception:
        logger.exception("Machine assessment failed")


# --- Helpers ---

def _coords(entity: dict, lat_key: str, lon_key: str) -> tuple[float | None, float | None]:
    lat = entity.get(lat_key)
    lon = entity.get(lon_key)
    if lat is None or lon is None:
        return None, None
    try:
        return float(lat), float(lon)
    except (ValueError, TypeError):
        return None, None


def _news_coords(item: dict) -> tuple[float | None, float | None]:
    """Extract lat/lon from a news item.

    News items store coordinates as coords: [lat, lon] rather than
    separate lat/lon fields.
    """
    coords = item.get("coords")
    if coords and isinstance(coords, (list, tuple)) and len(coords) >= 2:
        try:
            return float(coords[0]), float(coords[1])
        except (ValueError, TypeError):
            return None, None
    # Fallback: some items may have flat lat/lon
    lat = item.get("lat")
    lon = item.get("lon") or item.get("lng")
    if lat is not None and lon is not None:
        try:
            return float(lat), float(lon)
        except (ValueError, TypeError):
            pass
    return None, None


def _geo_label(events: list[dict]) -> str:
    for e in events:
        geo = e.get("action_geo", "")
        if geo:
            return geo.split(",")[0]
    return "Unknown"


def _top_event_codes(events: list[dict], n: int = 3) -> list[str]:
    from collections import Counter
    codes = Counter(e.get("event_root_code", "?") for e in events)
    code_names = {"14": "PROTEST", "17": "COERCE", "18": "ASSAULT", "19": "FIGHT", "20": "MASS_VIOLENCE"}
    return [code_names.get(code, code) for code, _ in codes.most_common(n)]
