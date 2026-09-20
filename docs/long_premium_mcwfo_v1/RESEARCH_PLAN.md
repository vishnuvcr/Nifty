# NIFTY Long-Premium MC/WFO Research v1

## Research question

Can the frozen NIFTY Monte Carlo / walk-forward forecast identify situations where buying a sufficiently cheap NIFTY call or put has positive expected value after option premium, brokerage, slippage/execution stress, and expiry time decay?

## Why this is a separate study

This branch is deliberately independent of the four fixed limited-risk prospective candidates. It tests the simplest finite-loss directional structures:

- Buy Call
- Buy Put

The maximum loss is the premium paid. The upside/downside asymmetry is evaluated by the realised expiry payoff. Time decay is not subtracted a second time: the historical realized P&L already contains the paid premium and expiry intrinsic value.

## Aims

1. Test whether the MC terminal distribution identifies option purchases with positive net expected value.
2. Test whether the relationship survives a cheapness constraint based on premium as a fraction of spot.
3. Separate development selection from validation and the already-exposed 2025-2026 period.
4. Include explicit execution stress and brokerage.
5. Control for multiple cheapness rules.
6. Establish whether a fresh post-exposure holdout could ever justify prospective validation.

## Frozen protocol

- Parent MC/WFO strategy artifact: run 35425922439.
- Parent MC: 5,000 bootstrap paths and 756 completed daily log returns.
- Candidate universe: Buy Call and Buy Put only.
- Entry decision: inherited parent strategy-lab observation.
- Baseline lot size: 65.
- Baseline execution stress: 2.0 option points per contract.
- Baseline round-trip brokerage: ₹10 per executed order, two orders, converted to points using lot size.
- Baseline total execution stress: 2.307692 points/trade.
- Cheapness rules: premium <= 0.30% through 0.80% of spot in 0.05 percentage-point increments.
- Development: through 2022.
- Validation: 2023-2024.
- Exposed final: 2025-2026, descriptive only.
- Minimum development candidate size: 20 gated observations.
- Selection score: mean net P&L minus one standard error.
- Minimum validation size for a pass: 20.
- Validation pass requires positive mean and PF > 1.
- Multiple-testing: moving-block max-statistic Reality-Check-style bootstrap across all 22 predeclared rules.
- This implementation is not claimed to be a full Hansen SPA.

## Acceptance boundary

A positive historical result is hypothesis-generating only. No strategy can be promoted to prospective trading from this phase without a fresh, previously unexposed holdout and deployment-grade historical bid/ask evidence.

## Required outputs

- complete rule grid;
- development-only selection table;
- frozen selected rule;
- validation statistics and uncertainty;
- post-hoc validation diagnostics explicitly labelled as such;
- multiple-testing diagnostic;
- cost sensitivity;
- final report;
- error and conversation logs.
