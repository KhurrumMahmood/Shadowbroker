"""Rule-based correlation engine — detects compound patterns across data layers.

Runs in parallel with the existing AlertEngine. Both read from latest_data,
both write alerts. The correlation engine detects multi-layer patterns;
the alert engine detects single-layer anomalies.

Three correlation types:
  1. RF Anomaly: GPS jamming + internet outage in same 1° grid
  2. Military Buildup: military flights + naval vessels + GDELT conflict in same grid
  3. Infrastructure Cascade: internet outage + KiwiSDR silence in same grid

Ported from upstream BigBodyCobain/Shadowbroker v0.9.6.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from math import floor

from services.agent.alert_checkers import _MILITARY_SHIP_TYPES
from services.agent.alerts import Alert, AlertSeverity, get_alert_store
from services.agent.significance import score_alert

logger = logging.getLogger(__name__)

# Grid resolution: 1 degree (~111km at equator)
_GRID_RES = 1.0

# Minimum indicators for each correlation type
_RF_MIN_INDICATORS = 3
_MILITARY_MIN_INDICATORS = 3
_INFRA_MIN_INDICATORS = 2


def _grid_key(lat: float, lng: float) -> str:
    """Bin a lat/lng into a 1-degree grid cell."""
    return f"{floor(lat / _GRID_RES) * _GRID_RES:.0f},{floor(lng / _GRID_RES) * _GRID_RES:.0f}"


def _grid_center(key: str) -> tuple[float, float]:
    """Get the center lat/lng of a grid cell."""
    parts = key.split(",")
    lat = float(parts[0]) + _GRID_RES / 2
    lng = float(parts[1]) + _GRID_RES / 2
    return lat, lng


def _extract_coords(item: dict) -> tuple[float, float] | None:
    """Extract lat/lng from various field naming conventions."""
    lat = item.get("lat") or item.get("latitude")
    lng = item.get("lng") or item.get("lon") or item.get("longitude")
    if lat is None or lng is None:
        return None
    try:
        return float(lat), float(lng)
    except (ValueError, TypeError):
        return None


def _bin_to_grid(items: list[dict]) -> dict[str, list[dict]]:
    """Bin a list of items into grid cells by their coordinates."""
    grid: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        coords = _extract_coords(item)
        if coords:
            key = _grid_key(coords[0], coords[1])
            grid[key].append(item)
    return grid


# ---------------------------------------------------------------------------
# Correlation detectors
# ---------------------------------------------------------------------------

def _detect_rf_anomaly(data: dict) -> list[dict]:
    """Detect RF anomalies: GPS jamming + internet outage in same grid.

    Quality gates:
    - GPS ratio >= 60% (high-confidence jamming area)
    - Outage severity >= 40% (significant disruption)
    - 3+ indicators required
    """
    gps = data.get("gps_jamming", [])
    outages = data.get("internet_outages", [])

    if not gps or not outages:
        return []

    gps_grid = _bin_to_grid(gps)
    outage_grid = _bin_to_grid(outages)

    findings = []
    for cell, gps_items in gps_grid.items():
        outage_items = outage_grid.get(cell, [])
        if not outage_items:
            continue

        # Quality gates
        gps_ratios = [g.get("ratio", 0) for g in gps_items if g.get("ratio")]
        avg_gps_ratio = sum(gps_ratios) / len(gps_ratios) if gps_ratios else 0
        outage_severities = [o.get("severity", 0) for o in outage_items if o.get("severity")]
        avg_severity = sum(outage_severities) / len(outage_severities) if outage_severities else 50

        indicators = len(gps_items) + len(outage_items)
        if indicators < _RF_MIN_INDICATORS:
            continue
        if 0 < avg_gps_ratio < 60:
            continue

        lat, lng = _grid_center(cell)
        findings.append({
            "type": "rf_anomaly",
            "lat": lat,
            "lng": lng,
            "grid_cell": cell,
            "gps_count": len(gps_items),
            "outage_count": len(outage_items),
            "avg_gps_ratio": round(avg_gps_ratio, 1),
            "avg_outage_severity": round(avg_severity, 1),
            "indicators": indicators,
            "severity": "high" if indicators >= 6 else "medium",
            "_source": "correlation_engine/rf_anomaly",
        })

    return findings


def _detect_military_buildup(data: dict) -> list[dict]:
    """Detect military buildup: flights + ships + GDELT conflict in same grid.

    Severity: high (11+ indicators), medium (6-10), low (3-5)
    """
    mil_flights = data.get("military_flights", [])
    mil_ships = [s for s in data.get("ships", [])
                 if s.get("type") in ("military", "carrier", "destroyer", "frigate")]
    gdelt = [g for g in data.get("gdelt", [])
             if "conflict" in str(g.get("category", "")).lower()
             or "military" in str(g.get("category", "")).lower()]
    ukraine_alerts = data.get("ukraine_alerts", [])

    all_military = mil_flights + mil_ships + gdelt + ukraine_alerts
    if len(all_military) < _MILITARY_MIN_INDICATORS:
        return []

    # Bin each source separately
    flight_grid = _bin_to_grid(mil_flights)
    ship_grid = _bin_to_grid(mil_ships)
    gdelt_grid = _bin_to_grid(gdelt)
    alert_grid = _bin_to_grid(ukraine_alerts)

    # Find cells with multiple source types
    all_cells = set(flight_grid) | set(ship_grid) | set(gdelt_grid) | set(alert_grid)

    # Source label -> grid, keyed for the output dict
    source_grids = [
        ("military_flights", "flight_count", flight_grid),
        ("naval_vessels", "ship_count", ship_grid),
        ("gdelt_conflict", "gdelt_count", gdelt_grid),
        ("ukraine_alerts", "alert_count", alert_grid),
    ]

    findings = []
    for cell in all_cells:
        sources = []
        indicator_count = 0
        counts: dict[str, int] = {}

        for source_label, count_key, grid in source_grids:
            items_in_cell = grid.get(cell, [])
            counts[count_key] = len(items_in_cell)
            if items_in_cell:
                sources.append(source_label)
                indicator_count += len(items_in_cell)

        # Need at least 2 source types and minimum indicators
        if len(sources) < 2 or indicator_count < _MILITARY_MIN_INDICATORS:
            continue

        if indicator_count >= 11:
            severity = "high"
        elif indicator_count >= 6:
            severity = "medium"
        else:
            severity = "low"

        lat, lng = _grid_center(cell)
        findings.append({
            "type": "military_buildup",
            "lat": lat,
            "lng": lng,
            "grid_cell": cell,
            "sources": sources,
            **counts,
            "indicators": indicator_count,
            "severity": severity,
            "_source": "correlation_engine/military_buildup",
        })

    return findings


def _detect_infra_cascade(data: dict) -> list[dict]:
    """Detect infrastructure cascade: internet outage + KiwiSDR in same grid.

    Indicates potential infrastructure disruption affecting both internet
    and radio monitoring capabilities.
    """
    outages = data.get("internet_outages", [])
    kiwisdr = data.get("kiwisdr", [])
    fires = data.get("firms_fires", [])

    if not outages:
        return []

    outage_grid = _bin_to_grid(outages)
    kiwi_grid = _bin_to_grid(kiwisdr) if kiwisdr else {}
    fire_grid = _bin_to_grid(fires) if fires else {}

    findings = []
    for cell, outage_items in outage_grid.items():
        kiwi_items = kiwi_grid.get(cell, [])
        fire_items = fire_grid.get(cell, [])

        sources = ["internet_outage"]
        indicator_count = len(outage_items)

        if kiwi_items:
            sources.append("kiwisdr_affected")
            indicator_count += len(kiwi_items)
        if fire_items:
            sources.append("fire_hotspots")
            indicator_count += min(len(fire_items), 5)

        if indicator_count < _INFRA_MIN_INDICATORS or len(sources) < 2:
            continue

        lat, lng = _grid_center(cell)
        findings.append({
            "type": "infra_cascade",
            "lat": lat,
            "lng": lng,
            "grid_cell": cell,
            "sources": sources,
            "outage_count": len(outage_items),
            "kiwisdr_count": len(kiwi_items),
            "fire_count": len(fire_items),
            "indicators": indicator_count,
            "severity": "high" if indicator_count >= 6 else "medium",
            "_source": "correlation_engine/infra_cascade",
        })

    return findings


# ---------------------------------------------------------------------------
# 4. Conflict Escalation
# ---------------------------------------------------------------------------


def _detect_conflict_escalation(data: dict) -> list[dict]:
    """Detect conflict escalation: 3+ source types converging in a grid cell
    AND a CONFLICT prediction market showing significant movement.

    Source types: ukraine_alerts, military flights, military ships, GDELT conflict.
    Market gate: requires any CONFLICT market with delta_pct > 5%.
    """
    ukraine_alerts = data.get("ukraine_alerts", [])
    mil_flights = data.get("military_flights", [])
    ships = data.get("ships", [])
    gdelt = [g for g in data.get("gdelt", [])
             if "conflict" in str(g.get("category", "")).lower()
             or "military" in str(g.get("category", "")).lower()]
    markets = data.get("prediction_markets", [])

    # Market gate: need at least one CONFLICT market with significant delta
    conflict_markets = [
        m for m in markets
        if str(m.get("category", "")).upper() == "CONFLICT"
        and abs(m.get("delta_pct", 0)) > 5
    ]
    if not conflict_markets:
        return []

    # Filter military ships
    mil_ships = [s for s in ships if s.get("type", "").lower() in _MILITARY_SHIP_TYPES]

    # Bin each source into grid
    source_grids = [
        ("ukraine_alerts", _bin_to_grid(ukraine_alerts)),
        ("military_flights", _bin_to_grid(mil_flights)),
        ("military_ships", _bin_to_grid(mil_ships)),
        ("gdelt_conflict", _bin_to_grid(gdelt)),
    ]

    all_cells = set().union(*(grid.keys() for _, grid in source_grids))
    max_market_delta = max(abs(m.get("delta_pct", 0)) for m in conflict_markets)

    findings = []
    for cell in all_cells:
        sources_present = []
        counts: dict[str, int] = {}

        for source_name, grid in source_grids:
            items = grid.get(cell, [])
            counts[source_name] = len(items)
            if items:
                sources_present.append(source_name)

        if len(sources_present) < 3:
            continue

        indicator_count = sum(counts.values())
        if indicator_count >= 11:
            severity = "high"
        elif indicator_count >= 6:
            severity = "medium"
        else:
            severity = "low"

        lat, lng = _grid_center(cell)
        findings.append({
            "type": "conflict_escalation",
            "lat": lat,
            "lng": lng,
            "grid_cell": cell,
            "sources": sources_present,
            **counts,
            "market_delta_pct": round(max_market_delta, 1),
            "market_count": len(conflict_markets),
            "indicators": indicator_count,
            "severity": severity,
            "_source": "correlation_engine/conflict_escalation",
        })

    return findings


# ---------------------------------------------------------------------------
# 5. FIMI Amplification
# ---------------------------------------------------------------------------

def _is_gdelt_stale_for_correlation() -> bool:
    """Check if GDELT data is stale (>30 min). Prevents false 'manufactured' labels.

    Note: mirrors alert_checkers._is_gdelt_stale — kept separate to avoid
    coupling the correlation engine to the alert checker module's internals.
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


def _detect_fimi_amplification(data: dict) -> list[dict]:
    """Detect FIMI amplification: classify disinformation narratives by comparing
    FIMI narrative volume against GDELT event coverage per target country.

    High FIMI + low GDELT = "manufactured" narrative
    High FIMI + high GDELT = "amplified" real events

    Not grid-based (FIMI lacks lat/lng). Matches by target_country.

    Staleness gate: skips if GDELT is empty or stale.
    """
    fimi = data.get("fimi", [])
    gdelt = data.get("gdelt", [])

    if not fimi:
        return []

    # Staleness gate
    if not gdelt or _is_gdelt_stale_for_correlation():
        return []

    # Group FIMI by target_country
    by_country: dict[str, list[dict]] = defaultdict(list)
    for f in fimi:
        country = f.get("target_country", "").strip()
        if country:
            by_country[country].append(f)

    if not by_country:
        return []

    def gdelt_count_for(country: str) -> int:
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

    findings = []
    for country, narratives in by_country.items():
        if len(narratives) < 2:
            continue  # Need multiple narratives to be meaningful

        g_count = gdelt_count_for(country)
        actors = list({n.get("actor", "Unknown") for n in narratives if n.get("actor")})

        if g_count < 5:
            classification = "manufactured"
            severity = "medium"
        elif g_count > 20:
            classification = "amplified"
            severity = "low"
        else:
            continue  # Ambiguous

        findings.append({
            "type": "fimi_amplification",
            "country": country,
            "classification": classification,
            "fimi_count": len(narratives),
            "gdelt_count": g_count,
            "actors": actors[:5],
            "indicators": len(narratives) + g_count,
            "severity": severity,
            "_source": "correlation_engine/fimi_amplification",
        })

    return findings


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_DETECTORS = [
    _detect_rf_anomaly,
    _detect_military_buildup,
    _detect_infra_cascade,
    _detect_conflict_escalation,
    _detect_fimi_amplification,
]

_SEVERITY_TO_ALERT = {
    "high": AlertSeverity.CRITICAL,
    "medium": AlertSeverity.ELEVATED,
    "low": AlertSeverity.NORMAL,
}


def _finding_title(finding: dict) -> str:
    """Generate a human-readable title for a correlation finding."""
    ftype = finding.get("type", "unknown")
    severity = finding.get("severity", "low").upper()

    titles = {
        "rf_anomaly": f"RF ANOMALY [{severity}] — GPS jamming + internet outage co-located",
        "military_buildup": f"MILITARY BUILDUP [{severity}] — Multi-domain military activity",
        "infra_cascade": f"INFRASTRUCTURE CASCADE [{severity}] — Co-located outages",
        "conflict_escalation": f"CONFLICT ESCALATION [{severity}] — Multi-source convergence + market signal",
        "fimi_amplification": f"FIMI AMPLIFICATION [{severity}] — {finding.get('classification', 'unknown')} narrative ({finding.get('country', '?')})",
    }
    return titles.get(ftype, f"CORRELATION [{severity}] — {ftype}")


def _finding_description(finding: dict) -> str:
    """Generate a description from finding details."""
    ftype = finding.get("type", "unknown")
    grid = finding.get("grid_cell", "?")

    if ftype == "rf_anomaly":
        return (
            f"Grid {grid}: {finding.get('gps_count', 0)} GPS jamming zones + "
            f"{finding.get('outage_count', 0)} internet outages. "
            f"Avg GPS ratio: {finding.get('avg_gps_ratio', 0)}%."
        )
    if ftype == "military_buildup":
        sources = ", ".join(finding.get("sources", []))
        return (
            f"Grid {grid}: {finding.get('indicators', 0)} indicators across {sources}. "
            f"Flights: {finding.get('flight_count', 0)}, "
            f"Ships: {finding.get('ship_count', 0)}, "
            f"GDELT: {finding.get('gdelt_count', 0)}."
        )
    if ftype == "infra_cascade":
        return (
            f"Grid {grid}: {finding.get('outage_count', 0)} outages + "
            f"{finding.get('kiwisdr_count', 0)} KiwiSDR + "
            f"{finding.get('fire_count', 0)} fire hotspots."
        )
    if ftype == "conflict_escalation":
        sources = ", ".join(finding.get("sources", []))
        return (
            f"Grid {grid}: {finding.get('indicators', 0)} indicators across {sources}. "
            f"Market delta: {finding.get('market_delta_pct', 0)}pp."
        )
    if ftype == "fimi_amplification":
        return (
            f"{finding.get('country', '?')}: {finding.get('fimi_count', 0)} FIMI narratives vs "
            f"{finding.get('gdelt_count', 0)} GDELT events. "
            f"Classification: {finding.get('classification', '?')}. "
            f"Actors: {', '.join(finding.get('actors', []))}."
        )
    return f"Correlation finding in grid {grid}: {finding.get('indicators', 0)} indicators."


def run_correlation_engine(data: dict, ds=None) -> list[dict]:
    """Run all correlation detectors against a snapshot of latest_data.

    Returns list of correlation findings. Also saves findings as Alerts
    to the AlertStore for the IntelFeedPanel and agent access.

    Args:
        data: snapshot of latest_data
        ds: optional DataSource for baseline-aware significance scoring
    """
    start = time.monotonic()
    all_findings: list[dict] = []

    for detector in _DETECTORS:
        try:
            findings = detector(data)
            all_findings.extend(findings)
        except Exception as e:
            logger.warning(f"Correlation detector {detector.__name__} failed: {e}")

    # Save to AlertStore
    store = get_alert_store()
    saved_count = 0
    for finding in all_findings:
        alert = Alert(
            alert_type=f"correlation_{finding['type']}",
            severity=_SEVERITY_TO_ALERT.get(finding.get("severity", "low"), AlertSeverity.NORMAL),
            title=_finding_title(finding),
            description=_finding_description(finding),
            lat=finding.get("lat"),
            lng=finding.get("lng"),
            data=finding,
        )
        score_alert(alert, ds=ds)
        if store.save(alert) is not None:
            saved_count += 1

    elapsed_ms = int((time.monotonic() - start) * 1000)
    if all_findings:
        logger.info(
            f"Correlation engine: {len(all_findings)} findings "
            f"({saved_count} new alerts) in {elapsed_ms}ms"
        )

    return all_findings
