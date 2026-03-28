"""Proactive alert checkers — pure functions that detect patterns in live data.

Each checker: (DataSource) -> list[Alert]
No LLM calls — pure Python pattern matching on entity data.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from services.agent.alerts import Alert, AlertSeverity
from services.agent.datasource import DataSource, _haversine_km

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared geo helpers
# ---------------------------------------------------------------------------

def _has_position(entity: dict) -> bool:
    """True when the entity has a usable lat/lng pair."""
    return entity.get("lat") is not None and entity.get("lng") is not None


def _count_nearby(
    origin: dict,
    items: list[dict],
    radius_km: float,
) -> int:
    """Count items within *radius_km* of *origin* (both must have lat/lng)."""
    lat, lng = origin["lat"], origin["lng"]
    return sum(
        1 for item in items
        if _has_position(item)
        and _haversine_km(lat, lng, item["lat"], item["lng"]) < radius_km
    )


def _find_nearby(
    origin: dict,
    items: list[dict],
    radius_km: float,
) -> list[dict]:
    """Return items within *radius_km* of *origin*."""
    lat, lng = origin["lat"], origin["lng"]
    return [
        item for item in items
        if _has_position(item)
        and _haversine_km(lat, lng, item["lat"], item["lng"]) < radius_km
    ]


def _centroid(items: list[dict]) -> tuple[float, float]:
    """Average lat/lng of positioned items. Returns (0, 0) when none qualify."""
    positioned = [item for item in items if _has_position(item)]
    if not positioned:
        return 0.0, 0.0
    lat = sum(item["lat"] for item in positioned) / len(positioned)
    lng = sum(item["lng"] for item in positioned) / len(positioned)
    return lat, lng


# ---------------------------------------------------------------------------
# Static reference data
# ---------------------------------------------------------------------------
from services.chokepoints import CHOKEPOINTS as _CHOKEPOINTS

_SANCTIONED_ZONES = [
    {"name": "Iran", "lat": 27.0, "lng": 56.0, "radius_km": 300},
    {"name": "North Korea", "lat": 39.0, "lng": 126.0, "radius_km": 200},
    {"name": "Syria", "lat": 35.0, "lng": 38.0, "radius_km": 250},
    {"name": "Venezuela", "lat": 10.5, "lng": -66.9, "radius_km": 300},
]

_AIRLIFT_MODELS = {"C-17", "C-17A", "C-5", "C-5M", "C-130J", "C-130",
                    "C-17A Globemaster III", "C-5M Super Galaxy",
                    "C-130J Super Hercules"}

_AIRLIFT_CALLSIGN_PREFIXES = ("RCH", "REACH")

_AIRLIFT_MODEL_PREFIXES = ("C-17", "C-5", "C-130")

_AIRLIFT_SURGE_THRESHOLD = 5  # 5+ strategic airlift = anomalous

_SUSPICIOUS_DESTINATIONS = {"", "FOR ORDERS", "FOR ORDER", "ORDERS", "TBN", "TBA"}


# ---------------------------------------------------------------------------
# 1. Military Convergence
# ---------------------------------------------------------------------------
def check_military_convergence(ds: DataSource) -> list[Alert]:
    """Alert when 2+ countries' military flights are within 200km of each other."""
    flights = ds.query("military_flights", limit=500)
    if len(flights) < 2:
        return []

    by_country: dict[str, list[dict]] = {}
    for f in flights:
        by_country.setdefault(f.get("country", "Unknown"), []).append(f)

    countries = list(by_country.keys())
    if len(countries) < 2:
        return []

    convergence_zones: list[dict] = []
    seen_pairs: set[tuple[str, str]] = set()

    for i, c1 in enumerate(countries):
        for c2 in countries[i + 1:]:
            pair = tuple(sorted([c1, c2]))
            if pair in seen_pairs:
                continue
            for f1 in by_country[c1]:
                if not _has_position(f1):
                    continue
                for f2 in by_country[c2]:
                    if not _has_position(f2):
                        continue
                    dist = _haversine_km(f1["lat"], f1["lng"], f2["lat"], f2["lng"])
                    if dist < 200:
                        seen_pairs.add(pair)
                        convergence_zones.append({
                            "countries": list(pair),
                            "lat": (f1["lat"] + f2["lat"]) / 2,
                            "lng": (f1["lng"] + f2["lng"]) / 2,
                            "distance_km": round(dist, 1),
                        })
                        break
                if pair in seen_pairs:
                    break

    if not convergence_zones:
        return []

    all_countries: set[str] = set()
    center_lat, center_lng = 0.0, 0.0
    for z in convergence_zones:
        all_countries.update(z["countries"])
        center_lat += z["lat"]
        center_lng += z["lng"]
    center_lat /= len(convergence_zones)
    center_lng /= len(convergence_zones)

    severity = AlertSeverity.CRITICAL if len(all_countries) >= 3 else AlertSeverity.ELEVATED

    return [Alert(
        alert_type="military_convergence",
        severity=severity,
        title=f"Military Convergence — {len(all_countries)} nations",
        description=(
            f"Military flights from {', '.join(sorted(all_countries))} "
            f"detected within 200km of each other."
        ),
        lat=round(center_lat, 2),
        lng=round(center_lng, 2),
        data={"countries": sorted(all_countries), "country_count": len(all_countries),
              "zones": convergence_zones},
    )]


# ---------------------------------------------------------------------------
# 2. Chokepoint Disruption
# ---------------------------------------------------------------------------
def check_chokepoint_disruption(ds: DataSource) -> list[Alert]:
    """Alert when GPS jamming is detected at a major chokepoint."""
    jamming = ds.query("gps_jamming", limit=200)
    if not jamming:
        return []

    alerts: list[Alert] = []
    for cp in _CHOKEPOINTS:
        for j in jamming:
            if not _has_position(j):
                continue
            dist = _haversine_km(cp["lat"], cp["lng"], j["lat"], j["lng"])
            if dist < cp["radius_km"]:
                sev_str = j.get("severity", "").lower()
                severity = AlertSeverity.CRITICAL if sev_str == "high" else AlertSeverity.ELEVATED
                alerts.append(Alert(
                    alert_type="chokepoint_disruption",
                    severity=severity,
                    title=f"GPS Jamming — {cp['name']}",
                    description=(
                        f"GPS jamming ({sev_str}) detected within "
                        f"{round(dist)}km of {cp['name']}."
                    ),
                    lat=j["lat"],
                    lng=j["lng"],
                    data={"chokepoint": cp["name"], "jamming_severity": sev_str,
                          "distance_km": round(dist, 1)},
                ))
                break  # One alert per chokepoint

    return alerts


# ---------------------------------------------------------------------------
# 3. Infrastructure Cascade
# ---------------------------------------------------------------------------
def check_infrastructure_cascade(ds: DataSource) -> list[Alert]:
    """Alert when earthquake + fire + outage are co-located (within 200km)."""
    earthquakes = ds.query("earthquakes", limit=200)
    fires = ds.query("firms_fires", limit=500)
    outages = ds.query("internet_outages", limit=200)

    if not earthquakes or (not fires and not outages):
        return []

    alerts: list[Alert] = []
    radius = 200  # km

    for eq in earthquakes:
        if not _has_position(eq):
            continue
        mag = eq.get("mag", 0)
        if mag < 4.5:
            continue

        nearby_fires = _count_nearby(eq, fires, radius)
        nearby_outages = len(_find_nearby(eq, outages, radius))
        place = eq.get("place", "Unknown")

        if nearby_fires > 0 and nearby_outages > 0:
            alerts.append(Alert(
                alert_type="infrastructure_cascade",
                severity=AlertSeverity.CRITICAL,
                title=f"Infrastructure Cascade — M{mag} {place}",
                description=(
                    f"M{mag} earthquake with {nearby_fires} fire hotspot(s) "
                    f"and {nearby_outages} internet outage(s) within {radius}km."
                ),
                lat=eq["lat"],
                lng=eq["lng"],
                data={"magnitude": mag, "fires": nearby_fires,
                      "outages": nearby_outages, "place": eq.get("place", "")},
            ))
        elif nearby_fires > 2 or nearby_outages > 1:
            alerts.append(Alert(
                alert_type="infrastructure_cascade",
                severity=AlertSeverity.ELEVATED,
                title=f"Possible Cascade — M{mag} {place}",
                description=(
                    f"M{mag} earthquake co-located with {nearby_fires} fires "
                    f"and {nearby_outages} outages."
                ),
                lat=eq["lat"],
                lng=eq["lng"],
                data={"magnitude": mag, "fires": nearby_fires,
                      "outages": nearby_outages},
            ))

    return alerts


# ---------------------------------------------------------------------------
# 4. Sanctions Evasion
# ---------------------------------------------------------------------------
def check_sanctions_evasion(ds: DataSource) -> list[Alert]:
    """Alert when ships with suspicious destinations are near sanctioned zones."""
    ships = ds.query("ships", limit=500)
    if not ships:
        return []

    alerts: list[Alert] = []
    for zone in _SANCTIONED_ZONES:
        suspicious_ships: list[dict] = []
        for s in ships:
            if not _has_position(s):
                continue
            dist = _haversine_km(zone["lat"], zone["lng"], s["lat"], s["lng"])
            if dist > zone["radius_km"]:
                continue
            dest = (s.get("destination") or "").strip().upper()
            if dest in _SUSPICIOUS_DESTINATIONS and s.get("type") in ("tanker", "cargo"):
                suspicious_ships.append({
                    "name": s.get("name", "Unknown"),
                    "mmsi": s.get("mmsi", ""),
                    "destination": dest or "(blank)",
                    "distance_km": round(dist, 1),
                })

        if suspicious_ships:
            alerts.append(Alert(
                alert_type="sanctions_evasion",
                severity=AlertSeverity.ELEVATED,
                title=f"Suspicious Vessels — {zone['name']}",
                description=(
                    f"{len(suspicious_ships)} vessel(s) with blank/suspicious destinations "
                    f"detected near {zone['name']}."
                ),
                lat=zone["lat"],
                lng=zone["lng"],
                data={"zone": zone["name"], "vessels": suspicious_ships},
            ))

    return alerts


# ---------------------------------------------------------------------------
# 5. Airlift Surge
# ---------------------------------------------------------------------------
def _is_airlift(flight: dict) -> bool:
    """True when the flight matches a strategic airlift profile."""
    model = flight.get("model", "")
    callsign = flight.get("callsign", "")
    return (
        model in _AIRLIFT_MODELS
        or any(model.startswith(p) for p in _AIRLIFT_MODEL_PREFIXES)
        or any(callsign.startswith(p) for p in _AIRLIFT_CALLSIGN_PREFIXES)
        or flight.get("military_type", "") == "cargo"
    )


def check_airlift_surge(ds: DataSource) -> list[Alert]:
    """Alert when strategic airlift aircraft count exceeds threshold."""
    flights = ds.query("military_flights", limit=500)
    if not flights:
        return []

    airlift = [f for f in flights if _is_airlift(f)]

    if len(airlift) < _AIRLIFT_SURGE_THRESHOLD:
        return []

    severity = AlertSeverity.CRITICAL if len(airlift) >= 8 else AlertSeverity.ELEVATED
    center_lat, center_lng = _centroid(airlift)

    return [Alert(
        alert_type="airlift_surge",
        severity=severity,
        title=f"Airlift Surge — {len(airlift)} strategic transports",
        description=(
            f"{len(airlift)} strategic airlift aircraft (C-17, C-5, C-130) detected airborne. "
            f"Normal baseline: 1-3."
        ),
        lat=round(center_lat, 2),
        lng=round(center_lng, 2),
        data={"count": len(airlift),
              "callsigns": [f.get("callsign", "") for f in airlift[:10]]},
    )]


# ---------------------------------------------------------------------------
# 6. Under-Reported Crisis
# ---------------------------------------------------------------------------
def check_under_reported_crisis(ds: DataSource) -> list[Alert]:
    """Alert when GDELT event count is high but news coverage is low."""
    gdelt = ds.query("gdelt", limit=500)
    news = ds.query("news", limit=500)

    if not gdelt:
        return []

    total_gdelt = sum(e.get("count", 1) for e in gdelt)
    news_count = len(news)

    if total_gdelt < 30 or news_count > max(3, total_gdelt // 10):
        return []

    return [Alert(
        alert_type="under_reported_crisis",
        severity=AlertSeverity.ELEVATED,
        title="Under-Reported Crisis Detected",
        description=(
            f"{total_gdelt} GDELT events detected across {len(gdelt)} clusters, "
            f"but only {news_count} news article(s). Potential coverage gap."
        ),
        data={"gdelt_events": total_gdelt, "gdelt_clusters": len(gdelt),
              "news_articles": news_count},
    )]


# ---------------------------------------------------------------------------
# 7. EW Detection (Electronic Warfare)
# ---------------------------------------------------------------------------
def check_ew_detection(ds: DataSource) -> list[Alert]:
    """Alert when GPS jamming + internet outage + conflict co-located."""
    jamming = ds.query("gps_jamming", limit=200)
    outages = ds.query("internet_outages", limit=200)
    gdelt = ds.query("gdelt", limit=200)

    if not jamming:
        return []

    radius = 300  # km -- EW effects can be wide-area

    alerts: list[Alert] = []
    for j in jamming:
        if not _has_position(j):
            continue

        nearby_outages = len(_find_nearby(j, outages, radius))
        nearby_conflict = len(_find_nearby(j, gdelt, radius))

        if nearby_outages and nearby_conflict:
            severity = AlertSeverity.CRITICAL
            classification = "LIKELY EW"
        elif nearby_outages or nearby_conflict:
            severity = AlertSeverity.ELEVATED
            classification = "POSSIBLE EW"
        else:
            continue

        alerts.append(Alert(
            alert_type="ew_detection",
            severity=severity,
            title=f"Electronic Warfare — {classification}",
            description=(
                f"GPS jamming co-located with {nearby_outages} internet outage(s) "
                f"and {nearby_conflict} conflict event(s) within {radius}km."
            ),
            lat=j["lat"],
            lng=j["lng"],
            data={"classification": classification,
                  "jamming_severity": j.get("severity", "unknown"),
                  "outages": nearby_outages,
                  "conflict_events": nearby_conflict},
        ))

    return alerts


# ---------------------------------------------------------------------------
# 8. VIP Movement
# ---------------------------------------------------------------------------
def check_vip_movement(ds: DataSource) -> list[Alert]:
    """Alert when notable/tracked aircraft are detected airborne."""
    flights = ds.query("military_flights", limit=500)
    civil_flights = ds.query("flights", limit=500)
    all_flights = flights + civil_flights

    if not all_flights:
        return []

    alerts: list[Alert] = []
    for f in all_flights:
        is_notable = f.get("is_notable", False)
        mil_type = f.get("military_type", "")

        if not (is_notable or mil_type == "vip"):
            continue

        alt = f.get("alt", 0)
        if not alt or alt <= 1000:
            continue

        callsign = f.get("callsign", "Unknown")
        model = f.get("model", "")
        notable_reason = f.get("notable_reason", "")

        alerts.append(Alert(
            alert_type="vip_movement",
            severity=AlertSeverity.ELEVATED,
            title=f"VIP Aircraft — {callsign}",
            description=(
                f"Notable aircraft {callsign} ({model}) detected airborne. "
                f"{notable_reason}".strip()
            ),
            lat=f.get("lat"),
            lng=f.get("lng"),
            data={"callsign": callsign, "model": model,
                  "notable_reason": notable_reason},
        ))

    return alerts


# ---------------------------------------------------------------------------
# 9. Prediction Market Signal
# ---------------------------------------------------------------------------

# Conflict regions mapped from market title keywords to coordinates
_CONFLICT_REGIONS: dict[str, tuple[float, float]] = {
    "ukraine": (48.5, 31.5),
    "russia": (55.7, 37.6),
    "taiwan": (23.5, 121.0),
    "china": (35.0, 105.0),
    "iran": (32.0, 53.0),
    "korea": (38.0, 127.0),
    "north korea": (39.0, 126.0),
    "hormuz": (26.5, 56.3),
    "gaza": (31.4, 34.4),
    "israel": (31.8, 35.2),
    "syria": (35.0, 38.0),
}


def check_prediction_market_signal(ds: DataSource) -> list[Alert]:
    """Alert when CONFLICT prediction markets spike AND military flights are elevated nearby.

    Filters: CONFLICT category only (excludes POLITICS/FINANCE/CRYPTO to avoid
    election-cycle false positives). Requires >5 military flights within 500km
    (NATO baseline is ~2-3, so >5 is genuinely elevated).
    """
    markets = ds.query("prediction_markets", limit=200)
    mil_flights = ds.query("military_flights", limit=500)

    if not markets or not mil_flights:
        return []

    # Filter to CONFLICT category with significant movement
    conflict_markets = [
        m for m in markets
        if str(m.get("category", "")).upper() == "CONFLICT"
        and abs(m.get("delta_pct", 0)) > 10
    ]

    if not conflict_markets:
        return []

    matched_regions: list[dict] = []

    for market in conflict_markets:
        title_lower = market.get("title", "").lower()
        for keyword, (rlat, rlng) in _CONFLICT_REGIONS.items():
            if keyword not in title_lower:
                continue

            origin = {"lat": rlat, "lng": rlng}
            nearby_count = _count_nearby(origin, mil_flights, 500)

            if nearby_count <= 5:
                continue

            matched_regions.append({
                "market_title": market.get("title", "Unknown"),
                "delta_pct": round(market.get("delta_pct", 0), 1),
                "consensus_pct": market.get("consensus_pct"),
                "region": keyword,
                "military_flights_nearby": nearby_count,
            })
            break  # One region match per market

    if not matched_regions:
        return []

    severity = AlertSeverity.CRITICAL if len(matched_regions) >= 2 else AlertSeverity.ELEVATED

    lat, lng = _CONFLICT_REGIONS[matched_regions[0]["region"]]

    market_summaries = [
        f"{r['market_title']} (delta {r['delta_pct']:+.1f}pp, {r['military_flights_nearby']} mil flights)"
        for r in matched_regions
    ]

    return [Alert(
        alert_type="prediction_market_signal",
        severity=severity,
        title=f"Market Signal — {len(matched_regions)} conflict market(s) spiking",
        description=(
            f"CONFLICT prediction market(s) moving >10pp with elevated military "
            f"activity: {'; '.join(market_summaries[:3])}"
        ),
        lat=lat,
        lng=lng,
        data={
            "matched_regions": matched_regions,
            "indicators": [
                f"Market: {r['market_title']} delta {r['delta_pct']:+.1f}pp"
                for r in matched_regions
            ] + [
                f"Military flights: {r['military_flights_nearby']} near {r['region']}"
                for r in matched_regions
            ],
        },
    )]


# ---------------------------------------------------------------------------
# 10. Black Sea Escalation
# ---------------------------------------------------------------------------

# Black Sea zone bounding box
_BLACK_SEA_LAT_MIN, _BLACK_SEA_LAT_MAX = 43.0, 48.0
_BLACK_SEA_LNG_MIN, _BLACK_SEA_LNG_MAX = 30.0, 42.0
_BLACK_SEA_CENTER = {"lat": 45.5, "lng": 36.0}

_MILITARY_SHIP_TYPES = {"military", "carrier", "destroyer", "frigate"}


def _in_black_sea(item: dict) -> bool:
    """Check if an item's coordinates fall within the Black Sea zone."""
    raw_lat = item.get("lat") or item.get("latitude")
    raw_lng = item.get("lng") or item.get("lon") or item.get("longitude")
    if raw_lat is None or raw_lng is None:
        return False
    try:
        lat, lng = float(raw_lat), float(raw_lng)
    except (ValueError, TypeError):
        return False
    return (_BLACK_SEA_LAT_MIN <= lat <= _BLACK_SEA_LAT_MAX
            and _BLACK_SEA_LNG_MIN <= lng <= _BLACK_SEA_LNG_MAX)


def check_black_sea_escalation(ds: DataSource) -> list[Alert]:
    """Alert when Ukraine air raids + military flights/ships converge in Black Sea.

    Requires active air raids (>0) in the Black Sea zone AND at least one of:
    - Military flights > 3 within 500km of zone center
    - Military-type ships > 1 in zone (NOT commercial vessels)
    """
    ukraine_alerts = ds.query("ukraine_alerts", limit=200)
    mil_flights = ds.query("military_flights", limit=500)
    ships = ds.query("ships", limit=500)

    if not ukraine_alerts:
        return []

    # Count air raids in Black Sea zone
    raids_in_zone = [a for a in ukraine_alerts if _in_black_sea(a)]
    if not raids_in_zone:
        return []

    # Count military flights near zone center
    mil_flight_count = _count_nearby(_BLACK_SEA_CENTER, mil_flights, 500)

    # Count military-type ships only (red team: commercial traffic always exceeds thresholds)
    mil_ships_in_zone = [
        s for s in ships
        if _in_black_sea(s) and s.get("type", "").lower() in _MILITARY_SHIP_TYPES
    ]

    has_mil_flights = mil_flight_count > 3
    has_mil_ships = len(mil_ships_in_zone) > 1

    if not has_mil_flights and not has_mil_ships:
        return []

    # Determine severity
    source_types = ["air_raids"]
    if has_mil_flights:
        source_types.append("military_flights")
    if has_mil_ships:
        source_types.append("military_ships")

    severity = AlertSeverity.CRITICAL if len(source_types) >= 3 else AlertSeverity.ELEVATED

    indicators = [
        f"Air raids: {len(raids_in_zone)} active in Black Sea zone",
        f"Military flights: {mil_flight_count} within 500km",
        f"Military ships: {len(mil_ships_in_zone)} in zone",
    ]

    raid_lat, raid_lng = _centroid(raids_in_zone)
    if not any(_has_position(r) for r in raids_in_zone):
        raid_lat, raid_lng = _BLACK_SEA_CENTER["lat"], _BLACK_SEA_CENTER["lng"]

    return [Alert(
        alert_type="black_sea_escalation",
        severity=severity,
        title=f"Black Sea Escalation — {len(source_types)} source types converging",
        description=(
            f"{len(raids_in_zone)} air raid(s) active in Black Sea zone with "
            f"{mil_flight_count} military flights and {len(mil_ships_in_zone)} military vessel(s)."
        ),
        lat=round(raid_lat, 2),
        lng=round(raid_lng, 2),
        data={
            "source_types": source_types,
            "raid_count": len(raids_in_zone),
            "military_flight_count": mil_flight_count,
            "military_ship_count": len(mil_ships_in_zone),
            "indicators": indicators,
        },
    )]


# ---------------------------------------------------------------------------
# 11. Disinformation Divergence
# ---------------------------------------------------------------------------

def _is_gdelt_stale() -> bool:
    """Check if GDELT data is stale or missing (staleness gate).

    Reads source_timestamps from the store. If GDELT hasn't been updated
    in >30 minutes, considers it stale to prevent false "manufactured" labels.
    """
    try:
        from services.fetchers._store import source_timestamps
        gdelt_ts = source_timestamps.get("gdelt")
        if not gdelt_ts:
            return True
        last_update = datetime.fromisoformat(gdelt_ts)
        return datetime.utcnow() - last_update > timedelta(minutes=30)
    except Exception:
        return True


def check_disinformation_divergence(ds: DataSource) -> list[Alert]:
    """Alert when FIMI major waves diverge from GDELT event coverage.

    High FIMI + low GDELT = "manufactured" crisis (ELEVATED)
    High FIMI + high GDELT = "amplified" real event (NORMAL, informational)

    Staleness gate: skips entirely if GDELT data is empty or >30min stale,
    to prevent ALL FIMI being labeled "manufactured" when GDELT is down.
    """
    fimi = ds.query("fimi", limit=200)
    gdelt = ds.query("gdelt", limit=500)

    if not fimi:
        return []

    # Staleness gate — skip if GDELT is unreliable
    if not gdelt or _is_gdelt_stale():
        return []

    # Filter to major waves only
    major_waves = [f for f in fimi if f.get("is_major_wave")]
    if not major_waves:
        return []

    # Group FIMI by target country
    by_country: dict[str, list[dict]] = {}
    for f in major_waves:
        country = f.get("target_country", "").strip()
        if country:
            by_country.setdefault(country, []).append(f)

    if not by_country:
        return []

    def count_gdelt_for_country(country: str) -> int:
        """Count GDELT events mentioning a country (handles GeoJSON and flat formats)."""
        country_lower = country.lower()
        count = 0
        for g in gdelt:
            props = g.get("properties", {})
            headlines = props.get("_headlines_list", [])
            text = " ".join([
                str(props.get("name", "")),
                str(props.get("action_geo_cc", "")),
                " ".join(str(h) for h in headlines),
                str(g.get("country", "")),
                str(g.get("country_code", "")),
                str(g.get("action_geo", "")),
            ]).lower()
            if country_lower in text:
                count += 1
        return count

    alerts: list[Alert] = []
    for country, narratives in by_country.items():
        gdelt_count = count_gdelt_for_country(country)
        actors = list({n.get("actor", "Unknown") for n in narratives if n.get("actor")})

        if gdelt_count < 5:
            classification = "manufactured"
            severity = AlertSeverity.ELEVATED
        elif gdelt_count > 20:
            classification = "amplified"
            severity = AlertSeverity.NORMAL
        else:
            continue  # Ambiguous zone — don't alert

        indicators = [
            f"FIMI narratives: {len(narratives)} major wave(s) targeting {country}",
            f"GDELT events: {gdelt_count} mentioning {country}",
            f"Classification: {classification}",
            f"Actors: {', '.join(actors[:5])}",
        ]
        narrative_titles = [n.get("title", "Untitled") for n in narratives[:5]]

        alerts.append(Alert(
            alert_type="disinformation_divergence",
            severity=severity,
            title=f"Disinfo Divergence — {classification} crisis ({country})",
            description=(
                f"{len(narratives)} FIMI major wave(s) targeting {country} with "
                f"{gdelt_count} GDELT events. Classification: {classification}."
            ),
            data={
                "country": country,
                "classification": classification,
                "fimi_count": len(narratives),
                "gdelt_count": gdelt_count,
                "actors": actors,
                "narrative_titles": narrative_titles,
                "indicators": indicators,
            },
        ))

    return alerts


# ---------------------------------------------------------------------------
# 12. Supply Chain Cascade
# ---------------------------------------------------------------------------

def check_supply_chain_cascade(ds: DataSource) -> list[Alert]:
    """Alert when internet outages + train disruptions + fires co-locate.

    Requires internet outage + 2 of {disrupted trains, fire hotspots} within 200km.
    Train data covers Amtrak (US) and Finnish DigiTraffic — geographic bias noted.
    """
    outages = ds.query("internet_outages", limit=200)
    trains = ds.query("trains", limit=500)
    fires = ds.query("firms_fires", limit=500)

    if not outages:
        return []

    radius = 200  # km

    # Filter to disrupted trains (stopped or delayed)
    disrupted_trains = [
        t for t in trains
        if _has_position(t)
        and (
            t.get("speed", 1) == 0
            or "delay" in str(t.get("status", "")).lower()
            or "stop" in str(t.get("status", "")).lower()
        )
    ]

    alerts: list[Alert] = []
    for outage in outages:
        if not _has_position(outage):
            continue

        nearby_trains = _count_nearby(outage, disrupted_trains, radius)
        nearby_fires = _count_nearby(outage, fires, radius)

        if nearby_trains == 0 and nearby_fires == 0:
            continue  # Need outage + at least 1 other source

        source_types = ["internet_outage"]
        if nearby_trains > 0:
            source_types.append("train_disruption")
        if nearby_fires > 0:
            source_types.append("fire_hotspot")

        severity = AlertSeverity.CRITICAL if len(source_types) >= 3 else AlertSeverity.ELEVATED

        indicators = [
            f"Internet outage at ({outage['lat']:.1f}, {outage['lng']:.1f})",
            f"Disrupted trains: {nearby_trains} within {radius}km",
            f"Fire hotspots: {nearby_fires} within {radius}km",
        ]

        outage_name = outage.get("name", outage.get("country", "Unknown region"))

        alerts.append(Alert(
            alert_type="supply_chain_cascade",
            severity=severity,
            title=f"Supply Chain Cascade — {outage_name}",
            description=(
                f"Internet outage co-located with {nearby_trains} disrupted train(s) "
                f"and {nearby_fires} fire hotspot(s) within {radius}km."
            ),
            lat=outage["lat"],
            lng=outage["lng"],
            data={
                "source_types": source_types,
                "outage_name": outage_name,
                "disrupted_trains": nearby_trains,
                "fire_hotspots": nearby_fires,
                "indicators": indicators,
            },
        ))

    return alerts


# ---------------------------------------------------------------------------
# Convenience: run all checkers
# ---------------------------------------------------------------------------
ALL_CHECKERS = [
    check_military_convergence,
    check_chokepoint_disruption,
    check_infrastructure_cascade,
    check_sanctions_evasion,
    check_airlift_surge,
    check_under_reported_crisis,
    check_ew_detection,
    check_vip_movement,
    check_prediction_market_signal,
    check_black_sea_escalation,
    check_disinformation_divergence,
    check_supply_chain_cascade,
]


def run_all_checkers(ds: DataSource) -> list[Alert]:
    """Run all alert checkers and return combined results."""
    alerts: list[Alert] = []
    for checker in ALL_CHECKERS:
        try:
            alerts.extend(checker(ds))
        except Exception:
            logger.exception("Checker %s failed", checker.__name__)
    return alerts
