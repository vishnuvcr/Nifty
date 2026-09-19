# Walk-Forward Experiment Matrix

## Forecast models
A. Zero-drift GBM + 20D realized volatility
B. GBM + 60D realized volatility
C. GBM + EWMA volatility
D. Historical-return bootstrap
E. GARCH/regime model (phase 2)

## Horizons
Evaluate at fixed decision points before the selected weekly expiry:
- 5 trading days
- 3 trading days
- 1 trading day

## Option construction
For each origin, choose a single target expiry and freeze:
- four strikes
- four-leg executable entry debit
- lot size
- costs/slippage
- position size

Primary construction:
- long K2 put
- short K1 put
- long K3 call
- short K4 call
- K1<K2<S0<K3<K4

Run separate tests for equal wing widths and delta-targeted wings.

## Walk-forward splits
- expanding 1-year minimum history
- rolling 2-year history
- rolling 3-year history
- final untouched holdout period

No parameter is tuned on the final holdout.

## Forecast tests
For each model:
- 50/80/90% interval coverage
- interval width
- interval score
- CRPS
- median absolute percentage error
- bull/bear/neutral balanced accuracy
- MCC
- multiclass Brier score
- reliability curves

## Trading tests
For every Long Iron Condor:
- entry debit
- breakevens
- wing widths
- simulated PoP
- realized outcome
- realized P&L
- P&L after costs
- max adverse excursion if intraday path data exists
- return on capital
- max drawdown
- Sharpe/Sortino
- profit factor
- tail loss

## Comparators
A strategy must be compared with:
1. always-neutral forecast
2. historical quantile range
3. zero-drift GBM
4. realized-volatility GBM
5. EWMA GBM
6. option-implied-volatility range

The final report must show results by calendar year and volatility regime, not only pooled results.
