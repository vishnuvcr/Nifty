# Prospective Paper Trading

The historical optimization is frozen. Do not alter the Batman entry thresholds while recording prospective trades.

## Daily process

1. At 09:30 IST on the decision day, freeze the model from the prior completed NIFTY 50 session close and obtain the entry-day complete NSE option-chain snapshot.
2. Run `scripts/batman_paper_signal.py`.
3. If the signal is `ENTER`, record the generated four legs, premiums, MC EV, MC POP, ES95/ES99 and recommended lots.
4. Append the signal with `scripts/paper_trade_ledger.py`.
5. At the predefined exit point, close the ledger record with the realized P&L.
6. Never retrospectively change strikes, entry date, or the MC seed to improve a trade.

## Frozen Batman rule

- Entry: fixed at 09:30 IST, exactly 3 trading sessions before expiry.
- MC: 5,000 bootstrap paths using the previous 756 daily log returns.
- Strikes: P20/P35/P65/P80 terminal MC quantiles mapped to the nearest unique listed strikes.
- Structure: +1 P35, -2 P20, +1 C65, -2 C80.
- Gate: MC EV > 0.
- Position size: ES95/ES99 risk budget.
- Paper account risk budget default: 2% per trade.

## Exit

For the initial prospective phase, use expiry settlement as the common benchmark. Do not introduce discretionary early exits until enough observations have accumulated to test an alternative exit rule separately.

## Evaluation gate

Do not declare live deployment from a single trade or a small sample. The prospective phase should accumulate a meaningful sequence of eligible signals and then be compared against the frozen historical expectation, including:

- net P&L after realistic costs and slippage
- win rate
- profit factor
- maximum drawdown
- losing streak
- tail loss
- calibration of MC EV versus realized P&L
- performance by volatility/direction regime

A signal with missing data or invalid option quotes is **NO_TRADE**, not an imputed trade.

## Adaptive regime router — observation-only research phase

The previously implemented adaptive router is **not promoted** after the corrected nested regime-strategy discovery. It remains available only for observation and feature collection.

- The producer records the regime, candidate strategy and MC metrics, but routing is **disabled by default**.
- Do not enable experimental routing until a new pre-2026 selection survives an untouched 2026 holdout and the required robustness checks.
- The frozen 2026 holdout from the nested discovery was negative under the declared gate, so the current operational state is **NO_TRADE / observation-only**.
- Continue collecting prospective features and full NO_TRADE observations without changing the rules after seeing 2026.
