import numpy as np
import pandas as pd

from scripts.run_nested_regime_strategy_discovery_v1 import (
    add_regimes,
    contract_count,
    mapping_stability,
    profit_factor,
    trailing_rank,
)


def test_trailing_rank_is_past_only():
    s = pd.Series([1.0, 2.0, 3.0, 4.0])
    r = trailing_rank(s, window=3, min_history=1)
    assert np.isnan(r[0])
    assert r[1] == 1.0
    assert r[2] == 1.0


def test_regime_ranks_are_decision_level():
    rows = []
    for i in range(40):
        for strategy in ["A", "B", "C"]:
            rows.append(
                {
                    "decision_id": str(i),
                    "decision_date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=i),
                    "strategy": strategy,
                    "trend20": float(i),
                    "trend60": float(i),
                    "rv20": float(i),
                    "p_expand": float(i),
                }
            )
    out = add_regimes(
        pd.DataFrame(rows), lookback=30, qlo=1/3, qhi=2/3
    )
    nuniq = out.groupby("decision_id")[["trend20_rank","trend60_rank","rv20_rank","p_expand_rank","vol_regime"]].nunique(dropna=False)
    assert (nuniq == 1).all().all()


def test_later_observation_does_not_change_earlier_rank():
    d = pd.DataFrame(
        {
            "decision_id": np.arange(40).astype(str),
            "decision_date": pd.date_range("2024-01-01", periods=40, freq="D"),
            "strategy": ["A"] * 40,
            "trend20": np.arange(40, dtype=float),
            "trend60": np.arange(40, dtype=float),
            "rv20": np.arange(40, dtype=float),
            "p_expand": np.arange(40, dtype=float),
        }
    )
    a = add_regimes(d, 30, 1/3, 2/3)
    b = d.copy()
    b.loc[b.index[35:], "trend20"] += 10000
    bb = add_regimes(b, 30, 1/3, 2/3)
    assert np.allclose(a.loc[:34, "trend20_rank"], bb.loc[:34, "trend20_rank"], equal_nan=True)


def test_contracts_cover_all_catalog():
    assert len(contract_count("Batman").__str__()) > 0
    assert contract_count("Short Straddle") == 2
    assert contract_count("Call Ratio Back Spread") == 3


def test_profit_factor():
    assert profit_factor(np.array([10.0, -5.0, 5.0])) == 3.0


def test_mapping_stability():
    a = pd.DataFrame([{"regime":"low","strategy":"A"},{"regime":"high","strategy":"B"}])
    b = pd.DataFrame([{"regime":"low","strategy":"A"},{"regime":"high","strategy":"C"}])
    c = pd.DataFrame([{"regime":"low","strategy":"A"},{"regime":"high","strategy":"B"}])
    s = mapping_stability([a,b,c]).set_index("regime")
    assert s.loc["low","stable_strategy"] == "A"
    assert s.loc["low","stable_count"] == 3
    assert s.loc["high","stable_strategy"] == "B"
    assert s.loc["high","stable_count"] == 2
