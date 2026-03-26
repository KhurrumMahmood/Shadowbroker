"""Proactive alert checkers — pure functions that detect patterns in live data.

Each checker: (DataSource) -> list[Alert]
No LLM calls — pure Python pattern matching on entity data.
"""
from __future__ import annotations

import logging

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
_CHOKEPOINTS = [
    {"name": "Strait of Hormuz", "lat": 26.5, "lng": 56.3, "radius_km": 150},
    {"name": "Suez Canal", "lat": 30.0, "lng": 32.5, "radius_km": 100},
    {"name": "Strait of Malacca", "lat": 2.5, "lng": 101.5, "radius_km": 150},
    {"name": "Bab-el-Mandeb", "lat": 12.6, "lng": 43.3, "radius_km": 100},
    {"name": "Panama Canal", "lat": 9.1, "lng": -79.7, "radius_km": 80},
    {"name": "Taiwan Strait", "lat": 24.5, "lng": 119.5, "radius_km": 200},
]

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
