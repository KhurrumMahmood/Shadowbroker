"""Tests for the proactive alert system — models, store, and API."""
import time
import pytest
from unittest.mock import patch

from services.agent.alerts import (
    Alert,
    AlertSeverity,
    AlertStore,
    get_alert_store,
)


class TestAlertModel:
    def test_defaults(self):
        a = Alert(
            alert_type="test",
            severity=AlertSeverity.ELEVATED,
            title="Test Alert",
            description="Something happened",
        )
        assert a.alert_type == "test"
        assert a.severity == AlertSeverity.ELEVATED
        assert a.lat is None
        assert a.lng is None
        assert a.data == {}
        assert a.created_at == 0.0
        assert a.alert_id == ""

    def test_full_construction(self):
        a = Alert(
            alert_type="military_convergence",
            severity=AlertSeverity.CRITICAL,
            title="Military Convergence",
            description="3 countries' flights within 200km",
            lat=26.5,
            lng=56.3,
            data={"countries": ["US", "IR", "UK"]},
        )
        assert a.lat == 26.5
        assert a.data["countries"] == ["US", "IR", "UK"]


class TestAlertStore:
    def test_save_and_get(self):
        store = AlertStore(max_alerts=50)
        a = Alert(
            alert_type="test",
            severity=AlertSeverity.NORMAL,
            title="Test",
            description="desc",
        )
        aid = store.save(a)
        assert aid
        retrieved = store.get(aid)
        assert retrieved is not None
        assert retrieved.title == "Test"
        assert retrieved.alert_id == aid
        assert retrieved.created_at > 0

    def test_get_missing_returns_none(self):
        store = AlertStore()
        assert store.get("nonexistent") is None

    def test_save_returns_unique_ids(self):
        store = AlertStore(dedup_cooldown_seconds=0)
        ids = set()
        for i in range(20):
            a = Alert(alert_type=f"type_{i}", severity=AlertSeverity.NORMAL,
                      title=f"Alert {i}", description="d")
            ids.add(store.save(a))
        assert len(ids) == 20

    def test_max_alerts_evicts_oldest(self):
        store = AlertStore(max_alerts=3, dedup_cooldown_seconds=0)
        aids = []
        for i in range(5):
            a = Alert(alert_type=f"type_{i}", severity=AlertSeverity.NORMAL,
                      title=f"Alert {i}", description="d")
            aids.append(store.save(a))
        # First two should be evicted
        assert store.get(aids[0]) is None
        assert store.get(aids[1]) is None
        # Last three should exist
        assert store.get(aids[2]) is not None
        assert store.get(aids[3]) is not None
        assert store.get(aids[4]) is not None

    def test_ttl_expires_alerts(self):
        store = AlertStore(ttl_seconds=0.01)
        a = Alert(alert_type="test", severity=AlertSeverity.NORMAL,
                  title="Expiring", description="d")
        aid = store.save(a)
        time.sleep(0.02)
        assert store.get(aid) is None

    def test_list_returns_metadata(self):
        store = AlertStore()
        a1 = Alert(alert_type="ew_detection", severity=AlertSeverity.CRITICAL,
                   title="EW Detected", description="GPS jamming co-located",
                   lat=26.5, lng=56.3)
        a2 = Alert(alert_type="airlift_surge", severity=AlertSeverity.ELEVATED,
                   title="Airlift Surge", description="8 C-17s eastbound")
        store.save(a1)
        store.save(a2)

        items = store.list()
        assert len(items) == 2
        # Should have metadata but no description body
        for item in items:
            assert "id" in item
            assert "alert_type" in item
            assert "severity" in item
            assert "title" in item
            assert "created_at" in item

    def test_list_newest_first(self):
        store = AlertStore()
        store.save(Alert(alert_type="a", severity=AlertSeverity.NORMAL,
                         title="First", description="d"))
        store.save(Alert(alert_type="b", severity=AlertSeverity.NORMAL,
                         title="Second", description="d"))
        items = store.list()
        assert items[0]["title"] == "Second"
        assert items[1]["title"] == "First"

    def test_dedup_within_cooldown(self):
        """Same alert_type + same location should be deduplicated within cooldown."""
        store = AlertStore(dedup_cooldown_seconds=60)
        a1 = Alert(alert_type="ew_detection", severity=AlertSeverity.CRITICAL,
                   title="EW 1", description="d", lat=26.5, lng=56.3)
        a2 = Alert(alert_type="ew_detection", severity=AlertSeverity.CRITICAL,
                   title="EW 2", description="d", lat=26.5, lng=56.3)
        id1 = store.save(a1)
        id2 = store.save(a2)
        assert id1  # first saves
        assert id2 is None  # second is deduplicated

    def test_dedup_allows_different_types(self):
        """Different alert types should not be deduplicated."""
        store = AlertStore(dedup_cooldown_seconds=60)
        a1 = Alert(alert_type="ew_detection", severity=AlertSeverity.CRITICAL,
                   title="EW", description="d", lat=26.5, lng=56.3)
        a2 = Alert(alert_type="military_convergence", severity=AlertSeverity.ELEVATED,
                   title="Mil Conv", description="d", lat=26.5, lng=56.3)
        id1 = store.save(a1)
        id2 = store.save(a2)
        assert id1
        assert id2  # different type, not deduped

    def test_dedup_allows_after_cooldown(self):
        """Same alert should be allowed after cooldown expires."""
        store = AlertStore(dedup_cooldown_seconds=0.01)
        a1 = Alert(alert_type="test", severity=AlertSeverity.NORMAL,
                   title="T1", description="d", lat=10.0, lng=20.0)
        id1 = store.save(a1)
        assert id1
        time.sleep(0.02)
        a2 = Alert(alert_type="test", severity=AlertSeverity.NORMAL,
                   title="T2", description="d", lat=10.0, lng=20.0)
        id2 = store.save(a2)
        assert id2  # cooldown expired, should save


class TestAlertStoreSingleton:
    def test_get_alert_store_returns_same_instance(self):
        # Reset singleton for test isolation
        import services.agent.alerts as mod
        mod._alert_store = None
        s1 = get_alert_store()
        s2 = get_alert_store()
        assert s1 is s2
        mod._alert_store = None  # cleanup
