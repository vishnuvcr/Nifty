import numpy as np
import pandas as pd

from scripts.adaptive_regime_signal_producer import regime_class, strategy_for_regime, trailing_rank


def test_volatility_regimes():
    assert regime_class(0.20) == "low"
    assert regime_class(1/3) == "low"
    assert regime_class(0.50) == "medium"
    assert regime_class(2/3) == "medium"
    assert regime_class(0.80) == "high"
    assert regime_class(None) == "unknown"


def test_frozen_risk_filters():
    assert strategy_for_regime("high", 0.49, 0.5) == (
        "Short Strangle", "high_vol_p_expand_filter_pass"
    )
    assert strategy_for_regime("high", 0.50, 0.5) == (
        None, "high_vol_p_expand_filter_block"
    )
    assert strategy_for_regime("medium", 0.9, 0.21) == (
        "Sell Put", "medium_vol_trend60_filter_pass"
    )
    assert strategy_for_regime("medium", 0.9, 0.20) == (
        None, "medium_vol_trend60_filter_block"
    )
    assert strategy_for_regime("low", 0.9, 0.9) == (
        None, "low_volatility_no_trade"
    )


def test_trailing_rank_is_past_only():
    h = pd.Series(np.arange(30, dtype=float))
    assert trailing_rank(h, 28.5, 30) == 29/30
    assert trailing_rank(h, -1.0, 30) == 0.0
    assert trailing_rank(h, 30.5, 30) == 1.0
    assert trailing_rank(pd.Series([1.0, np.nan]), 2.0, 30) is None
