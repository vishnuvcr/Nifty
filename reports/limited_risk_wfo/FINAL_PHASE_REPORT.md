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
