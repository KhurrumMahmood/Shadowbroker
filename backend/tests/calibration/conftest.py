"""Shared fixtures for calibration tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from services.agent.datasource import InMemoryDataSource
from tests.calibration.expectations import all_scenario_keys, get_expectation
from tests.calibration.scenarios import compose_scenario


# ── Staleness gate control ──────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_gdelt_fresh():
    """Make GDELT appear fresh for all calibration tests by default.

    Checker #11 and detector #5 read source_timestamps from
    services.fetchers._store to decide if GDELT is stale. Patching
    this module-level dict ensures the staleness gate doesn't interfere
    with normal calibration tests.
    """
    # Production writes naive UTC via datetime.utcnow().isoformat();
    # the checker compares with datetime.utcnow() — must match format.
    fresh = datetime.utcnow().isoformat()
    with patch.dict(
        "services.fetchers._store.source_timestamps",
        {"gdelt": fresh},
    ):
        yield


@pytest.fixture
def mock_gdelt_stale():
    """Override: make GDELT appear stale (>30min old)."""
    stale = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    with patch.dict(
        "services.fetchers._store.source_timestamps",
        {"gdelt": stale},
    ):
        yield


# ── Scenario fixtures ───────────────────────────────────────────────

@pytest.fixture(params=all_scenario_keys(), ids=lambda k: f"{k[0]}:{k[1]}")
def calibration_case(request):
    """Yield (data_dict, InMemoryDataSource, ScenarioExpectation) for each scenario."""
    region, scenario_type = request.param
    data = compose_scenario(region, scenario_type)
    ds = InMemoryDataSource(data)
    expectation = get_expectation(region, scenario_type)
    return data, ds, expectation
