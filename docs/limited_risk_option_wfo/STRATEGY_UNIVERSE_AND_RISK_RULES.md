# Strategy Universe and Risk Rules

## 1. Source universe

The starting universe is the 36 strategies currently declared in src/nifty_mc/strategy_catalog.py on the parent NIFTY MC-WFO branch.

The declared universe must be versioned at the first L3 run. Any addition/removal after that point requires a new protocol revision.

## 2. Risk classes

| Class | Definition | Examples from current catalog | Core-study status |
|---|---|---|---|
| R1 | Limited max loss + potentially unlimited profit | Buy Call, Buy Put, Long Straddle, Long Strangle, Strip, Strap, Call Ratio Back Spread, Put Ratio Back Spread | Eligible subject to mechanical audit |
| R2 | Limited max loss + limited max profit | Bull/Bear Call/Put Spreads, Bull/Bear Condors, Bull/Bear Butterflies, Long Iron Butterfly, Long Iron Condor, Iron Butterfly, Short Iron Condor | Eligible subject to mechanical audit |
| R3 | Limited loss but path-/multi-expiry-dependent | Long Calendar with Calls/Puts | Separate sub-study |
| X | Unbounded adverse loss under declared structure | Batman, Short Straddle, Short Strangle, Call Ratio Spread, Put Ratio Spread, Jade Lizard, Reverse Jade Lizard, Long Synthetic Future, Short Synthetic Future, Risk Reversal | Excluded from core |

## 3. Mechanical audit requirements

For every candidate:
- build the exact leg list from strategy_catalog.py;
- calculate net premium cashflow from executable quotes;
- evaluate payoff on a sufficiently wide grid;
- evaluate limiting slopes in both tails;
- identify maximum loss and maximum profit;
- verify against an analytical formula where available;
- fail closed if the result is ambiguous.

Required fields:
strategy, risk_class, audit_status, max_loss_points, max_profit_points, profit_unbounded, loss_unbounded, worst_case_underlying_region, contracts_per_unit, premium_cashflow, entry_cost, stress_slippage.

## 4. Strategy-specific notes

### Buy Call / Buy Put
Finite maximum loss equal to net premium paid; profit is unbounded on the favorable tail for the appropriate option.

### Long Straddle / Long Strangle
Finite maximum loss equal to total premium/debit after execution costs; upside is unbounded.

### Strip / Strap
Finite loss determined by the net debit under the actual entry convention; upside is unbounded on at least one tail. Exact risk must still be audited.

### Ratio Backspreads
Potentially finite maximum loss and unbounded favorable-tail profit, but eligibility depends on actual strike spacing and net premium. The auditor must not infer safety from the strategy name.

### Debit/Credit Spreads, Condors and Butterflies
Finite loss is expected from the structure, but the actual rupee maximum must include entry costs and exact leg quantities.

### Calendars
Treat as R3 because terminal payoff depends on different expiries and time value. Do not use a single-expiry intrinsic-value approximation.

## 5. Position-sizing rule

For the limited-risk core, the hard per-trade risk budget is:
maximum verified loss per strategy unit + modeled execution/cost reserve.

Never use MC ES95/ES99 as a substitute for a known maximum loss. ES is a secondary diagnostic; the finite structural maximum loss is the primary sizing constraint.
