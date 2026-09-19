from pathlib import Path

import numpy as np
import pandas as pd

from scripts.batman_signal_producer import (
    build_batman_signal,
    trading_sessions_between,
    unique_strikes,
)


def test_trading_sessions_excludes_weekends_and_holidays():
    holidays = {pd.Timestamp("2026-09-16")}
    sessions = trading_sessions_between(
        pd.Timestamp("2026-09-14"),
        pd.Timestamp("2026-09-18"),
        holidays,
    )
    assert list(sessions.strftime("%Y-%m-%d")) == [
        "2026-09-14",
        "2026-09-15",
        "2026-09-17",
        "2026-09-18",
    ]


def test_unique_strikes_are_distinct():
    strikes = np.array([100, 110, 120, 130, 140], dtype=float)
    targets = {"p20": 108.0, "p35": 111.0, "c65": 124.0, "c80": 129.0}
    result = unique_strikes(strikes, targets)
    assert len(set(result.values())) == 4


def test_batman_mc_signal_builds():
    expiry = pd.Timestamp("2026-09-24")
    chain = pd.DataFrame(
        [
            {"expiry": expiry, "strike": 95.0, "option_type": "PE", "last_price": 4.0, "bid": 3.9, "ask": 4.1},
            {"expiry": expiry, "strike": 100.0, "option_type": "PE", "last_price": 6.0, "bid": 5.9, "ask": 6.1},
            {"expiry": expiry, "strike": 105.0, "option_type": "PE", "last_price": 9.0, "bid": 8.9, "ask": 9.1},
            {"expiry": expiry, "strike": 115.0, "option_type": "CE", "last_price": 8.0, "bid": 7.9, "ask": 8.1},
            {"expiry": expiry, "strike": 120.0, "option_type": "CE", "last_price": 5.0, "bid": 4.9, "ask": 5.1},
            {"expiry": expiry, "strike": 125.0, "option_type": "CE", "last_price": 3.0, "bid": 2.9, "ask": 3.1},
            {"expiry": expiry, "strike": 130.0, "option_type": "CE", "last_price": 2.0, "bid": 1.9, "ask": 2.1},
            {"expiry": expiry, "strike": 135.0, "option_type": "CE", "last_price": 1.0, "bid": 0.9, "ask": 1.1},
        ]
    )
    terminal = np.linspace(90.0, 140.0, 500)
    result = build_batman_signal(
        spot=112.0,
        terminal=terminal,
        chain=chain,
        expiry=expiry,
        lot_size=65,
        capital=100000,
        risk_pct=0.02,
        cost_per_contract=2.0,
    )
    assert result["strategy"] == "Batman"
    assert set(result["strikes"]) == {"p20", "p35", "c65", "c80"}
    assert result["contracts_per_strategy_lot"] == 6
    assert result["mc_expected_pnl_points_net"] <= result["mc_expected_pnl_points_gross"]
    assert result["entry_cost_points"] == 12.0



def test_side_execution_requires_live_bid_ask():
    from scripts.batman_signal_producer import side_execution_price

    row = pd.Series({
        "option_type": "PE",
        "strike": 23000.0,
        "bid": np.nan,
        "ask": 30.0,
        "last_price": 29.0,
    })
    assert side_execution_price(row, "BUY") == (30.0, "ask")

    with np.testing.assert_raises(ValueError):
        side_execution_price(
            pd.Series({
                "option_type": "PE",
                "strike": 23000.0,
                "bid": np.nan,
                "ask": np.nan,
                "last_price": 29.0,
            }),
            "BUY",
        )


def test_frozen_entry_protocol_metadata():
    from scripts.batman_signal_producer import ENTRY_TIME_IST

    assert ENTRY_TIME_IST.hour == 9
    assert ENTRY_TIME_IST.minute == 30

def test_batman_workflow_is_isolated_from_adaptive_pages_and_has_manual_controls():
    workflow = Path(".github/workflows/batman-signal-producer.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch:" in workflow
    assert "--site-dir site/batman" in workflow
    assert "actions/upload-pages-artifact@v3" in workflow
    assert "actions/deploy-pages@v4" in workflow
    assert "TELEGRAM_BOT_TOKEN" in workflow
    assert "TELEGRAM_CHAT_ID" in workflow
    assert "--site-dir site" not in workflow
