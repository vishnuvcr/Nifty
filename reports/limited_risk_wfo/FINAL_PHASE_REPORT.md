# Limited-Risk Option WFO v1 — Results

Historical phases L0-L7 completed on the frozen parent NIFTY MC-WFO strategy artifact. L8 fresh holdout is HOLD.

## Headline result

27 of 36 catalogue strategies have finite terminal loss under the NIFTY S >= 0 domain and pass the mechanical core risk audit. Batman is X (unbounded adverse loss, finite maximum intrinsic payoff).

At the required 2-point/contract net-MC-EV gate, the strongest validation candidates included Jade Lizard (+98.19 points/trade, PF 4.02, n=29) and Put Ratio Spread (+61.88, PF 3.16, n=35).

The pre-2025 CPCV selected-path bootstrap is positive (95% CI +31.62 to +49.93), but the 27-strategy max-statistic multiple-testing diagnostic is not supportive: p=0.7426.

The 2025-2026 period is already exposed by the parent study, so it is not a clean final holdout. No strategy is promoted.

## Execution/data limitation

The parent options archive supplies EOD close prices rather than verified historical bid/ask. Results are EOD reconstruction plus explicit adverse execution stress, not a historical executable-fill replay.

## Final phase decision

**HOLD / OBSERVATION-ONLY**

Fresh post-exposure data and deployment-grade bid/ask history are required before any strategy can be promoted to paper trading.

See the detailed report in the branch and the CI artifact for complete raw tables.


## Per-strategy validation confidence intervals

A post-run statistical appendix was added after the user requested per-strategy intervals. These are recomputed 95% moving-block bootstrap confidence intervals for validation trade-level net P&L, using the same 2-point/contract cost stress and MC net-EV gate. Block length is 5 trades and 10,000 bootstrap repetitions.

| Strategy | n | Mean points | 95% bootstrap CI |
|---|---:|---:|---:|
| Jade Lizard | 29 | +98.19 | +42.44 to +147.65 |
| Put Ratio Spread | 35 | +61.88 | +35.93 to +94.08 |
| Sell Put | 49 | +22.95 | -18.37 to +84.16 |
| Bull Put Spread | 28 | +16.23 | -1.45 to +52.04 |

These intervals are an additional statistical appendix; the original L0-L7 branch report's predeclared CPCV uncertainty was for selected CPCV path means (+31.62 to +49.93), not four separate strategy means.
