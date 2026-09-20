# NIFTY Defined-Risk Prospective Validation v1

## Purpose

Observe the two strategies retained for the prospective phase from the limited-risk research without changing their rules after seeing future outcomes. The prospective scope was narrowed before the first eligible observation; no prospective outcome was used for this change.

Current frozen candidates:
1. Jade Lizard
2. Put Ratio Spread

Superseded pre-observation candidates: Sell Put and Bull Put Spread. They remain historical limited-risk research results only and are not part of this prospective validation.

They are evaluated independently. There is no further selection between the four in the prospective phase.

## Research question

Do the two frozen finite-loss NIFTY strategies retain positive net performance prospectively when the MC/WFO rule, strike mapping, costs, and entry timing are frozen in advance?

## Frozen entry protocol

- Entry time: 09:30 IST on the exact day that is three future NIFTY trading sessions before the selected expiry.
- Model cutoff: prior completed NIFTY 50 session close.
- Monte Carlo: 5,000 bootstrap paths using the last 756 completed daily log returns.
- Strike mapping:
  - Jade Lizard: P35, C65, C90.
  - Put Ratio Spread: ATM, P35.
- Each retained strategy is evaluated independently; a positive MC EV does not cause the other retained strategy to be dropped.
- Signal: ENTER when net MC EV > 0 and all required executable quotes are present.
- One-lot paper observation per candidate.
- Exit: expiry settlement only for the common prospective benchmark.
- Missing quotes/data: NO_TRADE, never imputed.

## Costs

The prospective entry proxy uses:
- 2.0 adverse option points per contract as the frozen NIFTY execution/slippage stress.
- Paytm Money brokerage assumption: ₹10 per executed F&O order.
- Round-trip brokerage is charged conservatively as two executed orders per strategy leg.
- NSE option-sale STT is incorporated for short option entry and the current exercise-STT rule is applied to long legs at expiry where applicable.
- Other statutory charges are retained as explicit fields/configuration and are not silently set from historical P&L.

Current broker/exchange rates must be re-verified before any real-money deployment.

## Evaluation

For each candidate, maintain:
- number of eligible signals;
- number of NO_TRADE observations;
- net P&L;
- mean/median P&L;
- win rate;
- profit factor;
- maximum drawdown;
- maximum observed loss;
- cumulative P&L;
- MC EV calibration;
- MC POP versus realized hit rate;
- results by volatility regime;
- results by calendar period.

No prospective strategy can be promoted from a small sample or because it is outperforming another frozen candidate.

## Scientific boundary

This is prospective validation, not a new optimization phase. Any parameter change requires a new frozen branch and a new validation boundary.

## Scope-change record — 2026-09-20

The prospective scope was narrowed from four candidates to two — Jade Lizard and Put Ratio Spread — before the first eligible prospective observation. Sell Put and Bull Put Spread are excluded from all future prospective scans, ledgers and Pages dashboards. This is a protocol/configuration change made before observing prospective outcomes, not a result-driven selection.
