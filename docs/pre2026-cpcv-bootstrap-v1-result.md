# Pre-2026 CPCV + Block Bootstrap Regime Discovery v1 — Result

## Protocol

- Source: immutable V2 run 9 artifact **35425922439**.
- Candidate universe: all **36 strategies**.
- 2026 is completely excluded.
- Regime features are computed once per decision date using past-only data.
- Volatility rank: RV20, 63 prior decision observations; thresholds 20% / 80%.
- Strategy gate: net MC EV > 0 after **2 option points per contract** stress.
- Strategy selection on each CPCV training partition: n >= 30 and mean - standard error > 0.
- CPCV: 6 chronological groups, every 2-group test combination = 15 paths.
- Block bootstrap: 10,000 resamples, block length 5.

## CPCV aggregate

| Metric | Result |
|---|---:|
| Selected test observations across paths | **1,751** |
| Mean net P&L | **+33.49 points** |
| Profit factor | **1.47** |
| Total net P&L | **+58,643.55 points** |
| Win rate | **63.96%** |
| Block-bootstrap 95% CI for mean | **+20.00 to +46.86** |
| Bootstrap probability mean <= 0 | **0.000** |
| Selection-bias diagnostic below median | **20.0%** |

## Regime robustness

| Regime | CPCV paths | Positive-mean paths | PF > 1 paths | Median test mean |
|---|---:|---:|---:|---:|
| Low | 15 | 73.3% | 73.3% | +32.11 |
| Medium | 15 | 66.7% | 66.7% | +21.51 |
| High | 15 | 86.7% | 86.7% | +67.02 |

All three regimes cleared the predeclared 50% path-stability threshold.

## Strategy-selection frequency

The selected strategy was not perfectly stable within every regime:

- Low: Risk Reversal **9/15**, Long Synthetic Future 4/15, Buy Call 2/15.
- High: Sell Put **5/15**, Risk Reversal 5/15, Long Synthetic Future 3/15, Batman 2/15.
- Medium: Short Straddle 4/15, Put Ratio Spread 4/15, Short Strangle 3/15, Strip 3/15, Buy Put 1/15.

This is important: the **regime-level return signal is more stable than the exact strategy identity**.

## Decision

**PRE-2026 CPCV ROBUSTNESS: PASS.**

The pre-2026 regime-conditioned strategy-selection process shows positive CPCV performance with a positive block-bootstrap confidence interval and a relatively low selection-bias diagnostic.

However, this does **not** justify replacing the already-used 2026 holdout result. The 2026 holdout has already been exposed and the earlier frozen mapping failed there. Therefore, this phase does not constitute a fresh out-of-sample confirmation.

The research implication is:

1. There is evidence of a pre-2026 regime-conditioned effect.
2. Exact strategy identity remains unstable, especially in medium volatility.
3. The next clean validation must come from **new observations after the existing 2026 cutoff**, not from re-optimizing and re-testing the already-used 2026 period.
4. The prospective adaptive producer remains **observation-only / NO_TRADE** until that fresh validation is available.

No strategy is promoted to live trading by this phase.
