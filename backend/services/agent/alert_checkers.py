"""Proactive alert checkers — pure functions that detect patterns in live data.

Each checker: (DataSource) -> list[Alert]
No LLM calls — pure Python pattern matching on entity data.
"""
from __future__ import annotations

import math
from services.agent.alerts import Alert, AlertSeverity
from services.agent.datasource import DataSource


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Chokepoints and sanctioned zones (static reference data)
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

_AIRLIFT_SURGE_THRESHOLD = 5  # 5+ strategic airlift = anomalous


# ---------------------------------------------------------------------------
# 1. Military Convergence
# ---------------------------------------------------------------------------
def check_military_convergence(ds: DataSource) -> list[Alert]:
    """Alert when 2+ countries' military flights are within 200km of each other."""
    flights = ds.query("military_flights", limit=500)
    if len(flights) < 2:
        return []

    # Group flights by country
    by_country: dict[str, list[dict]] = {}
    for f in flights:
        c = f.get("country", "Unknown")
        by_country.setdefault(c, []).append(f)

    countries = list(by_country.keys())
    if len(countries) < 2:
        return []

    # Check pairwise proximity between countries' flights
    convergence_zones: list[dict] = []
    seen_pairs = set()

    for i, c1 in enumerate(countries):
        for c2 in countries[i + 1:]:
            pair = tuple(sorted([c1, c2]))
            if pair in seen_pairs:
                continue
            for f1 in by_country[c1]:
                if f1.get("lat") is None:
                    continue
                for f2 in by_country[c2]:
                    if f2.get("lat") is None:
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

    # Find the zone with the most countries
    all_countries = set()
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

    alerts = []
    for cp in _CHOKEPOINTS:
        for j in jamming:
            if j.get("lat") is None:
                continue
            dist = _haversine_km(cp["lat"], cp["lng"], j["lat"], j["lng"])
            if dist < cp["radius_km"]:
                sev_str = j.get("severity", "").lower()
                severity = (AlertSeverity.CRITICAL if sev_str == "high"
                            else AlertSeverity.ELEVATED)
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

    # Need at least earthquakes + one other signal
    if not earthquakes or (not fires and not outages):
        return []

    alerts = []
    radius = 200  # km

    for eq in earthquakes:
        if eq.get("lat") is None:
            continue
        mag = eq.get("mag", 0)
        if mag < 4.5:
            continue

        co_located_fires = sum(
            1 for f in fires
            if f.get("lat") is not None
            and _haversine_km(eq["lat"], eq["lng"], f["lat"], f["lng"]) < radius
        )
        co_located_outages = [
            o for o in outages
            if o.get("lat") is not None
            and _haversine_km(eq["lat"], eq["lng"], o["lat"], o["lng"]) < radius
        ]

        if co_located_fires > 0 and co_located_outages:
            # Full cascade: earthquake + fire + outage
            alerts.append(Alert(
                alert_type="infrastructure_cascade",
                severity=AlertSeverity.CRITICAL,
                title=f"Infrastructure Cascade — M{mag} {eq.get('place', 'Unknown')}",
                description=(
                    f"M{mag} earthquake with {co_located_fires} fire hotspot(s) "
                    f"and {len(co_located_outages)} internet outage(s) within {radius}km."
                ),
                lat=eq["lat"],
                lng=eq["lng"],
                data={"magnitude": mag, "fires": co_located_fires,
                      "outages": len(co_located_outages), "place": eq.get("place", "")},
            ))
        elif co_located_fires > 2 or len(co_located_outages) > 1:
            # Partial cascade
            alerts.append(Alert(
                alert_type="infrastructure_cascade",
                severity=AlertSeverity.ELEVATED,
                title=f"Possible Cascade — M{mag} {eq.get('place', 'Unknown')}",
                description=(
                    f"M{mag} earthquake co-located with {co_located_fires} fires "
                    f"and {len(co_located_outages)} outages."
                ),
                lat=eq["lat"],
                lng=eq["lng"],
                data={"magnitude": mag, "fires": co_located_fires,
                      "outages": len(co_located_outages)},
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

    _SUSPICIOUS_DESTS = {"", "FOR ORDERS", "FOR ORDER", "ORDERS", "TBN", "TBA"}

    alerts = []
    for zone in _SANCTIONED_ZONES:
        suspicious_ships = []
        for s in ships:
            if s.get("lat") is None:
                continue
            dist = _haversine_km(zone["lat"], zone["lng"], s["lat"], s["lng"])
            if dist > zone["radius_km"]:
                continue
            dest = (s.get("destination") or "").strip().upper()
            if dest in _SUSPICIOUS_DESTS and s.get("type") in ("tanker", "cargo"):
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
def check_airlift_surge(ds: DataSource) -> list[Alert]:
    """Alert when strategic airlift aircraft count exceeds threshold."""
    flights = ds.query("military_flights", limit=500)
    if not flights:
        return []

    airlift = []
    for f in flights:
        model = f.get("model", "")
        callsign = f.get("callsign", "")
        mil_type = f.get("military_type", "")
        is_airlift = (
            model in _AIRLIFT_MODELS
            or any(model.startswith(m) for m in ("C-17", "C-5", "C-130"))
            or any(callsign.startswith(p) for p in _AIRLIFT_CALLSIGN_PREFIXES)
            or mil_type == "cargo"
        )
        if is_airlift:
            airlift.append(f)

    if len(airlift) < _AIRLIFT_SURGE_THRESHOLD:
        return []

    severity = AlertSeverity.CRITICAL if len(airlift) >= 8 else AlertSeverity.ELEVATED

    # Compute average position for the alert
    lats = [f["lat"] for f in airlift if f.get("lat") is not None]
    lngs = [f["lng"] for f in airlift if f.get("lng") is not None]
    center_lat = sum(lats) / len(lats) if lats else 0
    center_lng = sum(lngs) / len(lngs) if lngs else 0

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

    # Threshold: 10+ GDELT event clusters with 3 or fewer news articles
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

    radius = 300  # km — EW effects can be wide-area

    alerts = []
    for j in jamming:
        if j.get("lat") is None:
            continue

        co_outages = [
            o for o in outages
            if o.get("lat") is not None
            and _haversine_km(j["lat"], j["lng"], o["lat"], o["lng"]) < radius
        ]
        co_conflict = [
            g for g in gdelt
            if g.get("lat") is not None
            and _haversine_km(j["lat"], j["lng"], g["lat"], g["lng"]) < radius
        ]

        if co_outages and co_conflict:
            severity = AlertSeverity.CRITICAL
            classification = "LIKELY EW"
        elif co_outages or co_conflict:
            severity = AlertSeverity.ELEVATED
            classification = "POSSIBLE EW"
        else:
            continue

        alerts.append(Alert(
            alert_type="ew_detection",
            severity=severity,
            title=f"Electronic Warfare — {classification}",
            description=(
                f"GPS jamming co-located with {len(co_outages)} internet outage(s) "
                f"and {len(co_conflict)} conflict event(s) within {radius}km."
            ),
            lat=j["lat"],
            lng=j["lng"],
            data={"classification": classification,
                  "jamming_severity": j.get("severity", "unknown"),
                  "outages": len(co_outages),
                  "conflict_events": len(co_conflict)},
        ))

    return alerts


# ---------------------------------------------------------------------------
# 8. VIP Movement
# ---------------------------------------------------------------------------
def check_vip_movement(ds: DataSource) -> list[Alert]:
    """Alert when notable/tracked aircraft are detected airborne."""
    flights = ds.query("military_flights", limit=500)
    # Also check regular flights for tracked aircraft
    civil_flights = ds.query("flights", limit=500)
    all_flights = flights + civil_flights

    if not all_flights:
        return []

    alerts = []
    for f in all_flights:
        is_notable = f.get("is_notable", False)
        notable_reason = f.get("notable_reason", "")
        mil_type = f.get("military_type", "")

        if is_notable or mil_type == "vip":
            callsign = f.get("callsign", "Unknown")
            model = f.get("model", "")
            alt = f.get("alt", 0)

            # Only alert if airborne (alt > 1000ft)
            if alt and alt > 1000:
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
    alerts = []
    for checker in ALL_CHECKERS:
        try:
            alerts.extend(checker(ds))
        except Exception:
            pass  # Individual checker failures shouldn't block others
    return alerts
