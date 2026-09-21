# BATMAN Tuning T3 — Exit Management Research Plan

## Aim
Determine whether pre-registered fixed or trailing exit rules materially improve the realized, net-of-cost distribution of the frozen operational BATMAN D3/09:30 entry control.

## Scope
T3 uses only the 2020-01-01 through 2024-10-31 Ayush NIFTY option/spot archive. The 2025-2026 Rahul archive remains an untouched outer holdout for later nested walk-forward validation.

## Frozen entry control
- D3 relative to target expiry.
- Same-session 09:30 NIFTY spot signal.
- 5,000 Monte Carlo paths from the latest 756 completed daily NIFTY log returns.
- Quantiles P20/P35/P65/P80.
- BATMAN legs: +1 P35 PE, -2 P20 PE, +1 C65 CE, -2 C80 CE.
- Primary entry gate: gross MC expected P&L > 0.
- Entry execution: first positive-volume observation strictly after 09:30, using bar OPEN.
- Two premium points of adverse slippage per option leg.

## Exit candidates
Control: hold to expiry-session final executable option mark.

Fixed target: 10, 20, 30, 40, 50, 60, 75% of the pre-declared reference maximum-profit objective.

Fixed stop: 10, 20, 30, 40, 50, 75, 100% of MC ES95 loss reference.

Fixed target + stop: full 7 × 7 grid.

Trailing stop: 10, 20, 30, 40, 50% of maximum-profit reference.

Trailing target: activation 20, 30, 40, 50% of favorable move; retracement 10, 20, 30%.

Trailing target + fixed stop: 7 fixed-stop distances × 12 trailing-target parameter pairs.

The full pre-registered grid therefore contains 165 exit variants including the expiry control.

## Causal execution
A trigger can use only option marks timestamped at or after the completed entry and before the trigger timestamp. Once a trigger is reached, each leg exits on its first positive-volume observation strictly after the trigger, using that observation's OPEN with adverse slippage.

Expiry control exits each leg at the last positive-volume observation available by 15:29 on the expiry session.

## Costs
Every result is net of:
- entry brokerage;
- exit brokerage;
- option-sale STT at the historical rate;
- adverse slippage on each entry and exit leg.

Report at ₹10, ₹20 and ₹30 per executed F&O order.

## Primary analysis
The control comparison is paired on identical eligible D3/09:30 opportunities. T3 is descriptive/selection-stage research only; no exit variant is promoted before nested WFO in T4.

## Outputs
Trade-level exit outcomes, MAE/MFE, holding time, trigger reasons, candidate summaries, brokerage sensitivity, skip diagnostics and a frozen T3 selection table for T4.
