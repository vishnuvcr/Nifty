# All-Strategy MC-EV-Gated CPCV Result

## Research question

After testing all 36 strategies in the multi-strategy V2 lab, determine whether a fixed Monte Carlo EV gate can identify a strategy that remains useful under out-of-sample and combinatorial validation.

## Frozen comparison rule

- All 36 strategies from `src/nifty_mc/strategy_catalog.py`.
- Entry: the V2 engine's fixed 3-session-before-expiry decision date.
- Monte Carlo: 5,000 bootstrap paths using the 756-session NIFTY return lookback.
- Execution-cost stress: 2.0 option points per contract.
- Strategy gate: **net MC EV > 0 after the stress cost**.
- CPCV: six contiguous time groups, two groups held out per split, producing 15 train/test combinations.
- Minimum training observations: 10 gated trades per strategy.
- Training selection score: mean gated net P&L minus its standard error.
- Final holdout: 2025 onward, never used by the CPCV selection folds.

## CPCV result

Batman was selected in **7 of 15 splits (46.7%)**, the highest selection frequency.

Its CPCV test mean was positive in **85.7%** of its selected test splits, with a median test mean of **+30.61 points per gated trade**.

Other strategies were selected less frequently; Put Ratio Spread and Sell Put were selected 3/15 times each, while Jade Lizard and Short Strangle were selected once each.

## Final holdout for the CPCV-selected candidate

For Batman, using the same fixed net-MC-EV gate and 2-point-per-contract stress:

| Metric | 2025+ final holdout |
|---|---:|
| Gated trades | 41 |
| Mean net P&L/trade | +18.84 points |
| Total net P&L | +772.40 points |
| Win rate | 75.6% |
| Profit factor | 1.29 |
| Maximum drawdown | -1,839.90 points |
| Worst trade | -836.95 points |
| IID bootstrap P(total > 0) | 0.710 |
| Moving-block bootstrap, block 3 | 0.674 |
| Moving-block bootstrap, block 5 | 0.643 |
| Moving-block bootstrap, block 10 | 0.629 |

The block-bootstrap results are deliberately reported because the trade sequence is time ordered and may not be independent. They show that the positive final total is not equivalent to a high-certainty statistical guarantee.

## Other strategies

Several strategies produced larger final-period mean P&L under the same gate, but they did not replace Batman in the CPCV selection process. Examples include Bear Call Spread, Short Straddle, Short Strangle, Jade Lizard and Short Iron Condor.

This distinction matters: a strong final-period result alone is not enough to promote a strategy after reviewing all 36 candidates. The current research candidate is retained because it was selected most frequently by the pre-final CPCV process while also remaining positive in the final holdout.

## Operational conclusion

**Batman remains the current prospective paper-trading candidate.**

It is already implemented with:

- a fixed 09:30 IST entry time,
- prior-session model cutoff,
- entry-day NSE bid/ask snapshot,
- 5,000-path MC,
- 756-session lookback,
- net MC EV gate,
- ES95/ES99 risk sizing,
- 2-point-per-contract stress,
- no broker execution.

Batman is not a defined-risk structure. ES95/ES99 is therefore a sizing proxy rather than a hard maximum-loss bound.

This result supports continuing prospective **paper trading**, not unrestricted live deployment or any claim of guaranteed profitability.

## Reproducibility

The analysis is implemented in:

- `scripts/run_strategy_cpcv.py`
- `.github/workflows/strategy-cpcv-gated.yml`

The workflow artifact contains:

- `cpcv_splits.csv`
- `cpcv_selection_summary.csv`
- `final_holdout_all_strategies.csv`
- `strategy_cpcv_report.md`

