import numpy as np
import pandas as pd

from scripts.batman_t2_entry import (
    deterministic_seed,
    lot_size,
    stt_rate,
    unique_strikes,
    mc_terminal,
    get_execution_price,
    get_signal_price,
)

def test_lot_size_historical_boundaries():
    assert lot_size(pd.Timestamp("2021-06-30")) == 75
    assert lot_size(pd.Timestamp("2021-07-01")) == 50
    assert lot_size(pd.Timestamp("2024-04-25")) == 50
    assert lot_size(pd.Timestamp("2024-05-02")) == 25
    assert lot_size(pd.Timestamp("2024-10-31")) == 25

def test_stt_boundary():
    assert stt_rate(pd.Timestamp("2024-09-30")) == 0.000625
    assert stt_rate(pd.Timestamp("2024-10-01")) == 0.001

def test_unique_strikes_is_one_to_one():
    out = unique_strikes(np.array([100, 110, 120, 130, 140]), {"p20":105,"p35":115,"c65":125,"c80":135})
    assert len(out) == 4
    assert len(set(out.values())) == 4

def test_mc_is_deterministic_for_same_seed():
    r = np.array([0.01, -0.005, 0.002, -0.003] * 30, dtype=float)
    a = mc_terminal(100.0, r, 3, 5000, 123)
    b = mc_terminal(100.0, r, 3, 5000, 123)
    assert np.array_equal(a, b)

def test_signal_price_does_not_use_future_rows():
    base = pd.Timestamp("2024-01-01")
    df = pd.DataFrame({
        "expiry":[pd.Timestamp("2024-01-04")]*3,
        "option_type":["PE"]*3,
        "strike":[100,100,100],
        "timestamp":[base+pd.Timedelta(minutes=10),base+pd.Timedelta(minutes=20),base+pd.Timedelta(minutes=40)],
        "volume":[1,1,1],
        "close":[5.0,6.0,99.0],
        "open":[5.0,6.0,99.0],
    })
    px, ts = get_signal_price(df,pd.Timestamp("2024-01-04"),"PE",100,base+pd.Timedelta(minutes=25))
    assert px == 6.0
    assert ts == base+pd.Timedelta(minutes=20)

def test_execution_price_is_first_executable_bar_after_cutoff():
    base = pd.Timestamp("2024-01-01")
    df = pd.DataFrame({
        "expiry":[pd.Timestamp("2024-01-04")]*3,
        "option_type":["PE"]*3,
        "strike":[100,100,100],
        "timestamp":[base+pd.Timedelta(minutes=30),base+pd.Timedelta(minutes=31),base+pd.Timedelta(minutes=32)],
        "volume":[0,10,10],
        "open":[5.0,7.0,8.0],
        "close":[5.0,7.0,8.0],
    })
    px, ts = get_execution_price(df,pd.Timestamp("2024-01-04"),"PE",100,base+pd.Timedelta(minutes=30),True)
    assert px == 7.0
    assert ts == base+pd.Timedelta(minutes=31)

def test_deterministic_seed_is_stable():
    assert deterministic_seed(123,"abc") == deterministic_seed(123,"abc")
    assert deterministic_seed(123,"abc") != deterministic_seed(123,"abd")
