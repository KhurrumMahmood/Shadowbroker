"""Anomaly detection tools for the agent system.

Scans data categories for statistical anomalies and behavioral patterns.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.agent.datasource import DataSource

_SUSPICIOUS_DESTINATIONS = {"", "for orders", "unknown", "none", "tbd", "tba"}


def anomaly_scan(
    ds: DataSource,
    categories: list[str] | None = None,
) -> dict:
    """Scan categories for count anomalies against baselines.

    Returns {category: {count, baseline_mean, baseline_std, z_score, anomaly_level}}.
    """
    cats = categories or ds.categories()
    result: dict = {}

    for cat in cats:
        items = ds.query(cat, limit=10000)
        count = len(items)

        baseline = ds.get_baseline(f"{cat}_count")
        if baseline is None or baseline.n < 3:
            result[cat] = {
                "count": count,
                "baseline_mean": None,
                "baseline_std": None,
                "z_score": None,
                "anomaly_level": "unknown",
            }
            continue

        if baseline.std < 1e-10:
            z = 0.0 if abs(count - baseline.mean) < 1e-10 else float("inf")
        else:
            z = (count - baseline.mean) / baseline.std

        if abs(z) > 3:
            level = "critical"
        elif abs(z) > 2:
            level = "elevated"
        elif abs(z) > 1:
            level = "notable"
        else:
            level = "normal"

        result[cat] = {
            "count": count,
            "baseline_mean": round(baseline.mean, 1),
            "baseline_std": round(baseline.std, 2),
            "z_score": round(z, 2),
            "anomaly_level": level,
        }

    return result


def pattern_detect(
    ds: DataSource,
    category: str,
    pattern_type: str,
) -> dict:
    """Detect behavioral patterns in entity data.

    Pattern types:
      - dark_vessel: ships with blank/suspicious destinations or very low speed
      - holding_pattern: entities with very low speed (potential loitering)
    """
    items = ds.query(category, limit=10000)

    if pattern_type == "dark_vessel":
        flagged = _detect_dark_vessels(items)
    elif pattern_type == "holding_pattern":
        flagged = _detect_holding_pattern(items)
    else:
        return {"pattern_type": pattern_type, "flagged": [], "count": 0}

    return {
        "pattern_type": pattern_type,
        "flagged": flagged,
        "count": len(flagged),
    }


def _detect_dark_vessels(items: list[dict]) -> list[dict]:
    """Flag vessels with suspicious destinations or very low speed."""
    flagged = []
    for item in items:
        dest = (item.get("destination") or "").strip().lower()
        sog = item.get("sog")
        reasons = []
        if dest in _SUSPICIOUS_DESTINATIONS:
            reasons.append(f"suspicious_destination:{dest or 'empty'}")
        if sog is not None and float(sog) < 1.0:
            reasons.append(f"near_stationary:sog={sog}")
        if reasons:
            flagged.append({**item, "_flag_reasons": reasons})
    return flagged


def _detect_holding_pattern(items: list[dict]) -> list[dict]:
    """Flag entities with very low speed (potential loitering/holding)."""
    flagged = []
    for item in items:
        speed = item.get("sog") or item.get("speed") or item.get("velocity")
        if speed is not None and float(speed) < 2.0:
            flagged.append({**item, "_flag_reasons": [f"low_speed:{speed}"]})
    return flagged
