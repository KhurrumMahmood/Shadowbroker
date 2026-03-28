"""Dual-model significance scoring for alerts (EXP-024 + EXP-027).

Each alert is scored on two axes:
  - Signal (0-50): evidence the event is a genuine threat
  - Routine (0-50): evidence the event is normal/expected

Significance = signal - routine + 50, clamped to 0-100.

Scoring is a post-processing layer: checkers are NOT modified. The scoring
module reads each alert's `data` dict and computes sub-scores externally.

When BaselineStore has accumulated data (n >= 3), routine components
incorporate z-scores automatically. Until then, static calibration priors
from EXP-031 provide the routine model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from services.agent.alerts import Alert
    from services.agent.datasource import DataSource


# ── Scoring primitives ─────────────────────────────────────────────

@dataclass(frozen=True)
class ScoringComponent:
    """A signal sub-score extractor."""
    name: str
    weight: float
    extract: Callable[[dict], float]  # alert.data -> 0.0-1.0


@dataclass(frozen=True)
class RoutineComponent:
    """A routine sub-score extractor."""
    name: str
    weight: float
    extract: Callable[[dict, DataSource | None], float]  # (alert.data, ds) -> 0.0-1.0


@dataclass(frozen=True)
class SignalProfile:
    """Per-alert_type scoring configuration."""
    alert_type: str
    signal_components: list[ScoringComponent] = field(default_factory=list)
    routine_components: list[RoutineComponent] = field(default_factory=list)


# ── Combining function ─────────────────────────────────────────────

def combine_scores(
    signal_raw: float, routine_raw: float,
) -> tuple[int, float, float]:
    """Combine normalized signal/routine into significance.

    Args:
        signal_raw: 0.0-1.0 (weighted sum of signal components)
        routine_raw: 0.0-1.0 (weighted sum of routine components)

    Returns:
        (significance_0_100, signal_0_50, routine_0_50)
    """
    signal_50 = round(signal_raw * 50.0, 1)
    routine_50 = round(routine_raw * 50.0, 1)
    significance = max(0, min(100, round(signal_50 - routine_50 + 50)))
    return significance, signal_50, routine_50


def _weighted_average(components, data, ds=None) -> float:
    """Compute weighted average of component scores.

    If a component's extract raises or returns None, it contributes 0.
    Dispatches per-component: RoutineComponents get (data, ds), others get (data).
    """
    total_weight = 0.0
    total_score = 0.0

    for c in components:
        try:
            val = c.extract(data, ds) if isinstance(c, RoutineComponent) else c.extract(data)
            if val is None:
                continue
            val = max(0.0, min(1.0, float(val)))
            total_score += val * c.weight
            total_weight += c.weight
        except Exception:
            continue

    if total_weight < 1e-10:
        return 0.0
    return total_score / total_weight


# ── Derived severity ───────────────────────────────────────────────

def derive_severity(significance: int) -> AlertSeverity:
    """Map a 0-100 significance score to an AlertSeverity level."""
    from services.agent.alerts import AlertSeverity
    if significance >= 70:
        return AlertSeverity.CRITICAL
    if significance >= 40:
        return AlertSeverity.ELEVATED
    return AlertSeverity.NORMAL


# ── Core scoring function ──────────────────────────────────────────

def score_alert(alert: Alert, ds: DataSource | None = None) -> None:
    """Enrich an alert with significance scores in place.

    If no SignalProfile is registered for the alert_type, the alert
    is left unchanged (significance remains None).
    """
    profile = PROFILES.get(alert.alert_type)
    if profile is None:
        return

    data = alert.data or {}
    signal_raw = _weighted_average(profile.signal_components, data)
    routine_raw = _weighted_average(profile.routine_components, data, ds)

    significance, signal_50, routine_50 = combine_scores(signal_raw, routine_raw)
    alert.significance = significance
    alert.signal_score = signal_50
    alert.routine_score = routine_50


# ── Baseline integration helper ────────────────────────────────────

def _baseline_routine(metric: str, value: float, ds: DataSource | None) -> float:
    """Compute routine score from BaselineStore z-score.

    Returns 0.0 (no evidence) when baseline data is unavailable.
    "No evidence this is routine" != "this is half-routine".
    Low z-score (close to mean) = high routine. High z-score = low routine.
    """
    if ds is None:
        return 0.0
    stat = ds.get_baseline(metric)
    if stat is None or stat.n < 3:
        return 0.0
    if stat.std < 1e-10:
        return 0.9 if abs(value - stat.mean) < 1e-10 else 0.0
    z = abs((value - stat.mean) / stat.std)
    if z < 1.0:
        return 0.9   # well within normal range
    if z < 2.0:
        return 0.5   # somewhat expected
    if z < 3.0:
        return 0.2   # unusual
    return 0.0        # never seen before


# ── Static routine knowledge (from EXP-031 calibration) ───────────

_KNOWN_PATROL_PAIRS: dict[frozenset[str], str] = {
    frozenset({"United States", "Turkey"}): "black_sea",
    frozenset({"United States", "Japan"}): "taiwan_strait",
}


def _is_known_patrol(countries: list[str]) -> float:
    """Returns high routine score if the country set is a known patrol pair."""
    country_set = frozenset(countries)
    if country_set in _KNOWN_PATROL_PAIRS:
        return 0.9
    for patrol_pair in _KNOWN_PATROL_PAIRS:
        if patrol_pair.issubset(country_set):
            return 0.3  # known pair present but with extra countries
    return 0.0


# ── Shared extractors & factories ─────────────────────────────────

def _scale(value: float, low: float, high: float) -> float:
    """Linear scale value from [low, high] to [0.0, 1.0], clamped."""
    if high <= low:
        return 1.0 if value >= high else 0.0
    return max(0.0, min(1.0, (value - low) / (high - low)))


def _scale_key(key: str, low: float, high: float) -> Callable[[dict], float]:
    """Factory: extract a numeric key and scale it to [0.0, 1.0]."""
    def _extract(data: dict) -> float:
        return _scale(data.get(key, 0), low, high)
    return _extract


def _scale_list_key(key: str, low: float, high: float) -> Callable[[dict], float]:
    """Factory: extract len(data[key]) and scale it to [0.0, 1.0]."""
    def _extract(data: dict) -> float:
        return _scale(len(data.get(key, [])), low, high)
    return _extract


def _baseline_routine_factory(
    metric: str, key: str, *, use_len: bool = False, fixed_value: float | None = None,
) -> Callable[[dict, DataSource | None], float]:
    """Factory: create a routine component that delegates to _baseline_routine.

    Args:
        metric: BaselineStore metric name
        key: data dict key to extract the value from
        use_len: if True, use len(data[key]) instead of data[key]
        fixed_value: if set, ignore key and always pass this value
    """
    def _extract(data: dict, ds: DataSource | None) -> float:
        if fixed_value is not None:
            return _baseline_routine(metric, fixed_value, ds)
        raw = data.get(key, [] if use_len else 0)
        value = float(len(raw)) if use_len else float(raw)
        return _baseline_routine(metric, value, ds)
    return _extract


def _fimi_classification_signal(data: dict) -> float:
    """Score FIMI classification: manufactured=1.0, amplified=0.3, other=0.5."""
    c = (data.get("classification") or "").lower()
    if "manufactured" in c:
        return 1.0
    if "amplified" in c:
        return 0.3
    return 0.5


# ── Profile: military_convergence ──────────────────────────────────

def _mil_conv_country_signal(data: dict) -> float:
    """More countries = stronger signal. 2=0.3, 3=0.7, 4+=1.0."""
    count = data.get("country_count", 0)
    if count >= 4:
        return 1.0
    return _scale(count, 1, 4)


def _mil_conv_patrol_routine(data: dict, ds: DataSource | None) -> float:
    return _is_known_patrol(data.get("countries", []))


# ── Profile: chokepoint_disruption ──────────────────────────────────

def _chokepoint_severity_signal(data: dict) -> float:
    sev = (data.get("jamming_severity") or "").lower()
    return {"high": 1.0, "medium": 0.6, "low": 0.3}.get(sev, 0.2)

def _chokepoint_proximity_signal(data: dict) -> float:
    dist = data.get("distance_km", 150)
    return _scale(150 - dist, 0, 150)  # closer = higher signal


# ── Profile: infrastructure_cascade ────────────────────────────────

def _infra_colocation_signal(data: dict) -> float:
    return _scale(data.get("fires", 0) + data.get("outages", 0), 0, 8)


# ── Profile: under_reported_crisis ─────────────────────────────────

def _under_reported_ratio_signal(data: dict) -> float:
    """Higher GDELT-to-news ratio = more under-reported = stronger signal."""
    gdelt = data.get("gdelt_events", 0)
    if gdelt < 1:
        return 0.0
    ratio = gdelt / max(data.get("news_articles", 1), 1)
    return _scale(ratio, 5, 40)


# ── Profile: ew_detection ──────────────────────────────────────────

def _ew_classification_signal(data: dict) -> float:
    c = (data.get("classification") or "").upper()
    if "LIKELY" in c:
        return 1.0
    if "POSSIBLE" in c:
        return 0.5
    return 0.2

def _ew_colocation_signal(data: dict) -> float:
    return _scale(data.get("outages", 0) + data.get("conflict_events", 0), 0, 6)


# ── Profile: vip_movement ─────────────────────────────────────────

def _vip_reason_signal(data: dict) -> float:
    reason = (data.get("notable_reason") or "").lower()
    if "vip" in reason or "potus" in reason or "head of state" in reason:
        return 1.0
    if "military" in reason:
        return 0.7
    if "agency" in reason or "government" in reason:
        return 0.5
    return 0.3


# ── Profile: prediction_market_signal ──────────────────────────────

def _pred_market_delta_signal(data: dict) -> float:
    regions = data.get("matched_regions", [])
    if not regions:
        return 0.0
    max_delta = max(abs(r.get("delta_pct", 0)) for r in regions)
    return _scale(max_delta, 8, 30)


# ── Profile: supply_chain_cascade ──────────────────────────────────

def _supply_indicator_signal(data: dict) -> float:
    return _scale(data.get("disrupted_trains", 0) + data.get("fire_hotspots", 0), 0, 8)


# ── Correlation profiles ──────────────────────────────────────────

def _corr_conflict_market_signal(data: dict) -> float:
    return _scale(abs(data.get("market_delta_pct", 0)), 3, 20)


# ── Profile registry ──────────────────────────────────────────────

PROFILES: dict[str, SignalProfile] = {}


def _reg(p: SignalProfile) -> None:
    PROFILES[p.alert_type] = p


_reg(SignalProfile(
    alert_type="military_convergence",
    signal_components=[
        ScoringComponent("country_count", 0.6, _mil_conv_country_signal),
        ScoringComponent("zone_count", 0.4, _scale_list_key("zones", 0, 4)),
    ],
    routine_components=[
        RoutineComponent("known_patrol", 0.6, _mil_conv_patrol_routine),
        RoutineComponent("baseline_flights", 0.4,
                         _baseline_routine_factory("military_flights_count", "country_count")),
    ],
))

_reg(SignalProfile(
    alert_type="chokepoint_disruption",
    signal_components=[
        ScoringComponent("jamming_severity", 0.5, _chokepoint_severity_signal),
        ScoringComponent("proximity", 0.5, _chokepoint_proximity_signal),
    ],
    routine_components=[
        RoutineComponent("baseline_jamming", 1.0,
                         _baseline_routine_factory("gps_jamming_count", "", fixed_value=1.0)),
    ],
))

_reg(SignalProfile(
    alert_type="infrastructure_cascade",
    signal_components=[
        ScoringComponent("magnitude", 0.5, _scale_key("magnitude", 4.0, 7.0)),
        ScoringComponent("colocation", 0.5, _infra_colocation_signal),
    ],
    routine_components=[
        RoutineComponent("baseline_fires", 1.0,
                         _baseline_routine_factory("firms_fires_count", "fires")),
    ],
))

_reg(SignalProfile(
    alert_type="sanctions_evasion",
    signal_components=[
        ScoringComponent("vessel_count", 1.0, _scale_list_key("vessels", 0, 6)),
    ],
    routine_components=[
        RoutineComponent("baseline_ships", 1.0,
                         _baseline_routine_factory("ships_count", "vessels", use_len=True)),
    ],
))

_reg(SignalProfile(
    alert_type="airlift_surge",
    signal_components=[
        ScoringComponent("aircraft_count", 1.0, _scale_key("count", 4, 12)),
    ],
    routine_components=[
        RoutineComponent("baseline_airlift", 1.0,
                         _baseline_routine_factory("military_flights_count", "count")),
    ],
))

_reg(SignalProfile(
    alert_type="under_reported_crisis",
    signal_components=[
        ScoringComponent("gdelt_news_ratio", 0.6, _under_reported_ratio_signal),
        ScoringComponent("gdelt_volume", 0.4, _scale_key("gdelt_events", 20, 80)),
    ],
    routine_components=[
        RoutineComponent("baseline_gdelt", 1.0,
                         _baseline_routine_factory("gdelt_count", "gdelt_events")),
    ],
))

_reg(SignalProfile(
    alert_type="ew_detection",
    signal_components=[
        ScoringComponent("classification", 0.5, _ew_classification_signal),
        ScoringComponent("colocation", 0.5, _ew_colocation_signal),
    ],
    routine_components=[
        RoutineComponent("baseline_jamming", 1.0,
                         _baseline_routine_factory("gps_jamming_count", "", fixed_value=1.0)),
    ],
))

_reg(SignalProfile(
    alert_type="vip_movement",
    signal_components=[
        ScoringComponent("notable_reason", 1.0, _vip_reason_signal),
    ],
    routine_components=[
        RoutineComponent("baseline_tracked", 1.0,
                         _baseline_routine_factory("tracked_flights_count", "", fixed_value=1.0)),
    ],
))

_reg(SignalProfile(
    alert_type="prediction_market_signal",
    signal_components=[
        ScoringComponent("market_delta", 0.6, _pred_market_delta_signal),
        ScoringComponent("region_count", 0.4, _scale_list_key("matched_regions", 0, 4)),
    ],
    routine_components=[
        RoutineComponent("baseline_markets", 1.0,
                         _baseline_routine_factory("prediction_markets_count", "", fixed_value=1.0)),
    ],
))

_reg(SignalProfile(
    alert_type="black_sea_escalation",
    signal_components=[
        ScoringComponent("source_types", 0.4, _scale_list_key("source_types", 1, 3)),
        ScoringComponent("raid_count", 0.3, _scale_key("raid_count", 0, 6)),
        ScoringComponent("flight_count", 0.3, _scale_key("military_flight_count", 2, 10)),
    ],
    routine_components=[
        RoutineComponent("baseline_flights", 1.0,
                         _baseline_routine_factory("military_flights_count", "military_flight_count")),
    ],
))

_reg(SignalProfile(
    alert_type="disinformation_divergence",
    signal_components=[
        ScoringComponent("classification", 0.5, _fimi_classification_signal),
        ScoringComponent("fimi_count", 0.5, _scale_key("fimi_count", 1, 6)),
    ],
    routine_components=[
        RoutineComponent("baseline_fimi", 1.0,
                         _baseline_routine_factory("fimi_count", "fimi_count")),
    ],
))

_reg(SignalProfile(
    alert_type="supply_chain_cascade",
    signal_components=[
        ScoringComponent("source_types", 0.5, _scale_list_key("source_types", 1, 3)),
        ScoringComponent("indicator_total", 0.5, _supply_indicator_signal),
    ],
    routine_components=[
        RoutineComponent("baseline_outages", 1.0,
                         _baseline_routine_factory("internet_outages_count", "", fixed_value=1.0)),
    ],
))

# ── Correlation detector profiles ──────────────────────────────────

_reg(SignalProfile(
    alert_type="correlation_rf_anomaly",
    signal_components=[
        ScoringComponent("indicators", 0.7, _scale_key("indicators", 2, 9)),
        ScoringComponent("sources", 0.3, _scale_list_key("sources", 1, 4)),
    ],
    routine_components=[
        RoutineComponent("baseline_gps", 1.0,
                         _baseline_routine_factory("gps_jamming_count", "gps_count")),
    ],
))

_reg(SignalProfile(
    alert_type="correlation_military_buildup",
    signal_components=[
        ScoringComponent("indicators", 0.6, _scale_key("indicators", 2, 11)),
        ScoringComponent("sources", 0.4, _scale_list_key("sources", 1, 4)),
    ],
    routine_components=[
        RoutineComponent("baseline_military", 1.0,
                         _baseline_routine_factory("military_flights_count", "indicators")),
    ],
))

_reg(SignalProfile(
    alert_type="correlation_infra_cascade",
    signal_components=[
        ScoringComponent("indicators", 0.6, _scale_key("indicators", 1, 8)),
        ScoringComponent("sources", 0.4, _scale_list_key("sources", 1, 4)),
    ],
    routine_components=[
        RoutineComponent("baseline_outages", 1.0,
                         _baseline_routine_factory("internet_outages_count", "outage_count")),
    ],
))

_reg(SignalProfile(
    alert_type="correlation_conflict_escalation",
    signal_components=[
        ScoringComponent("indicators", 0.4, _scale_key("indicators", 2, 11)),
        ScoringComponent("sources", 0.3, _scale_list_key("sources", 1, 4)),
        ScoringComponent("market_delta", 0.3, _corr_conflict_market_signal),
    ],
    routine_components=[
        RoutineComponent("baseline_conflict", 1.0,
                         _baseline_routine_factory("ukraine_alerts_count", "indicators")),
    ],
))

_reg(SignalProfile(
    alert_type="correlation_fimi_amplification",
    signal_components=[
        ScoringComponent("classification", 0.5, _fimi_classification_signal),
        ScoringComponent("indicators", 0.5, _scale_key("indicators", 2, 10)),
    ],
    routine_components=[
        RoutineComponent("baseline_fimi", 1.0,
                         _baseline_routine_factory("fimi_count", "fimi_count")),
    ],
))
