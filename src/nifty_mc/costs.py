from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class IndiaTradingCosts:
    brokerage_per_order: float = 20.0
    slippage_per_leg: float = 1.0
    exchange_txn_rate: float = 0.00035
    gst_rate: float = 0.18
    sebi_rate: float = 0.000001
    stamp_rate: float = 0.00003
    stt_sell_option_rate: float = 0.001

def estimate_four_leg_entry_cost(notional_turnover: float, n_legs: int = 4, cfg: IndiaTradingCosts = IndiaTradingCosts()):
    brokerage = cfg.brokerage_per_order * n_legs
    exchange = notional_turnover * cfg.exchange_txn_rate
    sebi = notional_turnover * cfg.sebi_rate
    stamp = notional_turnover * cfg.stamp_rate
    gst = (brokerage + exchange) * cfg.gst_rate
    return brokerage + exchange + sebi + stamp + gst

def apply_entry_slippage(debit: float, n_legs: int = 4, points_per_leg: float = 1.0):
    return float(debit + n_legs * points_per_leg)
