# SENSEX Batman + Adaptive Transfer Backtest — v1 Results

## Execution status

S5 completed successfully on GitHub Actions.

Dataset: thetrademarkk/india-index-options-1m (CC BY-NC), supplemented with a separate historical SENSEX warm-up series so the 756-session MC lookback was available before 2024.

Execution proxy: 09:30 bar open with 0.5 option-point adverse slippage per executed leg.

Important: this is a one-lot transfer-edge backtest. The MC-EV gate is unchanged, but the copied ₹100,000 / 2% account-affordability constraint is reported separately because it suppresses every SENSEX lot at that account size.

## Chronological splits

- Development: 2024
- Validation: 2025
- Final holdout: 2026-01-01 through 2026-05-21, the latest SENSEX option expiry covered by the cached dataset used in this run.

## Results

| Period | Strategy | Trades | Total P&L / 1 lot | Mean P&L / trade | Win rate | Profit factor |
|---|---|---:|---:|---:|---:|---:|
| 2024 development | Batman | 40 | ₹60,647.60 | ₹1,516.19 | 85.0% | 1.64 |
| 2024 development | Adaptive | 51 | ₹327,167.27 | ₹6,415.04 | 70.6% | 2.53 |
| 2025 validation | Batman | 18 | ₹46,741.55 | ₹2,596.75 | 77.8% | 1.89 |
| 2025 validation | Adaptive | 46 | ₹115,473.52 | ₹2,510.29 | 60.9% | 1.62 |
| 2026 holdout | Batman | 26 | ₹205,909.30 | ₹7,919.59 | 84.6% | 3.61 |
| 2026 holdout | Adaptive | 18 | ₹51,754.14 | ₹2,875.23 | 66.7% | 1.56 |

## Combined 2025 validation + 2026 holdout

- Batman: 44 trades, ₹252,650.86 total, ₹5,742.06 mean/trade, 81.8% win rate, PF 2.92.
- Adaptive: 64 trades, ₹167,227.66 total, ₹2,612.93 mean/trade, 62.5% win rate, PF 1.60.

## Holdout diagnostics

- Batman: mean ₹6,063.03/lot, 81.8% winning outcomes, PF 2.97 across 33 observed expiries.
- Sell Put: mean ₹3,878.80/lot, 71.4% win rate, PF 2.10.
- Risk Reversal: mean -₹2,132.41/lot, 41.2% win rate, PF 0.70.
- Long Synthetic Future: mean -₹5,376.32/lot, 23.5% win rate, PF 0.54.
- Short Straddle and Short Strangle were negative in this holdout sample.

These are diagnostic per-strategy outcomes, not post-hoc replacements of the frozen Adaptive selection rule.

## Affordability diagnostic

The one-lot run retains the original MC risk calculations. At the copied ₹100,000 / 2% risk budget, the smallest estimated ES risk among evaluated holdout candidates was about ₹6,760 per lot, so zero holdout candidates could satisfy the original ₹2,000 risk budget. This is an affordability constraint, not evidence of zero strategy edge.

## Interpretation

The frozen Batman transfer shows positive net one-lot P&L in both 2025 validation and the untouched 2026 holdout, with positive holdout profit factor and win rate in this dataset.

The frozen Adaptive transfer also shows positive one-lot P&L in validation and holdout, although its holdout sample is smaller and its profit factor is lower than Batman's.

These results are transfer-study evidence, not proof of live-trading profitability. The option dataset is an educational third-party archive and uses OHLC bars rather than historical executable bid/ask quotes, so realized execution may differ materially.

## Files

- summary_development.json
- summary_validation.json
- summary_holdout.json
- strategy_realized_summary_*.csv
- adaptive_trades_*.csv
- batman_trades_*.csv