# Nested Regime-Strategy Discovery v1 — Results

Source: immutable V2 run 9 artifact from GitHub Actions run **35425922439**.

## Protocol

- Candidate universe: all 36 strategies in `src/nifty_mc/strategy_catalog.py`.
- Entry timing: the frozen 3-session-before-expiry decision point.
- Decision-level, past-only trailing ranks; regime features are computed once per decision date and then merged to strategy rows.
- Operating transaction-cost stress: **2 option points per contract**.
- Strategy gate: **net MC EV > 0**.
- Development candidate requirements: **n >= 30** gated trades and development mean minus standard error > 0.
- Validation requirements: **n >= 10**, positive mean net P&L and PF > 1.
- Outer folds: 2023, 2024 and 2025.
- For each outer fold: development ends two years before the test year; the immediately preceding year is validation; the test year is untouched during that fold's strategy selection.
- Hyperparameters are selected only from the 2023–2025 outer-fold evidence.
- **2026 is the final untouched holdout.**

## Pre-2026 nested-selection result

Selected regime parameterization:

- trailing rank lookback: **63 decision observations**
- quantile pair: **20% / 80%**
- pooled 2023–2025 outer-fold trades: **148**
- pooled mean net P&L: **+39.56 points/trade**
- pooled PF: **1.55**
- positive outer years: **3/3**
- stable active regimes (same strategy in at least 2 of 3 outer folds): **1**

The pre-2026 evidence therefore produced a selectable parameter setting, but strategy stability across folds was limited.

## Final strategy mapping frozen before 2026

Using the selected parameterization, development through 2024 and validation in 2025 produced:

| Volatility regime | Strategy | Validation n | Validation mean | Validation PF |
|---|---|---:|---:|---:|
| High | Range Forward | 15 | +321.38 | 17.59 |
| Medium | Short Straddle | 14 | +131.56 | 4.39 |
| Low | Range Forward | 32 | +55.83 | 2.22 |

No 2026 observations were used to choose this mapping.

## 2026 untouched holdout

At the declared 2-point/contract cost stress:

- Trades: **19**
- Mean net P&L: **-196.74 points/trade**
- Profit factor: **0.16**
- Total net P&L: **-3,738.10 points**
- Win rate: **36.84%**
- Maximum drawdown: **-4,407.15 points**
- Bootstrap 95% CI for mean: **-333.99 to -63.07**

By volatility regime:

| Regime | Frozen strategy | n | Mean | PF | Total |
|---|---|---:|---:|---:|---:|
| Low | Range Forward | 1 | -344.05 | 0.00 | -344.05 |
| Medium | Short Straddle | 2 | +148.87 | inf | +297.75 |
| High | Range Forward | 16 | -230.74 | 0.10 | -3,691.80 |

The high-volatility allocation dominated the negative aggregate result.

## Cost stress on the same frozen 2026 mapping

| Cost / contract | n | Mean | PF | Total |
|---:|---:|---:|---:|---:|
| 1 | 19 | -194.74 | 0.17 | -3,700.10 |
| 2 | 19 | -196.74 | 0.16 | -3,738.10 |
| 3 | 18 | -208.99 | 0.16 | -3,761.80 |
| 4 | 18 | -210.99 | 0.15 | -3,797.80 |

The conclusion is not caused by a narrow 2-point cost assumption.

## Direction-only secondary lens

Using the same frozen parameterization and pre-2026 selection logic, the direction-only mapping produced:

- 2026 trades: **6**
- Mean net P&L: **-61.59**
- PF: **0.54**
- Total net P&L: **-369.55**

This did not provide a surviving secondary router.

## Research conclusion

This phase did **not** identify a regime-strategy router that survives the untouched 2026 holdout.

The previously observed hypotheses involving Short Straddle, Call Ratio Back Spread, Short Strangle, Sell Put, or other regime allocations must not be promoted based on 2026 inspection alone. The current adaptive producer is therefore observation-only / NO_TRADE by default.

The appropriate next research target is a further pre-2026-only discovery step that reduces multiple testing and increases stability requirements before another final holdout is opened. Candidate tools include a predeclared strategy-family constraint, CPCV on the pre-2026 selection set, and block-bootstrap confidence intervals. Any new hypothesis must be selected before re-examining 2026.

