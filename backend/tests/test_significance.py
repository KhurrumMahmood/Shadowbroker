"""Tests for the dual-model significance scoring system (EXP-024 + EXP-027)."""
from __future__ import annotations

import pytest

from services.agent.alerts import Alert, AlertSeverity
from services.agent.significance import (
    SignalProfile,
    ScoringComponent,
    RoutineComponent,
    combine_scores,
    derive_severity,
    score_alert,
    PROFILES,
)


class TestCombineScores:
    """Verify the combining function produces correct quadrant behavior."""

    def test_max_signal_no_routine(self):
        """High signal, no routine -> significance near 100."""
        sig, s50, r50 = combine_scores(1.0, 0.0)
        assert sig == 100
        assert s50 == 50.0
        assert r50 == 0.0

    def test_no_signal_max_routine(self):
        """No signal, high routine -> significance near 0."""
        sig, s50, r50 = combine_scores(0.0, 1.0)
        assert sig == 0
        assert s50 == 0.0
        assert r50 == 50.0

    def test_no_signal_no_routine(self):
        """Neither model has opinion -> significance at 50 (novel)."""
        sig, s50, r50 = combine_scores(0.0, 0.0)
        assert sig == 50

    def test_max_signal_max_routine(self):
        """Both models strong -> significance at 50 (contested)."""
        sig, s50, r50 = combine_scores(1.0, 1.0)
        assert sig == 50

    def test_moderate_signal_low_routine(self):
        """Moderately interesting event."""
        sig, s50, r50 = combine_scores(0.6, 0.2)
        assert 60 <= sig <= 75

    def test_low_signal_moderate_routine(self):
        """Probably routine."""
        sig, s50, r50 = combine_scores(0.2, 0.6)
        assert 25 <= sig <= 40

    def test_clamps_to_0_100(self):
        """Edge: values clamp within range."""
        sig_hi, _, _ = combine_scores(1.0, 0.0)
        sig_lo, _, _ = combine_scores(0.0, 1.0)
        assert 0 <= sig_hi <= 100
        assert 0 <= sig_lo <= 100


class TestScoreAlert:
    """Verify score_alert enriches alerts without breaking them."""

    def test_unknown_alert_type_gets_none(self):
        """Alert types without a profile get significance=None."""
        alert = Alert(
            alert_type="totally_unknown_type",
            severity=AlertSeverity.NORMAL,
            title="Test",
            description="Test",
        )
        score_alert(alert, ds=None)
        assert alert.significance is None
        assert alert.signal_score is None
        assert alert.routine_score is None

    def test_military_convergence_high_signal(self):
        """3+ countries should produce high signal score."""
        alert = Alert(
            alert_type="military_convergence",
            severity=AlertSeverity.CRITICAL,
            title="Test",
            description="Test",
            data={
                "countries": ["United States", "Iran", "United Kingdom"],
                "country_count": 3,
                "zones": [{"countries": ["US", "IR", "UK"]}],
            },
        )
        score_alert(alert, ds=None)
        assert alert.significance is not None
        assert alert.signal_score is not None
        assert alert.signal_score >= 25  # high signal for 3 countries

    def test_military_convergence_routine_patrol(self):
        """US+Turkey in Black Sea should have high routine score."""
        alert = Alert(
            alert_type="military_convergence",
            severity=AlertSeverity.ELEVATED,
            title="Test",
            description="Test",
            lat=45.5,
            lng=36.0,
            data={
                "countries": ["United States", "Turkey"],
                "country_count": 2,
                "zones": [{"countries": ["US", "TR"]}],
            },
        )
        score_alert(alert, ds=None)
        assert alert.significance is not None
        assert alert.routine_score is not None
        assert alert.routine_score >= 15  # known patrol pair boosts routine

    def test_military_convergence_normal_vs_escalation(self):
        """Escalation scenario should score higher than normal patrol."""
        normal = Alert(
            alert_type="military_convergence",
            severity=AlertSeverity.ELEVATED,
            title="Normal patrol",
            description="Test",
            lat=45.5, lng=36.0,
            data={
                "countries": ["United States", "Turkey"],
                "country_count": 2,
                "zones": [{"countries": ["US", "TR"]}],
            },
        )
        escalation = Alert(
            alert_type="military_convergence",
            severity=AlertSeverity.CRITICAL,
            title="3-nation convergence",
            description="Test",
            lat=45.5, lng=36.0,
            data={
                "countries": ["United States", "Turkey", "United Kingdom"],
                "country_count": 3,
                "zones": [
                    {"countries": ["US", "TR", "UK"]},
                    {"countries": ["US", "TR"]},
                ],
            },
        )
        score_alert(normal, ds=None)
        score_alert(escalation, ds=None)
        assert escalation.significance > normal.significance

    def test_airlift_surge_high_count(self):
        """8+ airlift aircraft should produce high signal."""
        alert = Alert(
            alert_type="airlift_surge",
            severity=AlertSeverity.CRITICAL,
            title="Test",
            description="Test",
            data={"count": 10, "callsigns": ["C17-1"] * 10},
        )
        score_alert(alert, ds=None)
        assert alert.significance is not None
        assert alert.significance >= 60

    def test_airlift_surge_threshold_count(self):
        """5 airlift = just at threshold, low signal but no routine evidence."""
        alert = Alert(
            alert_type="airlift_surge",
            severity=AlertSeverity.ELEVATED,
            title="Test",
            description="Test",
            data={"count": 5, "callsigns": ["C17-1"] * 5},
        )
        score_alert(alert, ds=None)
        assert alert.significance is not None
        # No baseline → routine=0 → significance is signal+50, modest
        assert 50 <= alert.significance <= 65

    def test_under_reported_crisis_severe_gap(self):
        """30 GDELT, 1 news = severely under-reported, high signal."""
        alert = Alert(
            alert_type="under_reported_crisis",
            severity=AlertSeverity.ELEVATED,
            title="Test",
            description="Test",
            data={
                "gdelt_events": 30,
                "gdelt_clusters": 8,
                "news_articles": 1,
            },
        )
        score_alert(alert, ds=None)
        assert alert.significance is not None
        assert alert.significance >= 60

    def test_under_reported_crisis_mild_gap(self):
        """30 GDELT, 2 news = less severe gap, lower signal."""
        severe = Alert(
            alert_type="under_reported_crisis",
            severity=AlertSeverity.ELEVATED,
            title="Severe",
            description="Test",
            data={"gdelt_events": 50, "gdelt_clusters": 12, "news_articles": 1},
        )
        mild = Alert(
            alert_type="under_reported_crisis",
            severity=AlertSeverity.ELEVATED,
            title="Mild",
            description="Test",
            data={"gdelt_events": 30, "gdelt_clusters": 8, "news_articles": 2},
        )
        score_alert(severe, ds=None)
        score_alert(mild, ds=None)
        assert severe.significance > mild.significance


class TestDeriveSeverity:
    """Verify score-to-severity mapping."""

    def test_high_significance_critical(self):
        assert derive_severity(85) == AlertSeverity.CRITICAL

    def test_mid_significance_elevated(self):
        assert derive_severity(55) == AlertSeverity.ELEVATED

    def test_low_significance_normal(self):
        assert derive_severity(20) == AlertSeverity.NORMAL

    def test_boundary_70_critical(self):
        assert derive_severity(70) == AlertSeverity.CRITICAL

    def test_boundary_40_elevated(self):
        assert derive_severity(40) == AlertSeverity.ELEVATED

    def test_boundary_39_normal(self):
        assert derive_severity(39) == AlertSeverity.NORMAL


class TestProfileRegistry:
    """Verify all 17 profiles are registered."""

    _ALL_EXPECTED = [
        # 12 checker alert types
        "military_convergence", "chokepoint_disruption", "infrastructure_cascade",
        "sanctions_evasion", "airlift_surge", "under_reported_crisis",
        "ew_detection", "vip_movement", "prediction_market_signal",
        "black_sea_escalation", "disinformation_divergence", "supply_chain_cascade",
        # 5 correlation alert types
        "correlation_rf_anomaly", "correlation_military_buildup",
        "correlation_infra_cascade", "correlation_conflict_escalation",
        "correlation_fimi_amplification",
    ]

    def test_all_17_profiles_registered(self):
        for name in self._ALL_EXPECTED:
            assert name in PROFILES, f"Missing profile for {name}"
        assert len(PROFILES) == 17

    def test_profiles_have_components(self):
        for name in self._ALL_EXPECTED:
            profile = PROFILES[name]
            assert len(profile.signal_components) >= 1, f"{name} missing signal components"
            assert len(profile.routine_components) >= 1, f"{name} missing routine components"

    def test_component_weights_positive(self):
        for name, profile in PROFILES.items():
            for c in profile.signal_components:
                assert c.weight > 0, f"{name} signal {c.name} has non-positive weight"
            for c in profile.routine_components:
                assert c.weight > 0, f"{name} routine {c.name} has non-positive weight"
