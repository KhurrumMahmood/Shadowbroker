"""Scenario composers -- assemble synthetic data dicts from builders.

Each ``compose_*`` function returns a dict structured like ``latest_data``
from ``_store.py``, ready for ``InMemoryDataSource(data)`` or raw-dict
consumers (correlation detectors, post-processing).
"""
from __future__ import annotations

from typing import Callable

from tests.calibration.builders import (
    build_earthquakes,
    build_fimi,
    build_fires,
    build_flights_commercial,
    build_gdelt,
    build_gps_jamming,
    build_internet_outages,
    build_military_flights,
    build_news,
    build_prediction_markets,
    build_ships,
    build_trains,
    build_ukraine_alerts,
)


# ── Region definitions ──────────────────────────────────────────────

REGIONS: dict[str, dict] = {
    "persian_gulf": {
        "center": (26.5, 56.3),
        "bbox": (24, 28, 54, 58),
    },
    "black_sea": {
        "center": (45.5, 36.0),
        "bbox": (43, 48, 30, 42),
    },
    "taiwan_strait": {
        "center": (24.5, 119.5),
        "bbox": (22, 26, 118, 123),
    },
    "us_east_coast": {
        "center": (40.0, -74.0),
        "bbox": (38, 42, -76, -72),
    },
    "finland_baltic": {
        "center": (62.0, 26.0),
        "bbox": (60, 65, 24, 28),
    },
    "sub_saharan_africa": {
        "center": (5.0, 35.0),
        "bbox": (-5, 10, 25, 45),
    },
}


def _empty_store() -> dict:
    """Baseline data dict with all keys present as empty lists/None."""
    return {
        "last_updated": None,
        "news": [],
        "stocks": {},
        "oil": {},
        "flights": [],
        "ships": [],
        "military_flights": [],
        "tracked_flights": [],
        "cctv": [],
        "weather": None,
        "earthquakes": [],
        "uavs": [],
        "frontlines": None,
        "gdelt": [],
        "liveuamap": [],
        "kiwisdr": [],
        "space_weather": None,
        "internet_outages": [],
        "firms_fires": [],
        "gps_jamming": [],
        "datacenters": [],
        "military_bases": [],
        "power_plants": [],
        "coverage_gaps": [],
        "correlations": [],
        "disease_outbreaks": [],
        "prediction_markets": [],
        "trending_markets": [],
        "ukraine_alerts": [],
        "fimi": [],
        "trains": [],
        "meshtastic": [],
        "correlation_alerts": [],
    }


def _region_ctx(region: str) -> tuple[tuple[float, float], str]:
    """Return (center, region_name) for use in scenario composers."""
    return REGIONS[region]["center"], region


# ════════════════════════════════════════════════════════════════════
#  SCENARIO REGISTRY
# ════════════════════════════════════════════════════════════════════

_SCENARIOS: dict[tuple[str, str], Callable[[], dict]] = {}


def compose_scenario(region: str, scenario_type: str) -> dict:
    """Build a full data dict for the given (region, scenario_type)."""
    key = (region, scenario_type)
    if key not in _SCENARIOS:
        raise KeyError(f"No scenario registered for {key}")
    return _SCENARIOS[key]()


def _register(region: str, scenario_type: str):
    """Decorator to register a scenario composer function."""
    def wrapper(fn):
        _SCENARIOS[(region, scenario_type)] = fn
        return fn
    return wrapper


# ════════════════════════════════════════════════════════════════════
#  PERSIAN GULF SCENARIOS
# ════════════════════════════════════════════════════════════════════

@_register("persian_gulf", "normal")
def _persian_gulf_normal() -> dict:
    """Routine peacetime: single-country patrol, commercial shipping."""
    c, r = _region_ctx("persian_gulf")
    s = "normal"
    data = _empty_store()
    data["military_flights"] = build_military_flights(
        3, c, countries=["United States"], military_types=["fighter", "recon"],
        models=["F/A-18E", "P-8A"], region=r, scenario=s,
    )
    data["ships"] = build_ships(
        8, c, ship_types=["tanker", "cargo"], countries=["Panama", "Liberia", "Marshall Islands"],
        destinations=["FUJAIRAH", "JEBEL ALI", "RAS TANURA"], region=r, scenario=s,
    )
    data["gdelt"] = build_gdelt(
        5, c, events_per_feature=1, country_code="IR",
        geo_name="Tehran, Iran", region=r, scenario=s,
    )
    data["news"] = build_news(
        5, c, titles=["Gulf shipping update", "Oil market report"],
        risk_scores=[2, 3], region=r, scenario=s,
    )
    return data


@_register("persian_gulf", "hormuz_crisis")
def _persian_gulf_hormuz_crisis() -> dict:
    """GPS jamming, military convergence, sanctions evasion near Hormuz."""
    c, r = _region_ctx("persian_gulf")
    s = "hormuz_crisis"
    data = _empty_store()

    # 3 countries converging within 200km
    data["military_flights"] = build_military_flights(
        6, c, countries=["United States", "Iran", "United Kingdom"],
        military_types=["fighter", "recon"], models=["F/A-18E", "Su-24", "Typhoon"],
        spread_km=80, region=r, scenario=s,
    )
    # Tankers with suspicious destinations in Iran sanctioned zone
    data["ships"] = (
        build_ships(
            4, c, ship_types=["tanker"], countries=["Iran", "Panama"],
            destinations=["", "FOR ORDERS"], spread_km=100, region=r, scenario=s,
        )
        + build_ships(
            4, c, ship_types=["cargo"], countries=["Liberia"],
            destinations=["FUJAIRAH"], spread_km=150, region=r, scenario=s + "_legit",
        )
    )
    # GPS jamming near Hormuz
    data["gps_jamming"] = build_gps_jamming(
        3, c, severities=["high", "medium"], ratios=[0.8, 0.6],
        spread_km=80, region=r, scenario=s,
    )
    # Internet outages
    data["internet_outages"] = build_internet_outages(
        3, c, severities=[70, 60, 50], country_codes=["IR", "AE", "OM"],
        country_names=["Iran", "UAE", "Oman"], region_names=["Bandar Abbas", "Dubai", "Muscat"],
        spread_km=150, region=r, scenario=s,
    )
    # GDELT events
    data["gdelt"] = build_gdelt(
        15, c, events_per_feature=1, country_code="IR",
        geo_name="Bandar Abbas, Iran", event_root_codes=["18", "19"],
        headlines=["Iran seizes tanker", "Naval standoff in Hormuz"],
        spread_km=150, region=r, scenario=s,
    )
    # Few news articles (under-reported)
    data["news"] = build_news(
        3, c, titles=["Tensions in the Gulf"],
        risk_scores=[8], region=r, scenario=s,
    )
    return data


# ════════════════════════════════════════════════════════════════════
#  BLACK SEA SCENARIOS
# ════════════════════════════════════════════════════════════════════

@_register("black_sea", "normal")
def _black_sea_normal() -> dict:
    """Peacetime: NATO patrol, commercial shipping, low GDELT."""
    c, r = _region_ctx("black_sea")
    s = "normal"
    data = _empty_store()
    # 2 NATO countries patrolling — should trigger #1 at ELEVATED
    data["military_flights"] = build_military_flights(
        2, c, countries=["United States", "Turkey"],
        military_types=["fighter", "recon"], models=["F-16C", "P-8A"],
        spread_km=80, region=r, scenario=s,
    )
    data["ships"] = build_ships(
        5, c, ship_types=["cargo", "tanker"], countries=["Turkey", "Romania"],
        destinations=["ISTANBUL", "CONSTANTA"], region=r, scenario=s,
    )
    data["gdelt"] = build_gdelt(
        4, c, events_per_feature=1, country_code="UA",
        geo_name="Kyiv, Ukraine", region=r, scenario=s,
    )
    data["news"] = build_news(
        3, c, titles=["Ukraine diplomatic update"],
        risk_scores=[3], region=r, scenario=s,
    )
    # FIMI present but NOT major_wave
    data["fimi"] = build_fimi(
        1, c, target_countries=["Ukraine"], actors=["Russia"],
        is_major_wave=False, region=r, scenario=s,
    )
    # Stable prediction markets
    data["prediction_markets"] = build_prediction_markets(
        1, titles=["Will Ukraine ceasefire hold?"],
        categories=["CONFLICT"], delta_pcts=[2.0], consensus_pcts=[45.0],
    )
    return data


@_register("black_sea", "escalation")
def _black_sea_escalation() -> dict:
    """Full escalation: air raids, military convergence, FIMI, markets."""
    c, r = _region_ctx("black_sea")
    s = "escalation"
    data = _empty_store()

    # 3 air raids inside Black Sea bbox — centered near zone center for grid co-location
    data["ukraine_alerts"] = build_ukraine_alerts(
        3, c,  # (45.5, 36.0) — Inside 43-48N, 30-42E
        alert_types=["air_raid"], spread_km=40, region=r, scenario=s,
    )
    # 6 military flights, 3 countries — tight spread for detector grid co-location
    data["military_flights"] = build_military_flights(
        6, c, countries=["United States", "Turkey", "United Kingdom"],
        military_types=["fighter", "recon", "cargo"],
        models=["F-16C", "P-8A", "C-17A"], spread_km=40, region=r, scenario=s,
    )
    # 3 military ships — tight spread for grid co-location
    data["ships"] = build_ships(
        3, c, ship_types=["destroyer", "frigate", "military"],
        countries=["Russia", "Turkey", "United States"],
        destinations=["SEVASTOPOL", "ISTANBUL", ""],
        spread_km=40, region=r, scenario=s,
    )
    # 25 GDELT conflict events for Ukraine
    data["gdelt"] = build_gdelt(
        25, c, events_per_feature=1, country_code="UA",
        geo_name="Odesa, Ukraine", event_root_codes=["18", "19", "20"],
        headlines=["Shelling in southern Ukraine", "Naval clash in Black Sea"],
        spread_km=150, region=r, scenario=s,
    )
    # Only 2 news articles (under-reported)
    data["news"] = build_news(
        2, c, titles=["Black Sea tensions rise"],
        risk_scores=[9], region=r, scenario=s,
    )
    # FIMI major wave
    data["fimi"] = build_fimi(
        3, c, target_countries=["Ukraine"], actors=["Russia"],
        is_major_wave=True, region=r, scenario=s,
    )
    # CONFLICT prediction market spiking
    data["prediction_markets"] = build_prediction_markets(
        1, titles=["Will Ukraine conflict escalate?"],
        categories=["CONFLICT"], delta_pcts=[15.0], consensus_pcts=[72.0],
    )
    return data


# ════════════════════════════════════════════════════════════════════
#  TAIWAN STRAIT SCENARIOS
# ════════════════════════════════════════════════════════════════════

@_register("taiwan_strait", "normal")
def _taiwan_strait_normal() -> dict:
    c, r = _region_ctx("taiwan_strait")
    s = "normal"
    data = _empty_store()
    data["military_flights"] = build_military_flights(
        2, c, countries=["United States", "Japan"],
        military_types=["recon", "fighter"], models=["P-8A", "F-15J"],
        spread_km=100, region=r, scenario=s,
    )
    data["ships"] = build_ships(
        6, c, ship_types=["cargo", "tanker"], countries=["Panama", "Singapore"],
        destinations=["KAOHSIUNG", "SHANGHAI"], region=r, scenario=s,
    )
    data["gdelt"] = build_gdelt(
        4, c, events_per_feature=1, country_code="TW",
        geo_name="Taipei, Taiwan", region=r, scenario=s,
    )
    data["news"] = build_news(
        4, c, titles=["Taiwan trade update"],
        risk_scores=[2], region=r, scenario=s,
    )
    data["prediction_markets"] = build_prediction_markets(
        1, titles=["Will China invade Taiwan?"],
        categories=["CONFLICT"], delta_pcts=[1.0], consensus_pcts=[12.0],
    )
    return data


@_register("taiwan_strait", "posture")
def _taiwan_strait_posture() -> dict:
    """PLA military surge + prediction market spike."""
    c, r = _region_ctx("taiwan_strait")
    s = "posture"
    data = _empty_store()
    data["military_flights"] = build_military_flights(
        8, c, countries=["China", "China", "China", "China", "China", "United States", "United States", "Japan"],
        military_types=["fighter", "bomber", "fighter", "fighter", "recon", "fighter", "recon", "fighter"],
        models=["J-16", "H-6K", "J-11B", "J-16", "KJ-500", "F/A-18E", "P-8A", "F-15J"],
        spread_km=40, region=r, scenario=s,
    )
    data["ships"] = build_ships(
        4, c, ship_types=["carrier", "destroyer", "cargo", "tanker"],
        countries=["China", "China", "Panama", "Liberia"],
        destinations=["", "NINGBO", "KAOHSIUNG", "SHANGHAI"],
        spread_km=40, region=r, scenario=s,
    )
    data["gdelt"] = build_gdelt(
        20, c, events_per_feature=1, country_code="TW",
        geo_name="Taiwan Strait", event_root_codes=["17", "18", "19"],
        headlines=["PLA exercises near Taiwan", "US carrier enters strait"],
        spread_km=100, region=r, scenario=s,
    )
    data["news"] = build_news(
        3, c, titles=["Taiwan tensions escalate"],
        risk_scores=[9], region=r, scenario=s,
    )
    data["prediction_markets"] = build_prediction_markets(
        1, titles=["Will China invade Taiwan?"],
        categories=["CONFLICT"], delta_pcts=[12.0], consensus_pcts=[35.0],
    )
    return data


# ════════════════════════════════════════════════════════════════════
#  US EAST COAST SCENARIOS
# ════════════════════════════════════════════════════════════════════

@_register("us_east_coast", "normal")
def _us_east_coast_normal() -> dict:
    c, r = _region_ctx("us_east_coast")
    s = "normal"
    data = _empty_store()
    data["trains"] = build_trains(
        5, c, operators=["Amtrak"], speeds=[80, 95, 70, 85, 60],
        statuses=["Active"], region=r, scenario=s,
    )
    data["flights"] = build_flights_commercial(
        2, c, is_notable=False, region=r, scenario=s,
    )
    return data


@_register("us_east_coast", "infrastructure_cascade")
def _us_east_coast_cascade() -> dict:
    """Earthquake + fires + outages + stopped trains + VIP flight."""
    c, r = _region_ctx("us_east_coast")
    s = "infrastructure_cascade"
    data = _empty_store()
    data["earthquakes"] = build_earthquakes(
        1, c, magnitudes=[5.5], places=["10km NW of New York City"],
        spread_km=10, region=r, scenario=s,
    )
    data["firms_fires"] = build_fires(
        4, c, frps=[30.0, 45.0, 25.0, 35.0], confidences=["high", "high", "nominal", "high"],
        spread_km=80, region=r, scenario=s,
    )
    data["internet_outages"] = build_internet_outages(
        2, c, severities=[75, 65], country_codes=["US", "US"],
        country_names=["United States", "United States"],
        region_names=["New York", "New Jersey"],
        spread_km=80, region=r, scenario=s,
    )
    data["trains"] = build_trains(
        4, c, operators=["Amtrak"], speeds=[0, 0, 0, 0],
        statuses=["Delayed", "Stopped", "Delayed", "Stopped"],
        spread_km=100, region=r, scenario=s,
    )
    # VIP flight
    data["military_flights"] = build_military_flights(
        1, c, countries=["United States"], military_types=["vip"],
        models=["C-32A"], altitudes=[12000.0], region=r, scenario=s,
    )
    data["flights"] = build_flights_commercial(
        1, c, is_notable=True, military_type="vip",
        altitudes=[11000.0], region=r, scenario=s,
    )
    return data


# ════════════════════════════════════════════════════════════════════
#  FINLAND / BALTIC SCENARIOS
# ════════════════════════════════════════════════════════════════════

@_register("finland_baltic", "normal")
def _finland_normal() -> dict:
    c, r = _region_ctx("finland_baltic")
    s = "normal"
    data = _empty_store()
    data["trains"] = build_trains(
        3, c, operators=["Finnish Railways"], speeds=[120, 100, 80],
        statuses=["Active"], region=r, scenario=s,
    )
    return data


@_register("finland_baltic", "supply_chain")
def _finland_supply_chain() -> dict:
    """Internet outages + stopped trains + fires."""
    _c, r = _region_ctx("finland_baltic")
    s = "supply_chain"
    # Offset center to avoid 1° grid boundary at lat 62.0
    grid_center = (62.5, 26.5)
    data = _empty_store()
    data["internet_outages"] = build_internet_outages(
        2, grid_center, severities=[65, 55], country_codes=["FI", "FI"],
        country_names=["Finland", "Finland"],
        region_names=["Helsinki", "Tampere"],
        spread_km=30, region=r, scenario=s,
    )
    data["trains"] = build_trains(
        3, grid_center, operators=["Finnish Railways"], speeds=[0, 0, 0],
        statuses=["Delayed", "Stopped", "Delayed"],
        spread_km=40, region=r, scenario=s,
    )
    data["firms_fires"] = build_fires(
        2, grid_center, frps=[20.0, 15.0], spread_km=30, region=r, scenario=s,
    )
    return data


# ════════════════════════════════════════════════════════════════════
#  SUB-SAHARAN AFRICA SCENARIOS
# ════════════════════════════════════════════════════════════════════

@_register("sub_saharan_africa", "normal")
def _africa_normal() -> dict:
    c, r = _region_ctx("sub_saharan_africa")
    s = "normal"
    data = _empty_store()
    data["gdelt"] = build_gdelt(
        8, c, events_per_feature=1, country_code="ET",
        geo_name="Addis Ababa, Ethiopia", region=r, scenario=s,
    )
    data["news"] = build_news(
        6, c, titles=["Ethiopia development report", "East Africa trade"],
        risk_scores=[2, 3], region=r, scenario=s,
    )
    data["fimi"] = build_fimi(
        2, c, target_countries=["Ethiopia"], actors=["Russia"],
        is_major_wave=False, region=r, scenario=s,
    )
    data["firms_fires"] = build_fires(
        2, c, frps=[10.0], confidences=["nominal"], region=r, scenario=s,
    )
    return data


@_register("sub_saharan_africa", "coverage_gap")
def _africa_coverage_gap() -> dict:
    """High GDELT, zero news, FIMI major wave -- coverage gap + disinfo."""
    c, r = _region_ctx("sub_saharan_africa")
    s = "coverage_gap"
    data = _empty_store()
    data["gdelt"] = build_gdelt(
        30, c, events_per_feature=1, country_code="ET",
        geo_name="Addis Ababa, Ethiopia", event_root_codes=["18", "19", "14"],
        headlines=["Conflict in Ethiopia", "Protests spread"],
        spread_km=150, region=r, scenario=s,
    )
    # Only 1 news article — severely under-reported
    data["news"] = build_news(
        1, c, titles=["Brief mention of Ethiopia"],
        risk_scores=[4], region=r, scenario=s,
    )
    data["fimi"] = build_fimi(
        3, c, target_countries=["Ethiopia"], actors=["Russia"],
        is_major_wave=True, region=r, scenario=s,
    )
    return data
