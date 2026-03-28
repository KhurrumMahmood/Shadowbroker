"""Expected outcomes for each (region, scenario) combination.

Each expectation defines which checkers/detectors should fire and which
should stay silent. The calibration tests assert against these.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from services.agent.alerts import AlertSeverity


@dataclass(frozen=True)
class CheckerExpectation:
    """What we expect from a single alert checker for a given scenario."""
    checker_name: str
    should_fire: bool
    min_alerts: int = 0
    max_alerts: int = 50
    expected_severity: AlertSeverity | None = None
    notes: str = ""


@dataclass(frozen=True)
class DetectorExpectation:
    """What we expect from a single correlation detector."""
    finding_type: str          # e.g. "rf_anomaly", "military_buildup"
    should_fire: bool
    min_findings: int = 0
    expected_severity: str | None = None   # "high" | "medium" | "low"
    notes: str = ""


@dataclass(frozen=True)
class PostProcExpectation:
    """What we expect from a post-processing function."""
    result_key: str            # key in store dict: "coverage_gaps", "correlations"
    min_results: int = 0
    max_results: int = 200
    notes: str = ""


@dataclass
class ScenarioExpectation:
    """Full expected outcome for a (region, scenario) pair."""
    region: str
    scenario_type: str
    checkers: list[CheckerExpectation] = field(default_factory=list)
    detectors: list[DetectorExpectation] = field(default_factory=list)
    post_processing: list[PostProcExpectation] = field(default_factory=list)


# ── Registry ────────────────────────────────────────────────────────

EXPECTATIONS: dict[tuple[str, str], ScenarioExpectation] = {}


def _reg(e: ScenarioExpectation) -> None:
    EXPECTATIONS[(e.region, e.scenario_type)] = e


def get_expectation(region: str, scenario_type: str) -> ScenarioExpectation:
    return EXPECTATIONS[(region, scenario_type)]


def all_scenario_keys() -> list[tuple[str, str]]:
    return list(EXPECTATIONS.keys())


# ── Shorthand helpers ───────────────────────────────────────────────

C = CheckerExpectation
D = DetectorExpectation
P = PostProcExpectation
CRIT = AlertSeverity.CRITICAL
ELEV = AlertSeverity.ELEVATED
NORM = AlertSeverity.NORMAL

# All 12 checker names in canonical order.
_ALL_CHECKERS = [
    "check_military_convergence",
    "check_chokepoint_disruption",
    "check_infrastructure_cascade",
    "check_sanctions_evasion",
    "check_airlift_surge",
    "check_under_reported_crisis",
    "check_ew_detection",
    "check_vip_movement",
    "check_prediction_market_signal",
    "check_black_sea_escalation",
    "check_disinformation_divergence",
    "check_supply_chain_cascade",
]

# All 5 detector finding types in canonical order.
_ALL_DETECTORS = [
    "rf_anomaly",
    "military_buildup",
    "infra_cascade",
    "conflict_escalation",
    "fimi_amplification",
]


def _quiet_checkers(**overrides: CheckerExpectation) -> list[CheckerExpectation]:
    """Build a full 12-checker list where everything is silent by default.

    Pass keyword arguments keyed by checker name to override specific entries.
    Example: _quiet_checkers(check_vip_movement=C("check_vip_movement", should_fire=True, ...))
    """
    return [
        overrides.get(name, C(name, should_fire=False))
        for name in _ALL_CHECKERS
    ]


def _quiet_detectors(**overrides: DetectorExpectation) -> list[DetectorExpectation]:
    """Build a full 5-detector list where everything is silent by default."""
    return [
        overrides.get(name, D(name, should_fire=False))
        for name in _ALL_DETECTORS
    ]


# ════════════════════════════════════════════════════════════════════
#  PERSIAN GULF
# ════════════════════════════════════════════════════════════════════

_reg(ScenarioExpectation(
    region="persian_gulf",
    scenario_type="normal",
    checkers=_quiet_checkers(),
    detectors=_quiet_detectors(),
    post_processing=[
        P("coverage_gaps", max_results=0, notes="News proportional to GDELT"),
    ],
))

_reg(ScenarioExpectation(
    region="persian_gulf",
    scenario_type="hormuz_crisis",
    checkers=_quiet_checkers(
        check_military_convergence=C(
            "check_military_convergence", should_fire=True, min_alerts=1, max_alerts=1,
            expected_severity=CRIT,
            notes="3 countries (US, Iran, UK) within 200km"),
        check_chokepoint_disruption=C(
            "check_chokepoint_disruption", should_fire=True, min_alerts=1,
            notes="GPS jamming within Hormuz 150km radius"),
        check_sanctions_evasion=C(
            "check_sanctions_evasion", should_fire=True, min_alerts=1,
            expected_severity=ELEV,
            notes="Tankers in Iran zone with blank destinations"),
        check_ew_detection=C(
            "check_ew_detection", should_fire=True, min_alerts=1,
            notes="Jamming + outages within 300km"),
    ),
    detectors=_quiet_detectors(),
    post_processing=[
        P("correlations", min_results=1, notes="Flights + outages near GDELT hotspots"),
    ],
))


# ════════════════════════════════════════════════════════════════════
#  BLACK SEA
# ════════════════════════════════════════════════════════════════════

_reg(ScenarioExpectation(
    region="black_sea",
    scenario_type="normal",
    checkers=_quiet_checkers(
        check_military_convergence=C(
            "check_military_convergence", should_fire=True, min_alerts=1, max_alerts=1,
            expected_severity=ELEV,
            notes="2 NATO countries (US, Turkey) within 200km -- routine"),
    ),
    detectors=_quiet_detectors(),
))

_reg(ScenarioExpectation(
    region="black_sea",
    scenario_type="escalation",
    checkers=_quiet_checkers(
        check_military_convergence=C(
            "check_military_convergence", should_fire=True, min_alerts=1, max_alerts=1,
            expected_severity=CRIT,
            notes="3 countries (US, Turkey, UK) within 200km"),
        check_black_sea_escalation=C(
            "check_black_sea_escalation", should_fire=True, min_alerts=1, max_alerts=1,
            expected_severity=CRIT,
            notes="Air raids + mil flights > 3 + mil ships > 1"),
        check_disinformation_divergence=C(
            "check_disinformation_divergence", should_fire=True, min_alerts=1,
            notes="FIMI major_wave targeting Ukraine"),
    ),
    detectors=_quiet_detectors(
        military_buildup=D(
            "military_buildup", should_fire=True, min_findings=1,
            notes="Flights + mil ships + ukraine_alerts in same grid"),
        conflict_escalation=D(
            "conflict_escalation", should_fire=True, min_findings=1,
            notes="3 source types (alerts+flights+ships) + market delta 15pp"),
        fimi_amplification=D(
            "fimi_amplification", should_fire=True, min_findings=1,
            notes="3 FIMI narratives targeting Ukraine vs GDELT count"),
    ),
    post_processing=[
        P("coverage_gaps", min_results=1, notes="25 GDELT, only 2 news"),
        P("correlations", min_results=1, notes="Flights near GDELT hotspots"),
    ],
))


# ════════════════════════════════════════════════════════════════════
#  TAIWAN STRAIT
# ════════════════════════════════════════════════════════════════════

_reg(ScenarioExpectation(
    region="taiwan_strait",
    scenario_type="normal",
    checkers=_quiet_checkers(
        check_military_convergence=C(
            "check_military_convergence", should_fire=True, min_alerts=1, max_alerts=1,
            expected_severity=ELEV,
            notes="US + Japan within 200km -- routine"),
    ),
    detectors=_quiet_detectors(),
))

_reg(ScenarioExpectation(
    region="taiwan_strait",
    scenario_type="posture",
    checkers=_quiet_checkers(
        check_military_convergence=C(
            "check_military_convergence", should_fire=True, min_alerts=1, max_alerts=1,
            expected_severity=CRIT,
            notes="3 countries (China, US, Japan) within 200km"),
        check_prediction_market_signal=C(
            "check_prediction_market_signal", should_fire=True, min_alerts=1, max_alerts=1,
            expected_severity=ELEV,
            notes="CONFLICT delta 12pp + >5 flights near Taiwan"),
    ),
    detectors=_quiet_detectors(
        military_buildup=D(
            "military_buildup", should_fire=True, min_findings=1,
            notes="Flights + mil ships in same grid (GDELT lacks category field)"),
    ),
))


# ════════════════════════════════════════════════════════════════════
#  US EAST COAST
# ════════════════════════════════════════════════════════════════════

_reg(ScenarioExpectation(
    region="us_east_coast",
    scenario_type="normal",
    checkers=_quiet_checkers(),
    detectors=_quiet_detectors(),
))

_reg(ScenarioExpectation(
    region="us_east_coast",
    scenario_type="infrastructure_cascade",
    checkers=_quiet_checkers(
        check_infrastructure_cascade=C(
            "check_infrastructure_cascade", should_fire=True, min_alerts=1,
            notes="M5.5 earthquake + fires + outages within 200km"),
        check_vip_movement=C(
            "check_vip_movement", should_fire=True, min_alerts=1,
            expected_severity=ELEV,
            notes="VIP military type with alt > 1000"),
        check_supply_chain_cascade=C(
            "check_supply_chain_cascade", should_fire=True, min_alerts=1,
            notes="Outage + stopped trains + fires within 200km"),
    ),
    detectors=_quiet_detectors(
        infra_cascade=D(
            "infra_cascade", should_fire=True, min_findings=1,
            notes="Outages + fires co-locate"),
    ),
))


# ════════════════════════════════════════════════════════════════════
#  FINLAND / BALTIC
# ════════════════════════════════════════════════════════════════════

_reg(ScenarioExpectation(
    region="finland_baltic",
    scenario_type="normal",
    checkers=_quiet_checkers(),
    detectors=_quiet_detectors(),
))

_reg(ScenarioExpectation(
    region="finland_baltic",
    scenario_type="supply_chain",
    checkers=_quiet_checkers(
        check_supply_chain_cascade=C(
            "check_supply_chain_cascade", should_fire=True, min_alerts=1,
            notes="Outages + stopped trains + fires within 200km"),
    ),
    detectors=_quiet_detectors(
        infra_cascade=D(
            "infra_cascade", should_fire=True, min_findings=1,
            notes="Outages + fires co-locate"),
    ),
))


# ════════════════════════════════════════════════════════════════════
#  SUB-SAHARAN AFRICA
# ════════════════════════════════════════════════════════════════════

_reg(ScenarioExpectation(
    region="sub_saharan_africa",
    scenario_type="normal",
    checkers=_quiet_checkers(),
    detectors=_quiet_detectors(),
))

_reg(ScenarioExpectation(
    region="sub_saharan_africa",
    scenario_type="coverage_gap",
    checkers=_quiet_checkers(
        check_under_reported_crisis=C(
            "check_under_reported_crisis", should_fire=True, min_alerts=1,
            expected_severity=ELEV,
            notes="30 GDELT events, 1 news article -- severely under-reported"),
        check_disinformation_divergence=C(
            "check_disinformation_divergence", should_fire=True, min_alerts=1,
            notes="FIMI major_wave targeting Ethiopia"),
    ),
    detectors=_quiet_detectors(
        fimi_amplification=D(
            "fimi_amplification", should_fire=True, min_findings=1,
            notes="3 FIMI narratives targeting Ethiopia vs GDELT count"),
    ),
    post_processing=[
        P("coverage_gaps", min_results=1,
          notes="30 GDELT, 1 news -- severe gap with FIMI enrichment"),
    ],
))
