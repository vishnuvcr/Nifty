# Paper Trade Signal Orchestration — 2026-09-21

## Scope
The production paper-trading entry signal system is orchestrated by one **Paper Trade Signals Producer** workflow. It is the normal 09:30 IST scheduler and the manual backfill entry point.

## Active strategy families
- NIFTY: Batman; Adaptive; Jade Lizard; Put Ratio Spread
- SENSEX: Batman; Adaptive; Jade Lizard; Put Ratio Spread

Sell Put and Bull Put Spread are not in the active prospective stream.

## Control design
The common workflow dispatches four strategy-family workflows concurrently:
1. NIFTY Batman + Adaptive
2. SENSEX Batman + Adaptive
3. NIFTY defined-risk candidates
4. SENSEX defined-risk candidates

The child workflows persist their state and the centralized Pages publisher remains the sole Pages deployer.

## 09:40 IST backfill rule
The backfill is a controlled historical observation. It must not substitute current quotes for a past 09:40 observation. When a trustworthy historical executable option-chain snapshot is unavailable, the recorded result is BACKFILL_0940_NO_TRADE / NO_TRADE with:
- historical snapshot unavailable
- no quote snapshot used
- no future outcome used
- look-ahead safe

This is separate from the prospective performance ledger.

## Page audit requirement
Every individual strategy page displays the last completed workflow run time in IST and the 09:40 backfill state when applicable.

## Error prevention
The prior Pages overwrite failure came from multiple signal workflows deploying partial site trees. The common orchestration plus centralized Pages publisher removes that race.

## Execution log — 2026-09-21

- First controlled backfill attempt: common orchestrator run **35581938338** completed, but NIFTY defined-risk child run **35581947565** failed during persistence because the workflow referenced the nonexistent path `paper_trading/prospective_defined_risk/nifty`. The 09:40 backfill records themselves were created successfully.
- Correction applied: removed the nonexistent ledger path from the NIFTY defined-risk persistence step and corrected audit interpolation so `mode`, `decision_date`, and `entry_time_ist` are written as runtime values.
- Retry common orchestrator: **35582059262**, success. All four strategy-family workflows were dispatched concurrently at 09:13:40Z.
- Successful child runs: NIFTY Batman+Adaptive **35582069744**; SENSEX Batman+Adaptive **35582069804**; NIFTY defined-risk **35582069757**; SENSEX defined-risk **35582069753**.
- Final combined Pages publication: **35582136269**, success. The full Pages tree, per-strategy audit panels, backfill records, and combined run-status feed passed validation and deployed successfully.
