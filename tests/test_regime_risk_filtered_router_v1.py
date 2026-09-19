import numpy as np
import pandas as pd

from scripts.run_regime_risk_filtered_router_v1 import apply_filter


def test_filter_selects_only_frozen_strategy_by_regime():
    d = pd.DataFrame({
        "vol_regime": ["high", "high", "medium", "medium", "low"],
        "strategy": ["Short Strangle", "Sell Put", "Sell Put", "Short Strangle", "Sell Put"],
        "p_expand_rank": [0.2, 0.2, 0.2, 0.2, 0.2],
        "trend60_rank": [0.8, 0.8, 0.8, 0.8, 0.8],
    })
    out = apply_filter(d, 0.5, 0.2)
    assert list(out.strategy) == ["Short Strangle", "Sell Put"]


def test_filter_is_stricter_in_high_and_medium_regimes():
    d = pd.DataFrame({
        "vol_regime": ["high", "high", "medium", "medium"],
        "strategy": ["Short Strangle", "Short Strangle", "Sell Put", "Sell Put"],
        "p_expand_rank": [0.4, 0.6, 0.9, 0.9],
        "trend60_rank": [0.8, 0.8, 0.1, 0.3],
    })
    out = apply_filter(d, 0.5, 0.2)
    assert len(out) == 2
    assert out.iloc[0].p_expand_rank < 0.5
    assert out.iloc[1].trend60_rank > 0.2
