import pandas as pd

from scripts.build_option_targets import expiry_candidates


def test_2025_transition_uses_documented_expiries():
    out = set(expiry_candidates(pd.Timestamp("2025-04-01"), pd.Timestamp("2025-06-30")))
    assert pd.Timestamp("2025-04-03") in out
    assert pd.Timestamp("2025-04-11") in out
    assert pd.Timestamp("2025-04-21") in out
    assert pd.Timestamp("2025-05-05") in out
    assert pd.Timestamp("2025-05-12") in out
    assert pd.Timestamp("2025-05-19") in out
    assert pd.Timestamp("2025-05-26") in out
    assert pd.Timestamp("2025-06-02") in out
    assert pd.Timestamp("2025-06-30") in out


def test_2025_transition_does_not_create_fake_mondays():
    out = set(expiry_candidates(pd.Timestamp("2025-04-01"), pd.Timestamp("2025-06-30")))
    for date in ["2025-04-07", "2025-04-14", "2025-04-28"]:
        assert pd.Timestamp(date) not in out


def test_2025_july_august_remain_thursday_and_september_turns_tuesday():
    summer = set(expiry_candidates(pd.Timestamp("2025-07-01"), pd.Timestamp("2025-08-31")))
    assert pd.Timestamp("2025-07-03") in summer
    assert pd.Timestamp("2025-07-31") in summer
    assert pd.Timestamp("2025-08-28") in summer
    assert pd.Timestamp("2025-07-01") not in summer
    assert pd.Timestamp("2025-08-26") not in summer

    autumn = set(expiry_candidates(pd.Timestamp("2025-09-01"), pd.Timestamp("2025-09-30")))
    assert pd.Timestamp("2025-09-02") in autumn
    assert pd.Timestamp("2025-09-09") in autumn
    assert pd.Timestamp("2025-09-16") in autumn
    assert pd.Timestamp("2025-09-23") in autumn
    assert all(x.weekday() == 1 for x in autumn)


def test_historical_regime_is_thursday():
    out = expiry_candidates(pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-31"))
    assert len(out) == 4  # Jan 2024 has four Thursdays before Feb
    assert all(x.weekday() == 3 for x in out)
