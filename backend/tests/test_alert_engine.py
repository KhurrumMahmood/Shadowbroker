"""Tests for the AlertEngine — runs checkers and stores results."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from services.agent.alert_engine import AlertEngine
from services.agent.alerts import AlertStore, AlertSeverity
from services.agent.datasource import StaticDataSource

FIXTURES = Path(__file__).parent / "fixtures" / "scenarios"


@pytest.fixture
def hormuz_ds():
    return StaticDataSource(FIXTURES / "hormuz_crisis")


@pytest.fixture
def quiet_ds():
    return StaticDataSource(FIXTURES / "quiet_day")


@pytest.fixture
def cascade_ds():
    return StaticDataSource(FIXTURES / "cascade_event")


class TestAlertEngine:
    def test_run_produces_alerts_for_hormuz(self, hormuz_ds):
        store = AlertStore(dedup_cooldown_seconds=0)
        engine = AlertEngine(store=store)
        count = engine.run(hormuz_ds)
        assert count >= 3  # military_convergence, chokepoint, sanctions, ew
        assert len(store.list()) >= 3

    def test_run_produces_no_alerts_for_quiet(self, quiet_ds):
        store = AlertStore(dedup_cooldown_seconds=0)
        engine = AlertEngine(store=store)
        count = engine.run(quiet_ds)
        assert count == 0
        assert len(store.list()) == 0

    def test_run_produces_cascade_alert(self, cascade_ds):
        store = AlertStore(dedup_cooldown_seconds=0)
        engine = AlertEngine(store=store)
        count = engine.run(cascade_ds)
        assert count >= 1
        types = {a["alert_type"] for a in store.list()}
        assert "infrastructure_cascade" in types

    def test_dedup_prevents_repeated_alerts(self, hormuz_ds):
        store = AlertStore(dedup_cooldown_seconds=300)
        engine = AlertEngine(store=store)
        count1 = engine.run(hormuz_ds)
        count2 = engine.run(hormuz_ds)
        assert count1 >= 3
        assert count2 == 0  # all deduped

    def test_individual_checker_failure_doesnt_block_others(self, hormuz_ds):
        store = AlertStore(dedup_cooldown_seconds=0)
        engine = AlertEngine(store=store)

        # Patch one checker to raise
        with patch("services.agent.alert_engine.check_military_convergence",
                   side_effect=RuntimeError("boom")):
            count = engine.run(hormuz_ds)
            # Should still get alerts from other checkers
            assert count >= 2

    def test_run_returns_count_of_saved_alerts(self, hormuz_ds):
        store = AlertStore(dedup_cooldown_seconds=0)
        engine = AlertEngine(store=store)
        count = engine.run(hormuz_ds)
        assert count == len(store.list())
