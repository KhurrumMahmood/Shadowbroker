"""Tests for the 8 proactive alert checker functions.

Each checker is a pure function: (DataSource) -> list[Alert].
Tested against scenario fixtures for both trigger and no-trigger cases.
"""
import pytest
from pathlib import Path

from services.agent.alerts import Alert, AlertSeverity
from services.agent.alert_checkers import (
    check_military_convergence,
    check_chokepoint_disruption,
    check_infrastructure_cascade,
    check_sanctions_evasion,
    check_airlift_surge,
    check_under_reported_crisis,
    check_ew_detection,
    check_vip_movement,
)
from services.agent.datasource import StaticDataSource

FIXTURES = Path(__file__).parent / "fixtures" / "scenarios"


@pytest.fixture
def hormuz_ds():
    return StaticDataSource(FIXTURES / "hormuz_crisis")


@pytest.fixture
def taiwan_ds():
    return StaticDataSource(FIXTURES / "taiwan_posture")


@pytest.fixture
def quiet_ds():
    return StaticDataSource(FIXTURES / "quiet_day")


@pytest.fixture
def cascade_ds():
    return StaticDataSource(FIXTURES / "cascade_event")


@pytest.fixture
def airlift_ds():
    return StaticDataSource(FIXTURES / "airlift_surge")


@pytest.fixture
def discovery_ds():
    return StaticDataSource(FIXTURES / "open_ended_discovery")


class TestMilitaryConvergence:
    """Alert when 2+ countries' military flights within 200km of each other."""

    def test_triggers_hormuz(self, hormuz_ds):
        alerts = check_military_convergence(hormuz_ds)
        assert len(alerts) >= 1
        a = alerts[0]
        assert a.alert_type == "military_convergence"
        assert a.severity in (AlertSeverity.CRITICAL, AlertSeverity.ELEVATED)
        assert a.lat is not None
        assert "countries" in a.data or "country_count" in a.data

    def test_triggers_taiwan(self, taiwan_ds):
        alerts = check_military_convergence(taiwan_ds)
        assert len(alerts) >= 1

    def test_no_trigger_quiet(self, quiet_ds):
        alerts = check_military_convergence(quiet_ds)
        assert len(alerts) == 0


class TestChokepointDisruption:
    """Alert when GPS jamming detected at a major chokepoint."""

    def test_triggers_hormuz(self, hormuz_ds):
        alerts = check_chokepoint_disruption(hormuz_ds)
        assert len(alerts) >= 1
        a = alerts[0]
        assert a.alert_type == "chokepoint_disruption"
        assert a.severity in (AlertSeverity.CRITICAL, AlertSeverity.ELEVATED)

    def test_no_trigger_quiet(self, quiet_ds):
        alerts = check_chokepoint_disruption(quiet_ds)
        assert len(alerts) == 0


class TestInfrastructureCascade:
    """Alert when earthquake + fire + outage are co-located."""

    def test_triggers_cascade(self, cascade_ds):
        alerts = check_infrastructure_cascade(cascade_ds)
        assert len(alerts) >= 1
        a = alerts[0]
        assert a.alert_type == "infrastructure_cascade"
        assert a.severity == AlertSeverity.CRITICAL

    def test_no_trigger_quiet(self, quiet_ds):
        alerts = check_infrastructure_cascade(quiet_ds)
        assert len(alerts) == 0


class TestSanctionsEvasion:
    """Alert when ships with blank/suspicious destinations near sanctioned coasts."""

    def test_triggers_hormuz(self, hormuz_ds):
        alerts = check_sanctions_evasion(hormuz_ds)
        assert len(alerts) >= 1
        a = alerts[0]
        assert a.alert_type == "sanctions_evasion"

    def test_no_trigger_quiet(self, quiet_ds):
        alerts = check_sanctions_evasion(quiet_ds)
        assert len(alerts) == 0


class TestAirliftSurge:
    """Alert when strategic airlift (C-17, C-5) count exceeds threshold."""

    def test_triggers_surge(self, airlift_ds):
        alerts = check_airlift_surge(airlift_ds)
        assert len(alerts) >= 1
        a = alerts[0]
        assert a.alert_type == "airlift_surge"
        assert a.severity in (AlertSeverity.CRITICAL, AlertSeverity.ELEVATED)
        assert "count" in a.data

    def test_no_trigger_quiet(self, quiet_ds):
        alerts = check_airlift_surge(quiet_ds)
        assert len(alerts) == 0


class TestUnderReportedCrisis:
    """Alert when GDELT event count is high but news coverage is low."""

    def test_triggers_with_high_gdelt_low_news(self):
        """Create a scenario with lots of GDELT events but few news articles."""
        import json
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            # Many GDELT events in one region
            gdelt = [
                {"name": f"Event {i}", "count": 5, "action_geo_cc": "SD",
                 "lat": 15.5, "lng": 32.5, "source_url": f"http://e/{i}"}
                for i in range(15)
            ]
            (tmp / "gdelt.json").write_text(json.dumps(gdelt))
            # Only 1 news article
            news = [{"title": "Brief mention", "source": "wire", "url": "http://n/1"}]
            (tmp / "news.json").write_text(json.dumps(news))

            ds = StaticDataSource(tmp)
            alerts = check_under_reported_crisis(ds)
            assert len(alerts) >= 1
            a = alerts[0]
            assert a.alert_type == "under_reported_crisis"

    def test_no_trigger_balanced(self, hormuz_ds):
        """Hormuz has both GDELT events and news — should not trigger."""
        alerts = check_under_reported_crisis(hormuz_ds)
        assert len(alerts) == 0


class TestEWDetection:
    """Alert when GPS jamming + internet outage + conflict co-located."""

    def test_triggers_hormuz(self, hormuz_ds):
        """Hormuz has GPS jamming + internet outages + GDELT near same location."""
        alerts = check_ew_detection(hormuz_ds)
        assert len(alerts) >= 1
        a = alerts[0]
        assert a.alert_type == "ew_detection"
        assert a.severity in (AlertSeverity.CRITICAL, AlertSeverity.ELEVATED)

    def test_no_trigger_quiet(self, quiet_ds):
        alerts = check_ew_detection(quiet_ds)
        assert len(alerts) == 0


class TestVIPMovement:
    """Alert when notable/tracked aircraft detected airborne."""

    def test_triggers_with_tracked_aircraft(self):
        """Create a scenario with a known VIP aircraft."""
        import json
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            flights = [
                {"icao24": "a00001", "callsign": "EXEC1F",
                 "country": "United States", "model": "Boeing 747-200",
                 "lat": 38.9, "lng": -77.0, "alt": 35000, "heading": 90,
                 "military_type": "vip", "origin_name": "Andrews AFB",
                 "dest_name": "", "is_notable": True,
                 "notable_reason": "Head of State aircraft"},
            ]
            (tmp / "military_flights.json").write_text(json.dumps(flights))
            ds = StaticDataSource(tmp)
            alerts = check_vip_movement(ds)
            assert len(alerts) >= 1
            a = alerts[0]
            assert a.alert_type == "vip_movement"

    def test_no_trigger_quiet(self, quiet_ds):
        alerts = check_vip_movement(quiet_ds)
        assert len(alerts) == 0


class TestAllCheckers:
    """Integration: run all checkers against each scenario."""

    def test_hormuz_produces_multiple_alert_types(self, hormuz_ds):
        """Hormuz crisis should trigger multiple alert types."""
        all_alerts = []
        all_alerts.extend(check_military_convergence(hormuz_ds))
        all_alerts.extend(check_chokepoint_disruption(hormuz_ds))
        all_alerts.extend(check_sanctions_evasion(hormuz_ds))
        all_alerts.extend(check_ew_detection(hormuz_ds))
        types = {a.alert_type for a in all_alerts}
        assert len(types) >= 3, f"Expected 3+ alert types, got: {types}"

    def test_quiet_day_produces_no_alerts(self, quiet_ds):
        """Quiet day should produce zero alerts from any checker."""
        all_alerts = []
        all_alerts.extend(check_military_convergence(quiet_ds))
        all_alerts.extend(check_chokepoint_disruption(quiet_ds))
        all_alerts.extend(check_infrastructure_cascade(quiet_ds))
        all_alerts.extend(check_sanctions_evasion(quiet_ds))
        all_alerts.extend(check_airlift_surge(quiet_ds))
        all_alerts.extend(check_ew_detection(quiet_ds))
        all_alerts.extend(check_vip_movement(quiet_ds))
        assert len(all_alerts) == 0, f"Quiet day produced alerts: {[a.title for a in all_alerts]}"
