"""Synthetic data builders for calibration tests.

Each builder produces a list of correctly-shaped dicts matching the
production data format for a single feed type. Entities are scattered
deterministically within ``spread_km`` of ``center``.
"""
from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import cycle
from typing import Any


# ── Geo helpers ─────────────────────────────────────────────────────

def _seeded_rng(region: str, scenario: str, feed: str) -> random.Random:
    """Deterministic RNG per (region, scenario, feed) for reproducibility."""
    seed = hashlib.md5(f"{region}:{scenario}:{feed}".encode()).hexdigest()
    return random.Random(seed)


def _scatter(
    center: tuple[float, float],
    count: int,
    spread_km: float,
    rng: random.Random,
) -> list[tuple[float, float]]:
    """Generate ``count`` (lat, lng) points within ``spread_km`` of center."""
    lat_deg = spread_km / 111.0
    lng_deg = spread_km / (111.0 * max(math.cos(math.radians(center[0])), 0.1))
    return [
        (
            center[0] + rng.uniform(-lat_deg, lat_deg),
            center[1] + rng.uniform(-lng_deg, lng_deg),
        )
        for _ in range(count)
    ]


@dataclass
class _GeoContext:
    """Pre-computed scatter points + RNG for a geographic builder."""
    rng: random.Random
    points: list[tuple[float, float]]


def _geo_setup(
    count: int,
    center: tuple[float, float],
    spread_km: float,
    region: str,
    scenario: str,
    feed: str,
) -> _GeoContext:
    """Common setup shared by all geographic builders."""
    rng = _seeded_rng(region, scenario, feed)
    points = _scatter(center, count, spread_km, rng)
    return _GeoContext(rng=rng, points=points)


def _cycle_values(**named_lists: list[Any]) -> dict[str, cycle]:
    """Create named cycles from keyword arguments."""
    return {name: cycle(values) for name, values in named_lists.items()}


# ── Military Flights ────────────────────────────────────────────────

def build_military_flights(
    count: int,
    center: tuple[float, float],
    *,
    countries: list[str] | None = None,
    military_types: list[str] | None = None,
    models: list[str] | None = None,
    altitudes: list[float] | None = None,
    callsign_prefix: str = "MIL",
    spread_km: float = 100.0,
    region: str = "",
    scenario: str = "",
) -> list[dict]:
    geo = _geo_setup(count, center, spread_km, region, scenario, "military_flights")
    c = _cycle_values(
        country=countries or ["United States"],
        mtype=military_types or ["fighter"],
        model=models or ["F-16C"],
        alt=altitudes or [10000.0],
    )
    rng = geo.rng
    return [
        {
            "callsign": f"{callsign_prefix}{i + 1:02d}",
            "country": next(c["country"]),
            "lat": round(lat, 4),
            "lng": round(lng, 4),
            "alt": next(c["alt"]),
            "heading": rng.randint(0, 359),
            "type": "military_flight",
            "military_type": next(c["mtype"]),
            "model": next(c["model"]),
            "icao24": f"a{rng.randint(10000, 99999):05x}",
            "speed_knots": round(rng.uniform(200, 600), 1),
            "registration": "N/A",
            "origin_loc": None,
            "dest_loc": None,
            "origin_name": "",
            "dest_name": "",
            "squawk": "",
            "force": "",
        }
        for i, (lat, lng) in enumerate(geo.points)
    ]


# ── Ships ───────────────────────────────────────────────────────────

def build_ships(
    count: int,
    center: tuple[float, float],
    *,
    ship_types: list[str] | None = None,
    countries: list[str] | None = None,
    destinations: list[str] | None = None,
    spread_km: float = 150.0,
    region: str = "",
    scenario: str = "",
) -> list[dict]:
    geo = _geo_setup(count, center, spread_km, region, scenario, "ships")
    c = _cycle_values(
        stype=ship_types or ["cargo"],
        country=countries or ["Panama"],
        dest=destinations or ["FUJAIRAH"],
    )
    rng = geo.rng
    return [
        {
            "mmsi": f"2{rng.randint(10000000, 99999999)}",
            "name": f"VESSEL-{i + 1:03d}",
            "type": next(c["stype"]),
            "lat": round(lat, 4),
            "lng": round(lng, 4),
            "heading": rng.randint(0, 359),
            "sog": round(rng.uniform(5, 15), 1),
            "cog": rng.randint(0, 359),
            "callsign": f"V{rng.randint(100, 999)}",
            "destination": next(c["dest"]),
            "imo": 0,
            "country": next(c["country"]),
        }
        for i, (lat, lng) in enumerate(geo.points)
    ]


# ── GDELT ───────────────────────────────────────────────────────────

def build_gdelt(
    count: int,
    center: tuple[float, float],
    *,
    events_per_feature: int = 5,
    country_code: str = "IR",
    geo_name: str = "Tehran, Iran",
    event_root_codes: list[str] | None = None,
    headlines: list[str] | None = None,
    as_geojson: bool = True,
    spread_km: float = 200.0,
    region: str = "",
    scenario: str = "",
) -> list[dict]:
    geo = _geo_setup(count, center, spread_km, region, scenario, "gdelt")
    headlines = headlines or [f"Event in {geo_name}"]
    code_cycle = cycle(event_root_codes or ["18"])
    items: list[dict] = []
    for lat, lng in geo.points:
        code = next(code_cycle)
        if as_geojson:
            items.append({
                "type": "Feature",
                "properties": {
                    "name": geo_name,
                    "count": events_per_feature,
                    "action_geo_cc": country_code,
                    "_headlines_list": list(headlines),
                    "event_root_code": code,
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [round(lng, 4), round(lat, 4)],
                },
            })
        else:
            items.append({
                "lat": round(lat, 4),
                "lon": round(lng, 4),
                "action_geo": geo_name,
                "action_geo_cc": country_code,
                "event_root_code": code,
                "count": events_per_feature,
            })
    return items


# ── GPS Jamming ─────────────────────────────────────────────────────

def build_gps_jamming(
    count: int,
    center: tuple[float, float],
    *,
    severities: list[str] | None = None,
    ratios: list[float] | None = None,
    spread_km: float = 100.0,
    region: str = "",
    scenario: str = "",
) -> list[dict]:
    geo = _geo_setup(count, center, spread_km, region, scenario, "gps_jamming")
    c = _cycle_values(
        sev=severities or ["medium"],
        ratio=ratios or [0.5],
    )
    rng = geo.rng
    items: list[dict] = []
    for lat, lng in geo.points:
        r = next(c["ratio"])
        total = rng.randint(10, 30)
        items.append({
            "lat": round(lat, 4),
            "lng": round(lng, 4),
            "severity": next(c["sev"]),
            "ratio": r,
            "degraded": int(total * r),
            "total": total,
        })
    return items


# ── Internet Outages ────────────────────────────────────────────────

def build_internet_outages(
    count: int,
    center: tuple[float, float],
    *,
    severities: list[int] | None = None,
    country_codes: list[str] | None = None,
    country_names: list[str] | None = None,
    region_names: list[str] | None = None,
    spread_km: float = 150.0,
    region: str = "",
    scenario: str = "",
) -> list[dict]:
    country_codes = country_codes or ["XX"]
    geo = _geo_setup(count, center, spread_km, region, scenario, "internet_outages")
    c = _cycle_values(
        sev=severities or [50],
        cc=country_codes,
        cn=country_names or ["Unknown"],
        rn=region_names or ["Region-1"],
    )
    items: list[dict] = []
    for i, (lat, lng) in enumerate(geo.points):
        s = next(c["sev"])
        items.append({
            "region_code": f"{next(c['cc'])}-{i + 1:02d}",
            "region_name": next(c["rn"]),
            "country_code": country_codes[i % len(country_codes)],
            "country_name": next(c["cn"]),
            "level": "critical" if s >= 60 else "warning",
            "datasource": "bgp",
            "severity": s,
            "lat": round(lat, 4),
            "lng": round(lng, 4),
        })
    return items


# ── News ────────────────────────────────────────────────────────────

def build_news(
    count: int,
    center: tuple[float, float],
    *,
    titles: list[str] | None = None,
    risk_scores: list[int] | None = None,
    descriptions: list[str] | None = None,
    spread_km: float = 200.0,
    region: str = "",
    scenario: str = "",
) -> list[dict]:
    geo = _geo_setup(count, center, spread_km, region, scenario, "news")
    c = _cycle_values(
        title=titles or ["Regional news update"],
        risk=risk_scores or [3],
        desc=descriptions or [""],
    )
    return [
        {
            "title": next(c["title"]),
            "link": f"https://example.com/news-{i + 1}",
            "published": datetime.now(timezone.utc).isoformat(),
            "source": "TestSource",
            "risk_score": next(c["risk"]),
            "coords": [round(lat, 4), round(lng, 4)],
            "description": next(c["desc"]),
            "cluster_count": 1,
            "articles": [],
            "machine_assessment": None,
        }
        for i, (lat, lng) in enumerate(geo.points)
    ]


# ── Earthquakes ─────────────────────────────────────────────────────

def build_earthquakes(
    count: int,
    center: tuple[float, float],
    *,
    magnitudes: list[float] | None = None,
    places: list[str] | None = None,
    spread_km: float = 50.0,
    region: str = "",
    scenario: str = "",
) -> list[dict]:
    geo = _geo_setup(count, center, spread_km, region, scenario, "earthquakes")
    c = _cycle_values(
        mag=magnitudes or [3.0],
        place=places or ["Test location"],
    )
    rng = geo.rng
    return [
        {
            "id": f"eq{rng.randint(100000, 999999)}",
            "mag": next(c["mag"]),
            "lat": round(lat, 4),
            "lng": round(lng, 4),
            "place": next(c["place"]),
        }
        for i, (lat, lng) in enumerate(geo.points)
    ]


# ── Fires (FIRMS) ──────────────────────────────────────────────────

def build_fires(
    count: int,
    center: tuple[float, float],
    *,
    frps: list[float] | None = None,
    confidences: list[str] | None = None,
    spread_km: float = 100.0,
    region: str = "",
    scenario: str = "",
) -> list[dict]:
    geo = _geo_setup(count, center, spread_km, region, scenario, "fires")
    c = _cycle_values(
        frp=frps or [20.0],
        conf=confidences or ["nominal"],
    )
    rng = geo.rng
    return [
        {
            "lat": round(lat, 4),
            "lng": round(lng, 4),
            "frp": next(c["frp"]),
            "brightness": round(rng.uniform(300, 400), 1),
            "confidence": next(c["conf"]),
            "daynight": "D",
            "acq_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "acq_time": "0800",
        }
        for lat, lng in geo.points
    ]


# ── Prediction Markets ─────────────────────────────────────────────

def build_prediction_markets(
    count: int,
    *,
    titles: list[str] | None = None,
    categories: list[str] | None = None,
    delta_pcts: list[float] | None = None,
    consensus_pcts: list[float] | None = None,
) -> list[dict]:
    """Markets are non-geographic -- no center/spread needed."""
    c = _cycle_values(
        title=titles or ["Test market"],
        cat=categories or ["POLITICS"],
        delta=delta_pcts or [0.0],
        cons=consensus_pcts or [50.0],
    )
    return [
        {
            "title": next(c["title"]),
            "consensus_pct": next(c["cons"]),
            "category": next(c["cat"]),
            "delta_pct": next(c["delta"]),
            "volume": 500000.0,
            "volume_24h": 10000.0,
            "kalshi_volume": 5000,
            "polymarket_pct": None,
            "kalshi_pct": None,
            "description": "",
            "end_date": None,
            "sources": [],
            "slug": f"test-market-{i + 1}",
            "kalshi_ticker": "",
            "outcomes": [],
            "_source": "prediction_markets",
        }
        for i in range(count)
    ]


# ── Ukraine Alerts ──────────────────────────────────────────────────

def build_ukraine_alerts(
    count: int,
    center: tuple[float, float],
    *,
    alert_types: list[str] | None = None,
    spread_km: float = 100.0,
    region: str = "",
    scenario: str = "",
) -> list[dict]:
    geo = _geo_setup(count, center, spread_km, region, scenario, "ukraine_alerts")
    type_cycle = cycle(alert_types or ["air_raid"])
    rng = geo.rng
    return [
        {
            "id": rng.randint(10000, 99999),
            "alert_type": next(type_cycle),
            "location_title": f"Oblast-{i + 1}",
            "location_uid": f"uid-{i + 1}",
            "name_en": f"Region-{i + 1}",
            "lat": round(lat, 4),
            "lng": round(lng, 4),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "color": "#ef4444",
            "_source": "ukraine_alerts",
        }
        for i, (lat, lng) in enumerate(geo.points)
    ]


# ── FIMI (Disinformation) ──────────────────────────────────────────

def build_fimi(
    count: int,
    center: tuple[float, float],
    *,
    target_countries: list[str] | None = None,
    actors: list[str] | None = None,
    is_major_wave: bool = False,
    spread_km: float = 300.0,
    region: str = "",
    scenario: str = "",
) -> list[dict]:
    geo = _geo_setup(count, center, spread_km, region, scenario, "fimi")
    c = _cycle_values(
        tc=target_countries or ["Unknown"],
        actor=actors or ["Unknown"],
    )
    rng = geo.rng
    items: list[dict] = []
    for i, (lat, lng) in enumerate(geo.points):
        tc = next(c["tc"])
        actor = next(c["actor"])
        items.append({
            "id": f"fimi-{rng.randint(100000, 999999)}-{tc.lower().replace(' ', '-')}",
            "title": f"Narrative targeting {tc}",
            "description": f"Disinformation campaign by {actor}",
            "link": f"https://euvsdisinfo.eu/test-{i + 1}",
            "pub_date": datetime.now(timezone.utc).isoformat(),
            "threat_actors": [actor],
            "target_countries": [tc],
            "primary_actor": actor,
            "color": "#e53e3e",
            "target_country": tc,
            "lat": round(lat, 4),
            "lng": round(lng, 4),
            "is_major_wave": is_major_wave,
            "_source": "fimi",
        })
    return items


# ── Trains ──────────────────────────────────────────────────────────

def build_trains(
    count: int,
    center: tuple[float, float],
    *,
    operators: list[str] | None = None,
    speeds: list[int] | None = None,
    statuses: list[str] | None = None,
    spread_km: float = 200.0,
    region: str = "",
    scenario: str = "",
) -> list[dict]:
    geo = _geo_setup(count, center, spread_km, region, scenario, "trains")
    c = _cycle_values(
        op=operators or ["Amtrak"],
        speed=speeds or [80],
        status=statuses or ["Active"],
    )
    rng = geo.rng
    items: list[dict] = []
    for i, (lat, lng) in enumerate(geo.points):
        op = next(c["op"])
        items.append({
            "id": f"train-{op.lower()}-{i + 1}",
            "name": f"Train {i + 1}",
            "train_num": str(100 + i),
            "operator": op,
            "country": "US" if op == "Amtrak" else "FI",
            "lat": round(lat, 4),
            "lng": round(lng, 4),
            "speed": next(c["speed"]),
            "heading": rng.randint(0, 359),
            "status": next(c["status"]),
            "origin": "Origin City",
            "destination": "Destination City",
            "stations_left": rng.randint(1, 20),
            "_source": "trains",
        })
    return items


# ── Commercial Flights ──────────────────────────────────────────────

def build_flights_commercial(
    count: int,
    center: tuple[float, float],
    *,
    is_notable: bool = False,
    military_type: str | None = None,
    altitudes: list[float] | None = None,
    spread_km: float = 200.0,
    region: str = "",
    scenario: str = "",
) -> list[dict]:
    geo = _geo_setup(count, center, spread_km, region, scenario, "flights")
    alt_cycle = cycle(altitudes or [10000.0])
    rng = geo.rng
    return [
        {
            "callsign": f"UAL{100 + i}",
            "country": f"N{rng.randint(10000, 99999)}",
            "lng": round(lng, 4),
            "lat": round(lat, 4),
            "alt": next(alt_cycle),
            "heading": rng.randint(0, 359),
            "type": "commercial_flight",
            "origin_loc": None,
            "dest_loc": None,
            "origin_name": "",
            "dest_name": "",
            "registration": f"N{rng.randint(10000, 99999)}",
            "model": "B738",
            "icao24": f"a{rng.randint(10000, 99999):05x}",
            "speed_knots": round(rng.uniform(400, 500), 1),
            "squawk": "",
            "is_notable": is_notable,
            "military_type": military_type,
            "notable_reason": "Test VIP" if is_notable else None,
        }
        for i, (lat, lng) in enumerate(geo.points)
    ]
