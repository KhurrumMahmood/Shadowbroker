"""Edge case tests for GDELT staleness gates and empty feeds.

Tests that:
1. Stale GDELT silences checker #11 and detector #5
2. Fresh GDELT allows them to fire
3. Completely empty feeds produce no exceptions or alerts
"""
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from services.agent.alert_checkers import check_disinformation_divergence
from services.agent.datasource import InMemoryDataSource
from services.correlation_engine import _detect_fimi_amplification
from services.post_processing import post_process_slow_data
from tests.calibration.scenarios import _empty_store, compose_scenario
from tests.calibration.test_checker_calibration import _CHECKER_MAP
from tests.calibration.test_detector_calibration import _DETECTOR_MAP

_GDELT_TS_PATH = "services.fetchers._store.source_timestamps"


def _africa_data() -> dict:
    """The Africa coverage_gap scenario -- has both FIMI + GDELT."""
    return compose_scenario("sub_saharan_africa", "coverage_gap")


class TestStalenessGate:
    """GDELT staleness controls checker #11 and detector #5."""

    def test_fresh_gdelt_allows_disinfo(self):
        """With fresh GDELT, checker #11 fires on Africa coverage_gap."""
        ds = InMemoryDataSource(_africa_data())
        fresh = datetime.utcnow().isoformat()
        with patch.dict(_GDELT_TS_PATH, {"gdelt": fresh}):
            alerts = check_disinformation_divergence(ds)
        assert len(alerts) >= 1, "Checker #11 should fire with fresh GDELT"

    def test_stale_gdelt_silences_disinfo(self):
        """With stale GDELT (>30min), checker #11 returns empty."""
        ds = InMemoryDataSource(_africa_data())
        stale = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        with patch.dict(_GDELT_TS_PATH, {"gdelt": stale}):
            alerts = check_disinformation_divergence(ds)
        assert len(alerts) == 0, "Checker #11 should be silenced by stale GDELT"

    def test_missing_gdelt_timestamp_silences_disinfo(self):
        """Missing GDELT timestamp treated as stale."""
        ds = InMemoryDataSource(_africa_data())
        with patch.dict(_GDELT_TS_PATH, {}, clear=True):
            alerts = check_disinformation_divergence(ds)
        assert len(alerts) == 0, "Checker #11 should be silenced by missing GDELT ts"

    def test_fresh_gdelt_allows_fimi_detector(self):
        """With fresh GDELT, detector #5 fires on Africa coverage_gap."""
        fresh = datetime.utcnow().isoformat()
        with patch.dict(_GDELT_TS_PATH, {"gdelt": fresh}):
            findings = _detect_fimi_amplification(_africa_data())
        assert len(findings) >= 1, "Detector #5 should fire with fresh GDELT"

    def test_stale_gdelt_silences_fimi_detector(self):
        """With stale GDELT, detector #5 returns empty."""
        stale = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        with patch.dict(_GDELT_TS_PATH, {"gdelt": stale}):
            findings = _detect_fimi_amplification(_africa_data())
        assert len(findings) == 0, "Detector #5 should be silenced by stale GDELT"


class TestEmptyFeeds:
    """All empty feeds produce no alerts and no exceptions."""

    def test_all_checkers_empty(self):
        """Every checker returns [] on empty data with no exceptions."""
        ds = InMemoryDataSource(_empty_store())

        for name, fn in _CHECKER_MAP.items():
            alerts = fn(ds)
            assert alerts == [], (
                f"{name} should return empty on empty feeds but got {len(alerts)}"
            )

    def test_all_detectors_empty(self):
        """Every detector returns [] on empty data with no exceptions."""
        data = _empty_store()

        for name, fn in _DETECTOR_MAP.items():
            findings = fn(data)
            assert findings == [], (
                f"{name} should return empty on empty feeds but got {len(findings)}"
            )

    def test_post_processing_empty(self):
        """Post-processing on empty data produces no results, no exceptions."""
        store = _empty_store()
        post_process_slow_data(store)

        assert store.get("coverage_gaps") == []
        assert store.get("correlations") == []
