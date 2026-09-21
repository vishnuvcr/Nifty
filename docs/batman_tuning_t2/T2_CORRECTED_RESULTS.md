# T2 Corrected Entry Results

## Primary rule

The primary entry gate is the frozen parent rule: gross Monte Carlo expected P&L greater than zero. Execution costs are applied to realized P&L. Net-cost-adjusted MC-EV gating is a secondary sensitivity only.

These results are reconstructed directly from the completed T2 trade-level artifact, so no historical opportunity was rerun or dropped.

## Corrected gross-gate results at ₹20 brokerage per F&O order

| Offset | Timing | Opportunities | Entered | Mean net P&L/trade (INR) | Total net P&L (INR) | Win rate | Profit factor |
|---:|---|---:|---:|---:|---:|---:|---:|
| D0 | Evening → open | 252 | 44 | +500 | +22,004 | 54.5% | 1.20 |
| D0 | 09:30 | 253 | 13 | +241 | +3,136 | 69.2% | 1.10 |
| D1 | Evening → open | 250 | 38 | -689 | -26,191 | 55.3% | 0.86 |
| D1 | 09:30 | 252 | 108 | -1,250 | -135,044 | 62.0% | 0.63 |
| D2 | Evening → open | 248 | 41 | -1,599 | -65,566 | 56.1% | 0.73 |
| D2 | 09:30 | 250 | 81 | +200 | +16,227 | 70.4% | 1.06 |
| D3 | Evening → open | 191 | 29 | -1,378 | -39,971 | 58.6% | 0.83 |
| D3 | 09:30 | 248 | 65 | -1,744 | -113,383 | 69.2% | 0.67 |
| D4 | 09:30 | 190 | 40 | +1,676 | +67,044 | 72.5% | 1.46 |

D4 evening → open had one entered observation and D5 09:30 had one entered observation; those are insufficient for serious inference and are retained only as observations.

## Operational control

The operational intraday control is D3 + same-session 09:30.

At ₹20/order it entered 65 of 248 opportunities. Net realized P&L was approximately -₹113.4k, mean approximately -₹1.74k per entered trade, win rate 69.2%, profit factor 0.67.

Year breakdown for entered D3/09:30 trades at ₹20/order:

| Year | Trades | Mean net P&L/trade (INR) | Total net P&L (INR) | Win rate |
|---:|---:|---:|---:|---:|
| 2020 | 26 | -4,785 | -124,420 | 57.7% |
| 2021 | 15 | -1,009 | -15,142 | 80.0% |
| 2022 | 13 | +134 | +1,745 | 61.5% |
| 2023 | 1 | +1,064 | +1,064 | 100.0% |
| 2024 | 10 | +2,337 | +23,371 | 90.0% |

The negative pooled result is therefore dominated by 2020 losses; later years in this historical sample are positive, but several have small sample sizes.

## Gate sensitivity

For D3/09:30, changing the gate from gross MC-EV > 0 to net MC-EV > 0 reduced entered observations from 65 to 63 at ₹10/₹20 brokerage and to 61 at ₹30. The qualitative D3/09:30 result did not change.

## Interpretation

The parent historical candidate and this operational control are not interchangeable. The parent study used daily NSE F&O bhavcopy snapshots; this timing study uses minute-level option and spot data. The parent benchmark therefore remains a separate historical EOD reference, while D3/09:30 is the control for timing/exit experiments.

No T2 candidate is promoted from these descriptive results alone.
