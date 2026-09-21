# BATMAN T7 — Corrected Untouched Holdout Report

## Status

T7 development selection was frozen before any 2025–2026 holdout observation was used.

Frozen selection:
- Entry: D4 relative to target expiry.
- Timing: same-session 09:30 signal, first executable observation after 09:30.
- Exit: trailing target, activate at 30% of maximum-profit reference, retrace 30%.
- Monte Carlo: 5,000 paths, 756 completed daily log returns.
- Entry gate: gross MC expected P&L > 0.
- Costs: historical lot-size changes, option-sale STT, 8 executed F&O orders per round trip, ₹10/₹20/₹30 brokerage stress.
- Primary slippage: 2 adverse premium points per option leg.
- Stress slippage: 4 adverse premium points per option leg.

The first technically successful holdout run (Actions run 35622342772) was rejected under E034 because it evaluated rules on the wrong entry-day populations. The corrected run is Actions run 35622783758 and is the only holdout result accepted for inference.

## Corrected holdout coverage

- Expiry candidates: 82.
- D3/D4 requests: 162.
- Gross-MC gate-passing entry candidates: 80.
- Holdout decision coverage begins 2025-01-10 and extends through 2026-07-21.
- At the primary 2-point slippage / ₹20 brokerage case:
  - Original D3/09:30/expiry: 26 trades.
  - Prior D3/09:30/trailing 20%→10%: 28 trades.
  - D4/09:30/expiry decomposition: 28 trades.
  - Frozen T7 D4/09:30/trailing 30%→30%: 29 trades.

A large number of otherwise possible opportunities fail the gross MC gate or lack the required executable exit/fallback quotes. This is a material coverage limitation.

## Primary case — 2-point adverse slippage, ₹20/order

| Rule | Trades | Total net P&L | Mean/trade | Median | Win rate |
|---|---:|---:|---:|---:|---:|
| Original BATMAN: D3 / 09:30 / expiry | 26 | ₹148,119.05 | ₹5,696.89 | ₹4,325.16 | 88.5% |
| Prior candidate: D3 / 09:30 / trailing 20%→10% | 28 | ₹73,002.40 | ₹2,607.23 | ₹2,240.91 | 96.4% |
| D4 / 09:30 / expiry control | 28 | ₹144,552.29 | ₹5,162.58 | ₹4,712.58 | 78.6% |
| Frozen T7: D4 / 09:30 / trailing 30%→30% | 29 | ₹110,624.93 | ₹3,814.65 | ₹4,092.58 | 72.4% |

The frozen T7 rule is profitable, but the holdout does not show that its exit-management rule improves the D4 entry: D4 expiry control earned approximately ₹144.6k versus ₹110.6k for T7.

The original D3/09:30/expiry control also earned more pooled net P&L and higher mean P&L per trade than the frozen T7 candidate.

## Brokerage stress

For the frozen T7 candidate, total net P&L at 2-point slippage was:
- ₹10/order: ₹112,944.93
- ₹20/order: ₹110,624.93
- ₹30/order: ₹108,304.93

The conclusion is therefore not dependent on choosing the lowest brokerage stress.

## Slippage stress

At 4-point adverse slippage per option leg and ₹30/order:
- Original D3/09:30/expiry: ₹107,768.61 total.
- Prior D3/09:30/trailing 20%→10%: ₹25,042.33.
- D4 expiry control: ₹100,242.20.
- Frozen T7: ₹64,116.57.

T7 remains profitable under this conservative stress, but still does not exceed either expiry-control benchmark.

## Calendar stability

At the primary cost case, frozen T7 net P&L was positive in both calendar years:
- 2025: ₹68,355.33 across 18 trades.
- 2026: ₹42,269.60 across 11 trades.

The positive year totals do not establish robust superiority because the sample remains small and opportunity coverage is incomplete.

## Exit decomposition

The most direct exit test compares the frozen D4 entry under the two exits on the same 28 expiries for which both exit calculations were reconstructable.

Frozen T7 minus D4 expiry control:
- Total paired difference: −₹33,000.42.
- Mean paired difference: −₹1,178.59 per matched expiry.
- Median paired difference: ₹0, because many T7 trades fell back to expiry.
- Bootstrap 95% interval for the paired mean difference: approximately −₹3,318 to +₹311.
- Wilcoxon signed-rank p-value: 0.753.

Thus the corrected holdout does not provide evidence that the 30%/30% trailing target improves the D4 entry over simply holding to expiry.

## Entry-day decomposition

A descriptive expiry-matched comparison of D4 expiry versus D3 expiry was possible on 15 common expiries:
- D4 expiry minus D3 expiry: +₹20,855.12 total.
- Mean paired difference: +₹1,390.34.
- Bootstrap 95% interval: approximately −₹1,975 to +₹4,625.
- Wilcoxon p-value: 0.421.

This suggests that the D4 entry is not obviously harmful on the overlapping expiries, but the holdout is far too small to establish a reliable entry-day advantage.

## Comparison with the prior D3 trailing candidate

On the 15 expiries where both prior D3 trailing and T7 D4 trailing were reconstructable:
- T7 minus prior D3 trailing: +₹44,170.33 total.
- Mean paired difference: +₹2,944.69.
- Bootstrap 95% interval: approximately +₹450 to +₹5,480.
- Wilcoxon p-value: 0.055.

So T7 is materially better than the previously tested D3 20%/10% trailing candidate on this matched subset, but this does not overturn the comparison with the original expiry-control rule.

## Robustness

Primary-case bootstrap 95% intervals for mean trade P&L:
- Original BATMAN: approximately ₹2,926 to ₹8,552.
- D3 trailing 20%/10%: approximately ₹978 to ₹3,978.
- D4 expiry: approximately ₹3,305 to ₹7,216.
- Frozen T7: approximately ₹1,707 to ₹5,821.

Leave-one-best-trade-out pooled P&L remains positive for all four rules at the primary cost case, so no conclusion depends on a single largest winner.

## Scientific decision

**T7 does not justify replacing original BATMAN with the frozen D4 / 09:30 / trailing 30%→30% configuration.**

The defensible conclusions are:

1. The joint tuning produced a real, independently frozen candidate: D4 / 09:30 / trailing 30%→30%.
2. That frozen candidate generated positive 2025–2026 holdout P&L after the declared costs and 2-point adverse slippage.
3. It also remained positive under 4-point slippage and ₹30 brokerage stress.
4. However, the selected trailing exit did not improve the same D4 entry versus expiry exit.
5. The original D3 / 09:30 / expiry control remained stronger on the corrected holdout in pooled net P&L and mean P&L per trade.
6. The prior D3 trailing candidate was weaker than T7 on the overlapping expiries, but that is a secondary comparison and not sufficient to establish a replacement.

### Final T7 status

**NOT PROMOTED.**

No post-holdout parameter was changed.

## Limitations

The main limitation is sparse executable opportunity coverage. Of 162 D3/D4 requests, only 80 passed the gross MC entry gate, and further candidates were lost when executable expiry/fallback quotes were unavailable. Several comparisons therefore use small matched-expiry samples.

The holdout ends at 2026-07-21, matching the available option archive. This is an untouched historical holdout, not a live paper-trading sample.

## Next research direction

A future phase should be independently frozen and should target opportunity coverage and alternative entry construction rather than further tuning the already observed 30%/30% trailing parameters.

