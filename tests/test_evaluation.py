import numpy as np
from nifty_mc.evaluation import crps_empirical, directional_brier, interval_metrics


def test_interval_metrics_and_crps():
    samples = np.arange(1.0, 101.0)
    m = interval_metrics(50.0, samples)
    assert m["coverage_80"] == 1.0
    assert m["width_50"] > 0
    assert crps_empirical(50.0, samples) >= 0


def test_directional_brier():
    samples = np.array([90.0, 100.0, 110.0, 120.0])
    assert directional_brier(110.0, samples, 100.0) == 0.25
