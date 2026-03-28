"""Calibration tests for the 3 post-processing functions across all scenarios.

Runs `post_process_slow_data(store)` on each scenario's data dict and checks
coverage_gaps, correlations, and machine_assessments against expectations.
"""
import copy

import pytest

from services.post_processing import post_process_slow_data


class TestPostProcCalibration:
    """Run post-processing on each (region, scenario) and assert expectations."""

    def test_post_processing(self, calibration_case):
        """Verify post-processing outputs match expectations."""
        data, ds, expectation = calibration_case
        label = f"{expectation.region}:{expectation.scenario_type}"

        # Always run post-processing — even scenarios without explicit
        # expectations should complete without errors.
        store = copy.deepcopy(data)
        post_process_slow_data(store)

        assert isinstance(store.get("coverage_gaps"), list), (
            f"[{label}] coverage_gaps missing or not a list after post-processing"
        )
        assert isinstance(store.get("correlations"), list), (
            f"[{label}] correlations missing or not a list after post-processing"
        )

        for pe in expectation.post_processing:
            results = store.get(pe.result_key, [])
            count = len(results) if isinstance(results, list) else 0

            assert count >= pe.min_results, (
                f"[{label}] post_processing[{pe.result_key}] expected "
                f">= {pe.min_results} but got {count}. "
                f"Notes: {pe.notes}"
            )
            assert count <= pe.max_results, (
                f"[{label}] post_processing[{pe.result_key}] expected "
                f"<= {pe.max_results} but got {count}. "
                f"Notes: {pe.notes}"
            )
