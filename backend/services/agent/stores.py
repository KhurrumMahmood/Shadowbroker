"""Global agent store instances.

Singleton SnapshotStore and BaselineStore that get updated on every
data refresh cycle and are read by DataSource implementations.
"""
from services.agent.baselines import BaselineStore
from services.agent.snapshots import SnapshotStore

# Global instances — updated by data_fetcher hooks, read by InMemoryDataSource
snapshot_store = SnapshotStore(max_snapshots=288)  # 288 × 5min = 24h
baseline_store = BaselineStore(alpha=0.1)
