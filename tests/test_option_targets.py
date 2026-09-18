import pandas as pd

from scripts.build_option_targets import build_targets, expiry_candidates


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
    assert len(out) == 4
    assert all(x.weekday() == 3 for x in out)


def test_targets_never_predate_acquisition_window(tmp_path):
    dates = pd.date_range("2020-04-01", "2020-04-24", freq="B")
    index = pd.DataFrame({"date": dates, "close": range(len(dates))})
    path = tmp_path / "index.csv"
    index.to_csv(path, index=False)

    out = build_targets(str(path), "2020-04-13", "2020-04-24", dte_sessions=(5, 3))

    assert len(out) > 0
    assert (pd.to_datetime(out["decision_date"]) >= pd.Timestamp("2020-04-13")).all()


def test_targets_respect_acquisition_start_for_first_2020_expiry(tmp_path):
    dates = pd.date_range("2020-04-01", "2020-04-24", freq="B")
    index = pd.DataFrame({"date": dates, "close": range(len(dates))})
    path = tmp_path / "index.csv"
    index.to_csv(path, index=False)

    from scripts.build_option_targets import build_targets

    out = build_targets(str(path), "2020-04-13", "2020-04-24", dte_sessions=(5, 3))
    assert len(out) > 0
    assert (pd.to_datetime(out["decision_date"]) >= pd.Timestamp("2020-04-13")).all()
