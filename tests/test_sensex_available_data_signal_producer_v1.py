from __future__ import annotations

import numpy as np
import pandas as pd

from scripts.sensex_available_data_signal_producer_v1 import (
    data_limited_legs,
    make_data_limited_row,
)


def test_data_limited_batman_never_claims_execution() -> None:
    terminal = np.array([73000.0, 74000.0, 75000.0, 76000.0])
    legs = data_limited_legs("Batman", terminal, 74748.70)
    assert len(legs) == 4
    assert all(x["quote_status"] == "UNAVAILABLE" for x in legs)
    assert sum(x["quantity_per_lot"] for x in legs) == 6


def test_data_limited_row_is_not_an_enter_trade() -> None:
    decision = pd.Timestamp("2026-09-21")
    expiry = pd.Timestamp("2026-09-24")
    terminal = np.full(5000, 74748.70)
    row = make_data_limited_row(
        "Batman",
        decision,
        expiry,
        {"vol_regime": "UNAVAILABLE"},
        74748.70,
        pd.Timestamp("2026-09-18"),
        terminal,
        pd.Timestamp("2026-09-21T09:30:00+05:30"),
        "OPTION_PREMIUM_BID_ASK_SNAPSHOT_UNAVAILABLE",
        20,
    )
    assert row["signal"] == "DATA_LIMITED_CANDIDATE"
    assert row["execution_status"] == "NOT_EXECUTABLE"
    assert row["lots"] == 0
    assert pd.isna(row["mc_ev_points_net"])
    assert "option premium" in row["notes"].lower()
