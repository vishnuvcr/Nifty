# T4 Nested Walk-Forward Plan

## Objective
Determine whether an exit rule selected from prior data continues to improve BATMAN relative to the frozen expiry-control exit without using the outer test year during selection.

## Development data
2020-2024 corrected T3 trade-level artifact only.

## Outer walk-forward years
2022, 2023 and 2024.

For each outer test year:
1. Training data are all earlier development years.
2. Select one exit variant from the complete 165-variant grid using only the training years.
3. Primary score: worst brokerage total net P&L across ₹10/₹20/₹30.
4. Tie-break 1: median brokerage total net P&L.
5. Tie-break 2: worst-brokerage maximum drawdown, preferring values closer to zero.
6. Tie-break 3: lower rule complexity.
7. Evaluate the selected variant on the untouched outer test year at all three brokerage levels.
8. Compare against expiry control on the exact same opportunities.

## Final development selection
After the outer walk-forward exercise, apply exactly the same pre-registered selection rule to all 2020-2024 development data. This produces a single frozen candidate for the untouched 2025-2026 holdout.

## Holdout
The 2025-2026 Rahul/Dhan minute-option archive is never used for T2/T3 selection. It is used only after the final development rule is frozen.

## Anti-leakage
No future holdout prices, quote availability, exits, or trade outcomes enter candidate selection. The final holdout is read only after T4 development selection is written to a frozen JSON file.

## Success criterion
T4 does not require a profitable development maximum. It requires an honest OOS measurement of whatever the pre-registered selector chooses.
