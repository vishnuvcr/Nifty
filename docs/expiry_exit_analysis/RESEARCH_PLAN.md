# Expiry-Day Auction Exit Analysis — NIFTY + SENSEX

## Research question

What happens to the historical net performance of the frozen Batman and Adaptive entry rules when trades are closed on the expiry day at 15:00 IST versus 15:10 IST, instead of being held to expiry settlement?

## Scope

This is a separate sensitivity-analysis branch. Entry rules, MC process, regime classification, candidate universe, costs, data source and chronological sample are frozen from the corresponding NIFTY/SENSEX research. The only intended strategy change is the expiry-day exit mechanism.

## Exit scenarios

1. Frozen expiry-settlement baseline.
2. Exact 15:00:00 IST expiry-day 1-minute bar OPEN.
3. Exact 15:10:00 IST expiry-day 1-minute bar OPEN.

The exit timestamps are user-defined execution scenarios. The study does not assume any specific exchange auction mechanism; it only tests the P&L consequence of closing the position at those timestamps.

The exact bar OPEN is used so the exit price does not contain information from later in the same minute.

## Common controls

- 5,000 Monte Carlo paths.
- 756 completed daily log-return lookback.
- 3 future trading sessions to target expiry.
- Past-only RV20 regime ranked over the prior 252 observations.
- Batman and Adaptive entry eligibility is evaluated before any exit outcome is observed.
- Adaptive primary selection remains highest net MC EV among eligible frozen candidates.
- No exit outcome is used to alter entry strikes, regime, or strategy selection.
- NIFTY uses the historical NIFTY lot-size schedule.
- SENSEX remains one-lot transfer-edge mode, matching S5/S6.
- Entry and exit execution costs are deducted.
- Missing exit bars are reported as exit-unavailable rather than imputed.

## Statistical outputs

For each index, strategy, split and exit:
trade count, total P&L, mean/median P&L, win rate, profit factor, max drawdown, first/last observation, and 10,000-repetition circular moving-block bootstrap on validation + holdout.

## Data boundary

The rerun uses the public 1-minute index-options dataset already used by the SENSEX transfer study, with NIFTY and SENSEX option/index files cached in GitHub Actions. The NIFTY daily-history warmup source is pinned on the analysis branch. Usable dates are determined from actual option/index coverage; missing observations are not imputed.

The SENSEX sample remains limited by the available public option archive through 2026-05-21.

## Exit-cost treatment

NIFTY keeps the frozen 2-option-point-per-contract entry stress and applies the same 2-point-per-contract adverse execution stress to the closing transactions at 15:00/15:10.

SENSEX keeps the frozen S5/S6 entry MC gate and SENSEX transaction-cost model. For pre-expiry closing, actual closing-order turnover costs are applied and expiry exercise STT is not charged. The frozen S5/S6 entry gate remains unchanged.

## Success criterion

Produce reproducible results for all three exit scenarios on both indices, with a clear trade-count comparison and an explicit separation between historical settlement results and the new 15:00/15:10 exit variants.

## Entry-method control

Both indices use the frozen MC/regime entry-selection logic. The exit scenario is the only intended strategy change. To compare exit mechanics rather than account sizing, the rerun uses one-lot/one-strategy-unit transfer-edge realization after the net MC-EV entry gate. Historical transaction-cost/slippage stress is retained.
