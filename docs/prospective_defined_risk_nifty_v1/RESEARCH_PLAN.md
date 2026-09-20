# NIFTY Defined-Risk Prospective Validation v1

## Purpose

Freeze four strategies that already passed the limited-risk development-to-validation screen and observe them prospectively without changing their rules after seeing future outcomes.

Frozen candidates:
1. Jade Lizard
2. Put Ratio Spread
3. Sell Put
4. Bull Put Spread

They are evaluated independently. There is no further selection between the four in the prospective phase.

## Research question

Do the four frozen finite-loss NIFTY strategies retain positive net performance prospectively when the MC/WFO rule, strike mapping, costs, and entry timing are frozen in advance?

## Frozen entry protocol

- Entry time: 09:30 IST on the exact day that is three future NIFTY trading sessions before the selected expiry.
- Model cutoff: prior completed NIFTY 50 session close.
- Monte Carlo: 5,000 bootstrap paths using the last 756 completed daily log returns.
- Strike mapping:
  - Jade Lizard: P35, C65, C90.
  - Put Ratio Spread: ATM, P35.
  - Sell Put: ATM.
  - Bull Put Spread: P35, P10.
- Each strategy is evaluated independently; a positive MC EV does not cause any other strategy to be dropped.
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
