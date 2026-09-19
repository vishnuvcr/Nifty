# SENSEX Batman + Adaptive Backtest Engine v1

## Frozen implementation
- Source strategy definitions: parent `src/nifty_mc/strategy_catalog.py`.
- Batman: Buy 1×PE(P35), Sell 2×PE(P20), Buy 1×CE(P65), Sell 2×CE(P80).
- Adaptive candidate sets are frozen from Phase-10.
- MC: bootstrap 5,000 paths from 756 past daily log returns.
- Volatility regime: RV20 annualized; rank against the prior 252 RV20 observations only; low <= 1/3, medium <= 2/3, high > 2/3.
- Entry: 09:30 IST exactly 3 future trading sessions before the actual expiry date represented by the option dataset file.
- Strike mapping: nearest unique listed strike, ATM gets first priority exactly as parent implementation.
- Entry price proxy: 09:30 bar open adjusted adversely by pre-registered slippage.
- Candidate gate: net MC EV > 0 plus at least one risk-sized lot.
- Adaptive primary: highest net MC EV among eligible candidates; CPCV frequency is tie-break only.
- Exit: cash-settled intrinsic value using the SENSEX index close on expiry date.
- Risk proxy: max(ES95, ES99).
- No early exit.

## Data provenance boundary
The primary options dataset is the publicly accessible `thetrademarkk/india-index-options-1m` dataset, CC-BY-NC, whose SENSEX option files run from 2023-08-11 onward and contain 1-minute OHLCV/OI by expiry. The index lookback uses a daily SENSEX series downloaded independently for the full 756-session history.

## Study split
- Development: 2024-01-01 through 2024-12-31.
- Validation: 2025-01-01 through 2025-12-31.
- Final holdout: 2026-01-01 through 2026-07-31 (the available options-dataset endpoint before the current run).

The final holdout is untouched for selection and is reported separately from development/validation.