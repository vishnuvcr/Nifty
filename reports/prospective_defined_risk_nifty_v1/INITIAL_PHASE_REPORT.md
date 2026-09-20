# NIFTY Defined-Risk Prospective Validation v1 — Initial Phase Report

## Status

The four strategies are frozen and the prospective observation infrastructure is active:

- Jade Lizard
- Put Ratio Spread
- Sell Put
- Bull Put Spread

Each has a separate paper ledger and GitHub Pages dashboard.

## Frozen model

- 09:30 IST entry.
- Three future trading sessions to expiry.
- 5,000 Monte Carlo paths.
- 756 completed daily log returns.
- Net MC-EV gate after execution and transaction-cost assumptions.
- One-lot paper observation.
- Expiry settlement benchmark.
- Missing data produces NO_TRADE.

## Prospective result boundary

On 2026-09-20, there are **no prospective closed-trade observations to report** from this newly frozen phase. No historical trades have been backfilled into the prospective ledgers.

This is deliberate: using the already-exposed historical period as if it were a new prospective holdout would contaminate the validation.

## Research decision

**ACTIVE PROSPECTIVE VALIDATION / NO PROMOTION YET.**

The first future eligible observations will be assessed under the frozen rules without re-selection.
