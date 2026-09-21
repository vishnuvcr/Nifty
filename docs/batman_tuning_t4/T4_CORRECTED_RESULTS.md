# T4 Corrected Nested-WFO Results

## Final development selection

The corrected selector, applied to the accepted T3 2020-2024 development artifact, selected:

**Exit family:** trailing target  
**Activation:** 20% of maximum-profit reference  
**Retracement:** 10% of maximum-profit reference  
**Entry:** frozen D3 / same-session 09:30 BATMAN gross-MC-EV gate

At all three brokerage stresses the development totals were:

- ₹10/order: ₹33,799.55
- ₹20/order: ₹28,279.55
- ₹30/order: ₹22,759.55

The worst-brokerage development total was ₹22,759.55.

The corrected selector counted 69 unique development trades.

## Outer walk-forward

| Outer year | Selected rule | ₹10 total | ₹20 total | ₹30 total | Control ₹20 | Selected minus control ₹20 |
|---|---|---:|---:|---:|---:|---:|
| 2022 | 20% activation / 10% retracement | ₹17,340 | ₹16,300 | ₹15,260 | −₹7,032 | +₹23,332 |
| 2023 | 20% activation / 10% retracement | ₹1,322 | ₹1,242 | ₹1,162 | ₹1,853 | −₹611 |
| 2024 | 20% activation / 10% retracement | ₹7,593 | ₹6,713 | ₹5,833 | ₹17,550 | −₹10,836 |

The outer sample sizes are small in 2023 and 2024. These results are evidence for holdout testing, not conclusive stability proof.

## Decision

The rule is now frozen for the untouched 2025-2026 holdout.

No future holdout price, exit, or P&L has influenced this choice.
