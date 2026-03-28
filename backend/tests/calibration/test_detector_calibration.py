"""Calibration tests for all 5 correlation detectors across all scenarios.

Each test runs every detector against a (region, scenario) dataset and
asserts the result matches the expected outcome — fire or no-fire,
finding count bounds, and severity.
"""
import pytest

from services.correlation_engine import (
    _detect_rf_anomaly,
    _detect_military_buildup,
    _detect_infra_cascade,
    _detect_conflict_escalation,
    _detect_fimi_amplification,
)

_DETECTOR_MAP = {
    "rf_anomaly": _detect_rf_anomaly,
    "military_buildup": _detect_military_buildup,
    "infra_cascade": _detect_infra_cascade,
    "conflict_escalation": _detect_conflict_escalation,
    "fimi_amplification": _detect_fimi_amplification,
}


class TestDetectorCalibration:
    """Run all 5 detectors against each (region, scenario) and assert expectations."""

    def test_all_detectors(self, calibration_case):
        """For each scenario, verify every detector matches its expectation."""
        data, ds, expectation = calibration_case
        label = f"{expectation.region}:{expectation.scenario_type}"

        for de in expectation.detectors:
            detector_fn = _DETECTOR_MAP.get(de.finding_type)
            assert detector_fn is not None, (
                f"Unknown detector: {de.finding_type}"
            )

            findings = detector_fn(data)

            if de.should_fire:
                assert len(findings) >= de.min_findings, (
                    f"[{label}] {de.finding_type} should fire "
                    f"(min {de.min_findings}) but got {len(findings)} findings. "
                    f"Notes: {de.notes}"
                )
                if de.expected_severity is not None:
                    for f in findings:
                        assert f.get("severity") == de.expected_severity, (
                            f"[{label}] {de.finding_type} expected severity "
                            f"{de.expected_severity} but got "
                            f"{f.get('severity')}. Notes: {de.notes}"
                        )
            else:
                assert len(findings) == 0, (
                    f"[{label}] {de.finding_type} should NOT fire "
                    f"but produced {len(findings)} finding(s): "
                    f"{[f.get('type') for f in findings]}. "
                    f"Notes: {de.notes}"
                )
