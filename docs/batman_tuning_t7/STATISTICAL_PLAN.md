# T7 Statistical Plan

## Primary development selection
For each candidate configuration, use all training trades and all three brokerage scenarios.

Primary: worst-case mean net P&L per unique decision date across ₹10/₹20/₹30.

Secondary: worst-case total net P&L.

Tertiary: worst-case maximum drawdown at ₹30/order.

Quaternary: lower rule complexity.

Minimum training sample: 25 unique decision dates.

## Outer OOS
Years 2022, 2023 and 2024 are never read during selection for that fold.

Report selected versus D3/09:30/expiry control on matched calendar years.

## Holdout
The final 2020-2024-selected configuration is frozen to JSON before the 2025-2026 holdout.

No significance threshold is used to choose the winner; inference is performed only after selection.
