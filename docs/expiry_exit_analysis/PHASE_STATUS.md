# Expiry-Day Exit Analysis V2 — Phase Status

Last updated: 2026-09-20 (Asia/Kolkata)

| Phase | Status |
|---|---|
| E0 Exit-method specification | COMPLETE |
| E1 Single-pass analysis engine | COMPLETE |
| E2 Stable data preparation | COMPLETE |
| E3 CI execution | IN PROGRESS |
| E4 Results verification | NOT STARTED |
| E5 Final comparison report | NOT STARTED |

## Branch

research/expiry-auction-exit-analysis-v2

## Frozen entry rules

- Batman and Adaptive entry rules are unchanged.
- Monte Carlo: 5,000 bootstrap paths.
- Lookback: 756 completed daily log returns.
- Horizon: exactly 3 future trading sessions.
- Regime: past-only RV20 ranked over prior 252 observations.
- Adaptive candidate universe remains the frozen low/medium/high set.
- SENSEX uses the exact composite MC history provenance from the completed S5 transfer analysis.
- No exit result is used to alter entry strikes, regime, or strategy selection.

## Exit scenarios

1. Historical expiry settlement baseline.
2. 15:00:00 IST expiry-day one-minute bar OPEN.
3. 15:10:00 IST expiry-day one-minute bar OPEN.

No same-minute CLOSE is used because that would contain information after the intended execution instant.

## Cost treatment

- NIFTY: historical 2-option-point-per-contract execution stress at entry and the same stress at early exit; one strategy lot for exit-comparison sensitivity.
- SENSEX: frozen S5/S6 one-lot transfer-edge entry gate, 0.50-point adverse entry slippage per leg, SENSEX transaction costs, and 0.50-point adverse early-exit slippage per leg. No exercise STT is charged on early close.

## Data boundary

The NIFTY analysis uses the pinned historical NIFTY source file already committed on this branch through 2026-03-30, merged with the cached public 1-minute NIFTY option dataset for executable expiry-day option bars.

The SENSEX analysis uses the cached public SENSEX option/index dataset and the exact composite daily MC history used in S5/S6.
