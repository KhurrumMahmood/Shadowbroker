"""Tests for the BaselineStore EMA anomaly detection system."""
import math
import pytest

from services.agent.baselines import BaselineStore, BaselineStat


class TestUpdate:

    def test_first_observation(self):
        store = BaselineStore()
        stat = store.update("ships_count", 100.0)
        assert stat.mean == 100.0
        assert stat.std == 0.0
        assert stat.n == 1

    def test_ema_convergence(self):
        """EMA should converge toward the true mean over many observations."""
        store = BaselineStore(alpha=0.1)
        # Feed 100 observations of value 50
        for _ in range(100):
            stat = store.update("ships_count", 50.0)
        assert stat.mean == pytest.approx(50.0, abs=0.1)

    def test_ema_tracks_changes(self):
        """EMA should eventually track a shift in the data."""
        store = BaselineStore(alpha=0.1)
        # Baseline at 50
        for _ in range(50):
            store.update("metric", 50.0)
        # Shift to 100
        for _ in range(50):
            stat = store.update("metric", 100.0)
        # Should have moved significantly toward 100
        assert stat.mean > 90.0

    def test_variance_grows_with_spread(self):
        store = BaselineStore(alpha=0.1)
        # Alternating values → should build variance
        for i in range(100):
            val = 100.0 if i % 2 == 0 else 0.0
            stat = store.update("metric", val)
        assert stat.std > 20.0  # should have significant spread

    def test_n_increments(self):
        store = BaselineStore(alpha=0.1)
        for i in range(10):
            stat = store.update("metric", float(i))
        assert stat.n == 10


class TestGet:

    def test_returns_none_for_unknown(self):
        store = BaselineStore()
        assert store.get("nonexistent") is None

    def test_returns_stats(self):
        store = BaselineStore()
        store.update("metric", 42.0)
        stat = store.get("metric")
        assert stat is not None
        assert stat.mean == 42.0
        assert stat.n == 1


class TestZScore:

    def test_returns_none_for_unknown_metric(self):
        store = BaselineStore()
        assert store.z_score("nonexistent", 50.0) is None

    def test_returns_none_with_too_few_observations(self):
        store = BaselineStore()
        store.update("metric", 50.0)
        store.update("metric", 50.0)
        # Only 2 observations — need at least 3
        assert store.z_score("metric", 100.0) is None

    def test_zero_zscore_at_mean(self):
        store = BaselineStore(alpha=0.1)
        for _ in range(20):
            store.update("metric", 50.0)
        # With all observations at 50, std ≈ 0, value at mean → 0
        z = store.z_score("metric", 50.0)
        assert z == 0.0

    def test_high_zscore_for_outlier(self):
        store = BaselineStore(alpha=0.1)
        # Build baseline around 50 with some variance
        for i in range(50):
            store.update("metric", 50.0 + (i % 5))
        # A value far from the mean should have a high z-score
        z = store.z_score("metric", 200.0)
        assert z is not None
        assert z > 5.0  # way above normal

    def test_negative_zscore_for_below_mean(self):
        store = BaselineStore(alpha=0.1)
        for i in range(50):
            store.update("metric", 50.0 + (i % 5))
        z = store.z_score("metric", 0.0)
        assert z is not None
        assert z < -5.0

    def test_inf_zscore_with_zero_variance(self):
        """If all observations are identical, any different value → inf."""
        store = BaselineStore(alpha=0.1)
        for _ in range(10):
            store.update("metric", 50.0)
        z = store.z_score("metric", 51.0)
        assert z == float("inf")


class TestMetrics:

    def test_lists_tracked_metrics(self):
        store = BaselineStore()
        store.update("ships_count", 100)
        store.update("flights_count", 200)
        store.update("earthquakes_count", 5)
        metrics = store.metrics
        assert set(metrics) == {"ships_count", "flights_count", "earthquakes_count"}


class TestReset:

    def test_reset_specific_metric(self):
        store = BaselineStore()
        store.update("a", 1.0)
        store.update("b", 2.0)
        store.reset("a")
        assert store.get("a") is None
        assert store.get("b") is not None

    def test_reset_all(self):
        store = BaselineStore()
        store.update("a", 1.0)
        store.update("b", 2.0)
        store.reset()
        assert store.metrics == []


class TestAlphaValidation:

    def test_alpha_zero_raises(self):
        with pytest.raises(ValueError):
            BaselineStore(alpha=0.0)

    def test_alpha_negative_raises(self):
        with pytest.raises(ValueError):
            BaselineStore(alpha=-0.1)

    def test_alpha_one_is_valid(self):
        store = BaselineStore(alpha=1.0)
        store.update("metric", 42.0)
        assert store.get("metric").mean == 42.0
