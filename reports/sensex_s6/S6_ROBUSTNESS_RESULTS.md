# SENSEX S6 Robustness Results

Frozen Batman/Adaptive rules; one-lot transfer-edge mode; no SENSEX retuning.

## Slippage sensitivity

The 0.50-point baseline exactly reproduces the validated S5 transfer run. Across the predeclared 0.25/0.50/1.00/2.00-point-per-leg grid, validation and holdout remain positive for both strategies.

| Slippage | Split | Adaptive P&L | Adaptive PF | Batman P&L | Batman PF |
|---:|---|---:|---:|---:|---:|
| 0.25 | validation | ₹115,993 | 1.619 | ₹47,281 | 1.901 |
| 0.50 | validation | ₹115,474 | 1.615 | ₹46,742 | 1.889 |
| 1.00 | validation | ₹114,434 | 1.609 | ₹45,662 | 1.864 |
| 2.00 | validation | ₹119,701 | 1.634 | ₹43,504 | 1.816 |
| 0.25 | holdout | ₹52,189 | 1.560 | ₹206,689 | 3.623 |
| 0.50 | holdout | ₹51,754 | 1.555 | ₹205,909 | 3.609 |
| 1.00 | holdout | ₹50,885 | 1.545 | ₹204,351 | 3.581 |
| 2.00 | holdout | ₹49,147 | 1.524 | ₹201,234 | 3.527 |

## Monte Carlo seed sensitivity

At 0.50-point slippage, five fixed seeds (101, 202, 303, 404, 505) were run on both OOS periods.

| Split | Adaptive P&L range | Positive Adaptive seeds | Batman P&L range | Positive Batman seeds |
|---|---:|---:|---:|---:|
| Validation | ₹83,683–₹108,616 | 5/5 | ₹44,124–₹51,886 | 5/5 |
| Holdout | ₹51,324–₹66,011 | 5/5 | ₹205,049–₹226,179 | 5/5 |

Adaptive validation trade count varied from 45 to 48; holdout remained 18. Batman remained at 18 validation and 26 holdout trades across all five seeds.

## Dependence-aware bootstrap

Circular moving-block bootstrap, block length 3 trades, 10,000 repetitions, validation + holdout, base 0.50-point slippage:

| Strategy | Trades | Mean P&L | 95% block-bootstrap CI | P(mean > 0) |
|---|---:|---:|---:|---:|
| Adaptive | 64 | ₹2,613 | -₹804 to ₹6,133 | 0.9314 |
| Batman | 44 | ₹5,742 | ₹663 to ₹10,341 | 0.9875 |

## Interpretation

The frozen transfer rules are positive across every tested OOS slippage scenario and across all five fixed Monte Carlo seeds. The dependence-aware bootstrap interval for Batman remains above zero; the Adaptive interval crosses zero.

These are historical one-lot transfer-edge results, not evidence that the original ₹100,000/2%-risk sizing is deployable for SENSEX. The source archive contains OHLCV/OI rather than point-in-time bid/ask quotes, so the slippage grid is a stress test rather than direct historical spread reconstruction. The SENSEX options holdout is limited to 2026-01-01 through 2026-05-21 by the available options archive.
