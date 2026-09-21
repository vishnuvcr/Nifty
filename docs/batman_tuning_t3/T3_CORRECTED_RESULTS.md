# T3 Corrected Results

## Dataset and completeness

- Eligible D3 + 09:30 BATMAN entries: 69.
- Missing signal-chain opportunities: 2; these remain explicit skips.
- Exit variants: 165.
- Brokerage scenarios: ₹10, ₹20 and ₹30 per executed order.
- Every variant contains the same 69 eligible trades.
- Corrected workflow denominator/grid validation: PASS.
- No non-triggering rule was allowed to disappear; all non-triggered exits fall back to the expiry control.

## Frozen expiry-control benchmark

| Brokerage/order | Total net P&L (INR) | Mean/trade (INR) | Win rate | Profit factor | Max drawdown (INR) |
|---:|---:|---:|---:|---:|---:|
| ₹10 | -155,272 | -2,250 | 65.2% | 0.579 | -226,339 |
| ₹20 | -160,792 | -2,330 | 65.2% | 0.566 | -228,819 |
| ₹30 | -166,312 | -2,410 | 65.2% | 0.554 | -231,299 |

## Descriptive exit candidates

At ₹20/order:

| Exit rule | Total net P&L | Mean/trade | Win rate | Profit factor | Max DD |
|---|---:|---:|---:|---:|---:|
| Trailing target: activation 20%, retracement 10% | ₹28,280 | ₹410 | 85.5% | 1.234 | -₹81,614 |
| Fixed target: 20% | ₹17,888 | ₹259 | 91.3% | 1.156 | -₹81,614 |
| Trailing stop: 40% of max-profit reference | ₹9,638 | ₹140 | 49.3% | 1.074 | -₹34,493 |

The 20% fixed-target rule is positive at all three brokerage stresses:
- ₹10/order: ₹23,408.
- ₹20/order: ₹17,888.
- ₹30/order: ₹12,368.

The trailing-target rule with 20% activation and 10% retracement is positive at all three:
- ₹10/order: ₹33,800.
- ₹20/order: ₹28,280.
- ₹30/order: ₹22,760.

The 40% trailing-stop rule is positive at all three:
- ₹10/order: ₹15,158.
- ₹20/order: ₹9,638.
- ₹30/order: ₹4,118.

These are development-period descriptive results only. The grid was searched over the same historical sample, so no rule is promoted from T3.

## Calendar stability

At ₹20/order:
- Expiry control is strongly negative in 2020 and remains negative in 2021-2022; 2023-2024 contain relatively few trades and are positive.
- Fixed target 20% is positive in 2020, 2022, 2023 and 2024 but negative in 2021.
- Trailing target 20%/10% has the same key weakness: 2021 is negative.
- Trailing stop 40% is negative in 2020-2021 and positive in 2022-2024.

This year dependence is why the next phase is nested walk-forward selection.

## Rejected prior result

The first T3 artifact from run 16 is rejected. It excluded trades when an exit trigger was never reached, creating a biased denominator and artificially high win rates. Run 20 is the accepted corrected T3 result.
