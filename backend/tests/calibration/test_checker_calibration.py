"""Calibration tests for all 12 alert checkers across all scenarios.

Each test runs every checker against a (region, scenario) dataset and
asserts the result matches the expected outcome — fire or no-fire,
severity, and alert count bounds.
"""
import pytest

from services.agent.alert_checkers import (
    check_airlift_surge,
    check_black_sea_escalation,
    check_chokepoint_disruption,
    check_disinformation_divergence,
    check_ew_detection,
    check_infrastructure_cascade,
    check_military_convergence,
    check_prediction_market_signal,
    check_sanctions_evasion,
    check_supply_chain_cascade,
    check_under_reported_crisis,
    check_vip_movement,
)

_CHECKER_MAP = {
    "check_military_convergence": check_military_convergence,
    "check_chokepoint_disruption": check_chokepoint_disruption,
    "check_infrastructure_cascade": check_infrastructure_cascade,
    "check_sanctions_evasion": check_sanctions_evasion,
    "check_airlift_surge": check_airlift_surge,
    "check_under_reported_crisis": check_under_reported_crisis,
    "check_ew_detection": check_ew_detection,
    "check_vip_movement": check_vip_movement,
    "check_prediction_market_signal": check_prediction_market_signal,
    "check_black_sea_escalation": check_black_sea_escalation,
    "check_disinformation_divergence": check_disinformation_divergence,
    "check_supply_chain_cascade": check_supply_chain_cascade,
}


class TestCheckerCalibration:
    """Run all 12 checkers against each (region, scenario) and assert expectations."""

    def test_all_checkers(self, calibration_case):
        """For each scenario, verify every checker matches its expectation."""
        data, ds, expectation = calibration_case
        label = f"{expectation.region}:{expectation.scenario_type}"

        for ce in expectation.checkers:
            checker_fn = _CHECKER_MAP.get(ce.checker_name)
            assert checker_fn is not None, (
                f"Unknown checker: {ce.checker_name}"
            )

            alerts = checker_fn(ds)

            if ce.should_fire:
                assert len(alerts) >= ce.min_alerts, (
                    f"[{label}] {ce.checker_name} should fire "
                    f"(min {ce.min_alerts}) but got {len(alerts)} alerts. "
                    f"Notes: {ce.notes}"
                )
                assert len(alerts) <= ce.max_alerts, (
                    f"[{label}] {ce.checker_name} produced {len(alerts)} alerts, "
                    f"exceeding max {ce.max_alerts}. Threshold too loose?"
                )
                if ce.expected_severity is not None:
                    for a in alerts:
                        assert a.severity == ce.expected_severity, (
                            f"[{label}] {ce.checker_name} expected severity "
                            f"{ce.expected_severity.name} but got "
                            f"{a.severity.name}. Notes: {ce.notes}"
                        )
                # Verify alert_type matches checker convention
                for a in alerts:
                    assert a.alert_type, (
                        f"[{label}] {ce.checker_name} produced alert with "
                        f"empty alert_type"
                    )
            else:
                assert len(alerts) == 0, (
                    f"[{label}] {ce.checker_name} should NOT fire "
                    f"but produced {len(alerts)} alert(s): "
                    f"{[a.alert_type for a in alerts]}. "
                    f"Notes: {ce.notes}"
                )
