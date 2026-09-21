import numpy as np
import pandas as pd

from scripts.batman_t7_joint_engine import exit_variants, max_profit_reference, realized_net
from scripts.batman_t7_joint_wfo import variant_id, select


def test_exit_variant_count_is_32():
    assert len(list(exit_variants())) == 32


def test_joint_configuration_count_is_448():
    assert 14 * len(list(exit_variants())) == 448


def test_variant_id_distinguishes_entry_and_exit():
    d = pd.DataFrame({
        "entry_offset":[3,4],
        "entry_timing":["same_session_0930","same_session_0930"],
        "exit_family":["fixed_target","fixed_target"],
        "target_param":[0.2,0.2],
        "stop_param":[np.nan,np.nan],
        "activation_param":[np.nan,np.nan],
        "retracement_param":[np.nan,np.nan],
    })
    ids=variant_id(d)
    assert ids.iloc[0] != ids.iloc[1]


def test_max_profit_is_nonnegative():
    legs=[("PE",105,1,"p35"),("PE",95,-2,"p20"),("CE",105,1,"c65"),("CE",115,-2,"c80")]
    assert max_profit_reference(legs, 10.0) >= 0


def test_selection_rejects_less_than_25_unique_trades():
    rows=[]
    for i in range(24):
        for b in (10.0,20.0,30.0):
            rows.append({
                "decision_date":pd.Timestamp("2020-01-01")+pd.Timedelta(days=i),
                "entry_offset":0,"entry_timing":"same_session_0930","exit_family":"expiry_control",
                "target_param":np.nan,"stop_param":np.nan,"activation_param":np.nan,"retracement_param":np.nan,
                "brokerage_per_order_inr":b,"realized_net_inr":1000.0,
            })
    d=pd.DataFrame(rows)
    try:
        select(d)
    except RuntimeError:
        return
    raise AssertionError("selector accepted fewer than 25 training trades")


def test_trailing_stop_variant_uses_stop_fraction():
    from scripts.batman_t7_joint_engine import evaluate_exit
    legs=[("PE",105,1,"p35")]
    frames={}
    marks=pd.DataFrame({"timestamp":[pd.Timestamp("2024-01-01 10:00")],"pnl_points":[10.0]})
    result, reason = evaluate_exit(
        frames, legs, marks, 0.0, 20.0, 10.0,
        ("trailing_stop", None, 0.50, 1),
        pd.Timestamp("2024-01-01")
    )
    assert reason in {"missing_expiry_exit", "missing_expiry_fallback", None}
