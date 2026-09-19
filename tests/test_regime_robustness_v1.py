import numpy as np
import pandas as pd

from scripts.run_regime_robustness_v1 import trailing_rank, add_adaptive_regime, select_one_per_regime


def test_trailing_rank_excludes_current_observation():
    s = pd.Series([1.0, 2.0, 3.0, 4.0])
    r = trailing_rank(s, window=3, min_history=1)
    assert np.isnan(r[0])
    assert r[1] == 1.0
    assert r[2] == 1.0
    assert r[3] == 1.0


def test_regime_classifier_is_past_only():
    dates = pd.date_range("2024-01-01", periods=40, freq="D")
    d = pd.DataFrame({
        "decision_date": dates,
        "decision_id": np.arange(40).astype(str),
        "trend20": np.linspace(-1, 1, 40),
        "trend60": np.linspace(-0.5, 0.5, 40),
        "rv20": np.linspace(0.1, 0.5, 40),
        "p_expand": np.linspace(0.1, 0.9, 40),
    })
    a = add_adaptive_regime(d, lookback=30, qlo=1/3, qhi=2/3)
    b = a.copy()
    b.loc[b.index[35:], "trend20"] += 1000
    bb = add_adaptive_regime(b, lookback=30, qlo=1/3, qhi=2/3)
    # The first 30 observations cannot be classified, and a prior rank must
    # not react to a later observation.
    assert np.allclose(
        a.loc[:34, "trend20_rank"].to_numpy(float),
        bb.loc[:34, "trend20_rank"].to_numpy(float),
        equal_nan=True,
    )


def test_one_strategy_is_selected_per_regime():
    rows = []
    for regime in ["low", "medium", "high"]:
        for strategy in ["A", "B"]:
            for i in range(35):
                rows.append({
                    "vol_regime": regime,
                    "strategy": strategy,
                    "gate": True,
                    "net_pnl": 10.0 if strategy == "A" else 5.0,
                })
    # Add validation: A wins in every regime.
    dev = pd.DataFrame(rows)
    val = pd.DataFrame(rows)
    out = select_one_per_regime(dev, val, cost=2.0)
    assert set(out["regime"]) == {"low", "medium", "high"}
    assert len(out) == 3
    assert set(out["strategy"]) == {"A"}
