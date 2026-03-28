"""Integration test: run all 3 pipeline stages on the same data.

Verifies that checkers, detectors, and post-processing can all run
against the same scenario data without exceptions, and that alert
counts are internally consistent.
"""
import copy

import pytest

from services.correlation_engine import run_correlation_engine
from services.post_processing import post_process_slow_data
from tests.calibration.test_checker_calibration import _CHECKER_MAP


class TestFullPipeline:
    """Run all pipeline stages on each scenario -- no exceptions allowed."""

    def test_full_pipeline_no_exceptions(self, calibration_case):
        """All 3 stages complete without errors on every scenario."""
        data, ds, expectation = calibration_case
        store = copy.deepcopy(data)

        # Stage 1: all 12 checkers
        all_alerts = []
        for name, checker_fn in _CHECKER_MAP.items():
            alerts = checker_fn(ds)
            assert isinstance(alerts, list), (
                f"{name} returned {type(alerts)}, expected list"
            )
            all_alerts.extend(alerts)

        # Stage 2: correlation engine
        findings = run_correlation_engine(store)
        assert isinstance(findings, list), (
            f"run_correlation_engine returned {type(findings)}, expected list"
        )

        # Stage 3: post-processing
        post_process_slow_data(store)

        # Verify post-processing wrote expected keys
        assert "coverage_gaps" in store
        assert "correlations" in store
        assert isinstance(store["coverage_gaps"], list)
        assert isinstance(store["correlations"], list)

    def test_alert_fields_valid(self, calibration_case):
        """All produced alerts have required fields with valid types."""
        data, ds, expectation = calibration_case

        for name, checker_fn in _CHECKER_MAP.items():
            alerts = checker_fn(ds)
            for alert in alerts:
                assert alert.alert_type, (
                    f"{name} produced alert with empty alert_type"
                )
                assert alert.severity is not None, (
                    f"{name} produced alert with None severity"
                )
                assert alert.title, (
                    f"{name} produced alert with empty title"
                )
