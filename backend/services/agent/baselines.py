"""Rolling statistical baselines for anomaly detection.

Maintains exponential moving averages (EMA) per metric,
enabling z-score anomaly detection across data categories.
"""
from __future__ import annotations

import math
import threading
from dataclasses import dataclass


@dataclass
class BaselineStat:
    """Rolling statistical baseline for a metric."""
    mean: float
    std: float
    n: int


class BaselineStore:
    """Exponential moving average per metric for anomaly detection.

    Uses Welford's online algorithm for numerically stable
    variance computation, with an EMA weighting for recency bias.

    Args:
        alpha: EMA smoothing factor (0 < alpha <= 1).
               Smaller alpha = more historical weight.
               0.1 means ~10 observations to converge.
    """

    def __init__(self, alpha: float = 0.1):
        if not (0 < alpha <= 1):
            raise ValueError("alpha must be in (0, 1]")
        self._alpha = alpha
        self._stats: dict[str, _EmaState] = {}
        self._lock = threading.Lock()

    def update(self, metric: str, value: float) -> BaselineStat:
        """Update the EMA for a metric with a new observation.

        Returns the updated baseline stats.
        """
        with self._lock:
            if metric not in self._stats:
                self._stats[metric] = _EmaState(mean=value, var=0.0, n=1)
                return BaselineStat(mean=value, std=0.0, n=1)

            state = self._stats[metric]
            state.n += 1
            diff = value - state.mean
            state.mean += self._alpha * diff
            # EMA variance: exponentially weighted variance
            state.var = (1 - self._alpha) * (state.var + self._alpha * diff * diff)

            return BaselineStat(
                mean=state.mean,
                std=math.sqrt(max(state.var, 0)),
                n=state.n,
            )

    def get(self, metric: str) -> BaselineStat | None:
        """Get current baseline stats for a metric."""
        with self._lock:
            state = self._stats.get(metric)
            if state is None:
                return None
            return BaselineStat(
                mean=state.mean,
                std=math.sqrt(max(state.var, 0)),
                n=state.n,
            )

    def z_score(self, metric: str, value: float) -> float | None:
        """Calculate z-score of a value against the baseline.

        Returns None if baseline doesn't exist or std is 0.
        """
        stat = self.get(metric)
        if stat is None or stat.n < 3:
            return None
        if stat.std < 1e-10:
            # Zero variance — any deviation is "infinite"
            return 0.0 if abs(value - stat.mean) < 1e-10 else float("inf")
        return (value - stat.mean) / stat.std

    @property
    def metrics(self) -> list[str]:
        """List all tracked metrics."""
        return list(self._stats.keys())

    def reset(self, metric: str | None = None):
        """Reset a specific metric or all metrics."""
        if metric is None:
            self._stats.clear()
        else:
            self._stats.pop(metric, None)


@dataclass
class _EmaState:
    """Internal mutable state for EMA computation."""
    mean: float
    var: float
    n: int
