# T5 Final Robustness Conclusion

## Frozen holdout result

The development-frozen BATMAN rule was:

- D3 relative to the target expiry.
- Same-session 09:30 signal.
- 5,000 Monte Carlo paths.
- 756 completed daily NIFTY log-return lookback.
- Gross MC-EV > 0 entry gate.
- BATMAN legs: +1 P35 PE, -2 P20 PE, +1 C65 CE, -2 C80 CE.
- Trailing target: activate at 20% of maximum-profit reference and exit after a 10% retracement.

This rule was frozen before the 2025-2026 holdout was read.

## Holdout result

The untouched holdout produced 7 eligible trades from 2025-01-27 through 2026-04-01.

At ₹20 per executed F&O order:
- Total net P&L: ₹38,075.33
- Mean net P&L/trade: ₹5,439.33
- Median: ₹4,655.08
- Observed wins: 7/7
- Exact 95% Clopper-Pearson win-rate interval: 59.0% to 100%
- 95% t interval for mean trade P&L: approximately ₹2,976 to ₹7,903
- Largest trade share of total P&L: 28.4%
- Removing any one trade still leaves positive pooled P&L.

The sample is too small for the observed 100% win rate to constitute strong evidence. Bootstrap inference is reported only as exploratory.

## Brokerage stress

At ₹10, ₹20 and ₹30 per executed order, total net P&L was approximately:
- ₹38,635
- ₹38,075
- ₹37,515

Paytm Money's current F&O FAQ states ₹10 brokerage per unique executed F&O order; the higher figures are therefore stress scenarios rather than the primary assumption.

## Slippage stress

Starting from the tested 2-point adverse slippage assumption, an additional conservative slippage stress of 4 premium points per execution still left pooled net P&L positive at approximately ₹22,235.

This stress deliberately does not credit any compensating reduction in STT, making it conservative.

## Paired expiry-control comparison

A same-entry expiry-control benchmark could be reconstructed for 6 of the 7 holdout trades.

At ₹20/order:
- Frozen trailing-target: approximately ₹33,420
- Expiry control: approximately ₹80,917
- Paired difference: approximately −₹47,497
- Mean paired difference: approximately −₹7,916
- 95% t interval for paired mean difference: approximately −₹21,341 to +₹5,508
- Selected exit win rate: 100%
- Expiry-control win rate: 83.3%

One holdout trade did not have a fully reconstructable expiry-control exit under the available expiry-day executable quotes, so it was not included in this paired comparison.

## Scientific decision

The frozen trailing-target rule is **not promoted as an improved replacement for the expiry-control exit**.

The holdout demonstrates positive realized P&L for the frozen rule, but the paired comparison does not show that the selected exit improves the same-entry result; in fact, the reconstructed expiry-control total is materially larger in this small paired sample.

Therefore:
- The 2025-2026 result is evidence that the frozen entry + trailing-target combination can be profitable in this small sample.
- It is not sufficient evidence for robust superiority.
- No change is made to the already frozen prospective BATMAN control stream.
- The exit rule remains a research candidate rather than a production-promoted replacement.

## Main limitation

The dominant limitation is not missing data. The source layer was successfully reconstructed.

The dominant limitation is the **very small number of eligible holdout trades**: 7. Most otherwise possible opportunities failed because the required MC-derived strike grid or one of the four option legs was unavailable in the minute dataset. This sharply limits statistical power and generalizability.

The next research direction is therefore a new, independently frozen phase testing entry/exit variants designed to improve opportunity coverage while preserving the same anti-lookahead and cost/slippage controls, rather than tuning the already observed holdout.
