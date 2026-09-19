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

## Adaptive regime router — prospective phase

The current research candidate is separate from the frozen Batman protocol.

- High volatility + trailing p_expand rank < 0.50 → **Short Strangle**
- Medium volatility + trailing trend60 rank > 0.20 → **Sell Put**
- Low volatility → **NO_TRADE**
- Rank lookback: 252 decision observations
- MC: 5,000 bootstrap paths
- Return lookback: 756 sessions
- Stress cost: 2 option points per contract
- Entry: exactly 3 future trading sessions before the selected expiry, with the executable option-chain snapshot taken at/after 09:30 IST
- Model return cutoff: the prior completed NIFTY 50 session
- Gate: net MC EV > 0
- Position sizing: max(ES95, ES99) with the configured 2% paper-account risk budget
- No discretionary early exit
- No broker execution

The producer uses the immutable V2 run-9 regime predictions as a historical feature seed and then appends only new prospective entry-day feature observations. New signals are stored in adaptive_regime_signals.csv; open/closed paper positions are stored in adaptive_regime_ledger.csv.

The initial 2026 holdout supporting this candidate contains only 8 gated observations, so the live research objective is to collect a genuinely prospective sequence and test whether the edge persists after real entry-time quotes.
