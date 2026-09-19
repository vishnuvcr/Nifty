# Batman 3-session MC-EV Paper-Trading Candidate

## Status

This is the first strategy in the current research branch that is suitable for prospective paper trading under an explicit, reproducible rule set.

It is not a guarantee of future profitability and has not yet been validated on data after the historical dataset end date of 2026-03-30.

## Fixed entry rules

1. Use the 3rd trading session before the target NIFTY expiry.
2. Bootstrap the most recent 756 NIFTY daily log returns.
3. Simulate 5,000 terminal index paths to the target expiry.
4. Use the Monte Carlo terminal quantiles:
   - P20 -> short 2 PE
   - P35 -> long 1 PE
   - P65 -> long 1 CE
   - P80 -> short 2 CE
5. Enter only when the Monte Carlo expected P&L of the complete Batman structure is positive.
6. Compute MC ES95 and ES99 for risk budgeting.
7. Position size from a predefined capital-risk budget. Because Batman has theoretically unbounded tail loss, ES95/ES99 is a sizing proxy, not a hard maximum-loss guarantee.
8. Skip the trade when required strikes or valid premiums are unavailable.

## Structure

For one strategy unit:

- Buy 1 x P35
- Sell 2 x P20
- Buy 1 x C65
- Sell 2 x C80

The quantities mean six option contracts per strategy unit.

The paper-trading engine is implemented in scripts/batman_paper_signal.py.

## Historical research result

Using the V2 #7 strategy observations, restricted to:

- 3-session entry offset
- Batman
- MC expected P&L > 0

and applying a 2-point-per-contract execution-cost stress:

| Period | Trades | Mean P&L | Total P&L | Win rate | Profit factor |
|---|---:|---:|---:|---:|---:|
| Development 2020-2022 | 38 | +18.48 | +702.30 | 60.5% | 1.48 |
| Validation 2023-2024 | 20 | +50.72 | +1,014.45 | 80.0% | 3.62 |
| Final 2025-2026* | 17 | +50.30 | +855.10 | 82.4% | 3.94 |
| Combined OOS | 37 | +50.53 | +1,869.55 | 81.1% | 3.76 |

A 100,000-resample bootstrap of the pooled OOS P&L gave an estimated probability of a positive total P&L of approximately 0.997, with the 5th percentile of the bootstrap total still positive.

*The available final dataset ends on 2026-03-30, so this is not a full-calendar-year 2026 test.

## Important limitation

Batman is not a defined-risk structure. Extreme movement through one side can produce losses larger than the initial premium cashflow.

Therefore the operational next step is paper trading with ES-based position sizing and an explicit capital/risk limit, not unrestricted live deployment.

## Current NIFTY contract size

NSE revised the NIFTY lot size from 75 to 65 for revised contracts in late 2025. The current NSE contract-information page is the authoritative source for the applicable lot size of a contract before placing a trade.

## Research provenance

- NIFTY multi-strategy V2 implementation: scripts/run_strategy_regime_lab_v2.py
- Strategy definition: src/nifty_mc/strategy_catalog.py
- Paper signal engine: scripts/batman_paper_signal.py
- V2 artifact used for this candidate: strategy-regime-lab-v2 #7
