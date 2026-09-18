import pandas as pd

from nifty_mc.origins import build_expiry_schedule


def test_build_expiry_schedule_uses_sessions():
    idx = pd.date_range("2026-01-01", periods=10, freq="B")
    prices = pd.DataFrame({"close": range(100, 110)}, index=idx)
    out = build_expiry_schedule(prices, [idx[-1]], entry_days_to_expiry=(1, 3))
    assert len(out) == 2
    assert out[0].expiry_date == idx[-1]
    assert out[0].decision_date == idx[-2]
    assert out[1].decision_date == idx[-4]
