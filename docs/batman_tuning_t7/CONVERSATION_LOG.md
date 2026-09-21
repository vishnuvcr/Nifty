# T7 Audit Log

## 2026-09-21 — holdout execution and correction

The T7 development configuration was already frozen before holdout execution:

- D4
- same-session 09:30
- trailing target
- 30% activation / 30% retracement

A branch audit found that the development engine correctly stops at 2020–2024 but did not contain the 2025–2026 holdout implementation. A separate holdout engine/workflow was therefore added without changing the frozen selector.

The first holdout run completed technically, but audit of the output found E034: the comparison rules were being evaluated on both D3 and D4 candidate entries. That mixes different entry-day populations and invalidates the first result.

The first result is formally rejected. The corrected engine now:
- evaluates D3 rules only on D3 candidate entries;
- evaluates the frozen T7 rule only on D4 candidate entries;
- includes D4 expiry-only as a descriptive decomposition;
- pairs rule comparisons by expiry, not by decision date;
- retains the frozen 2-point slippage / ₹20 brokerage primary case and 4-point / ₹30 stress;
- makes no holdout-driven parameter selection.

No holdout superiority claim is made from the rejected run.
