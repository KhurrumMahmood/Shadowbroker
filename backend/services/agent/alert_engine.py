"""AlertEngine — runs all alert checkers against live data and stores results."""
from __future__ import annotations

import logging
from services.agent.alerts import AlertStore, get_alert_store
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
from services.agent.datasource import DataSource

logger = logging.getLogger(__name__)

_ALL_CHECKERS = [
    check_military_convergence,
    check_chokepoint_disruption,
    check_infrastructure_cascade,
    check_sanctions_evasion,
    check_airlift_surge,
    check_under_reported_crisis,
    check_ew_detection,
    check_vip_movement,
]


class AlertEngine:
    """Runs all alert checkers and saves results to the AlertStore."""

    def __init__(self, store: AlertStore | None = None):
        self._store = store or get_alert_store()

    def run(self, ds: DataSource) -> int:
        """Run all checkers against the datasource. Returns count of new alerts saved."""
        saved = 0
        for checker in _ALL_CHECKERS:
            try:
                alerts = checker(ds)
                for alert in alerts:
                    aid = self._store.save(alert)
                    if aid is not None:
                        saved += 1
            except Exception as e:
                logger.warning(f"Alert checker {checker.__name__} failed: {e}")
        return saved
