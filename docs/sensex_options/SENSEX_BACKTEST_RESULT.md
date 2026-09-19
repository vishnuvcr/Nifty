# SENSEX Batman + Adaptive Transfer Backtest — Phase S5/S6 Result

## Executive result

The frozen NIFTY Monte-Carlo / regime-routing framework was transferred to SENSEX and executed successfully on the available public 1-minute SENSEX option dataset.

Two result layers are reported separately:

1. **Account-sized gate (₹1,00,000 capital, 2% risk budget):** the base SENSEX run produced no executable trades because the estimated ES95/ES99 risk of one SENSEX lot commonly exceeded the ₹2,000 per-trade risk budget.
2. **One-lot strategy-edge test:** to distinguish strategy edge from account affordability, S6 evaluated exactly one lot whenever the frozen MC net-EV gate was positive. This is *not* an account-sized trading result.

## Data actually available

- Validation: 11 usable expiries, from 2025-10-09 through 2025-12-24.
- Holdout: 20 usable expiries, from 2026-01-08 through 2026-05-21.
- Development: no usable observations because the frozen 756-session MC lookback cannot be reconstructed from the available primary SENSEX dataset for 2024.
- The advertised split therefore remains chronologically defined, but only the above observed periods can be interpreted.
- No SENSEX parameter was tuned on the holdout.

## Base execution model

- Entry: 09:30 IST, 3 trading sessions before actual expiry.
- Exit: expiry settlement using the SENSEX index close.
- MC: 5,000 bootstrap paths from the previous 756 daily log returns.
- Volatility regime: past-only 20-session annualized realized volatility ranked against the prior 252 observations.
- Slippage base: 0.50 option points per executed leg.
- Costs: brokerage, BSE transaction charges, STT, SEBI fee, stamp duty and GST.
- Historical quote limitation: OHLC data, not historical bid/ask; therefore execution is a bar-open + adverse-slippage proxy.

## Validation — one-lot edge

At 0.50-point slippage per leg:

| Measure | Adaptive |
|---|---:|
| Trades | 10 |
| Total P&L / one lot | ₹36,037.89 |
| Win rate | 60.0% |

Standalone Batman was evaluated for realized expiry P&L even when its MC gate rejected the trade. Across the 11 validation observations, Batman's mean realized P&L was ₹3,672.71 per lot, with 72.7% positive observations and total realized P&L of ₹40,399.86 per lot-equivalent evaluation. This is a diagnostic strategy-edge result, not a claim that the live router would have entered all 11 trades.

## Holdout — one-lot edge

At 0.50-point slippage per leg:

| Measure | Adaptive | Batman standalone |
|---|---:|---:|
| Trades selected by MC gate | 18 | 26 |
| Total realized P&L | ₹55,055.50 | ₹212,512.03 |
| Win rate | 66.7% | 84.6% |
| Period | 2026-01-08 to 2026-05-21 | same |

The standalone Batman diagnostic across all 33 evaluable holdout expiries had:

- mean P&L: ₹6,366.83 per lot
- median P&L: ₹5,444.18
- win rate: 81.8%
- profit factor: 3.14
- best observation: ₹29,017.74
- worst observation: -₹30,610.35

The 26-trade Batman subset represents only dates passing the frozen MC net-EV gate.

## Slippage robustness

The one-lot holdout result remained positive across the pre-registered 0.25/0.50/1.00/2.00 point-per-leg slippage grid.

| Slippage / leg | Adaptive trades | Adaptive P&L | Adaptive win rate | Batman trades | Batman P&L | Batman win rate |
|---:|---:|---:|---:|---:|---:|---:|
| 0.25 | 18 | ₹55,490.10 | 66.7% | 26 | ₹213,291.30 | 84.6% |
| 0.50 | 18 | ₹55,055.50 | 66.7% | 26 | ₹212,512.03 | 84.6% |
| 1.00 | 18 | ₹54,186.31 | 66.7% | 26 | ₹210,953.50 | 84.6% |
| 2.00 | 18 | ₹57,864.47 | 66.7% | 26 | ₹207,836.43 | 84.6% |

The adaptive P&L is not monotonic with slippage because the frozen MC selector can choose a different strategy as execution assumptions change. Batman's realized P&L declines monotonically across this grid, as expected.

## Capital-affordability result

With ₹1,00,000 capital and a 2% risk budget, the base gate often produced zero recommended lots because ES-based risk per SENSEX lot was much larger than ₹2,000.

Therefore:

> The SENSEX transfer test does **not** support the statement that these strategies are executable under the frozen ₹1 lakh / 2% risk-budget account specification.

That is a capital/risk-sizing constraint, separate from the per-lot strategy-edge result.

## Scientific interpretation

The available data provide a **promising transfer signal**, especially for the frozen Batman structure in the available 2026 holdout window, but the evidence is not sufficient for a strong generalization claim.

The principal reasons are:

1. The 2024 development period is unusable under the frozen 756-session lookback with the available dataset.
2. The validation sample contains only 11 usable expiries.
3. The holdout contains only 20 usable expiries through 2026-05-21.
4. The public dataset is not a reconstructed exchange bid/ask feed.
5. The one-lot edge test is deliberately not an account-sized performance test.
6. The public dataset is not a substitute for exchange-verified historical market data.

## Current conclusion

**Batman:** The transfer test shows positive realized one-lot performance in both the available validation and holdout windows, and the holdout result remains positive across the tested slippage range. This is evidence worth further validation, not a final claim of profitability.

**Adaptive:** The frozen regime router generated positive one-lot realized P&L in both available validation and holdout periods. Its holdout result was positive across the tested slippage grid. However, the actual ₹1 lakh account gate generated no trades, so additional capital/risk-budget analysis is required before treating it as an executable account strategy.

**₹1 lakh account:** No usable account-sized SENSEX strategy is established by this run because the frozen 2% risk budget generally cannot accommodate one SENSEX lot.

## Next research phase

The next phase should **not** retune Batman or the regime map on these results. It should instead obtain a longer, exchange-verified SENSEX option history and repeat the frozen protocol with:

- at least 756 prior sessions available before the first validation observation;
- complete expiry coverage;
- bid/ask or tick/level-1 data for execution reconstruction;
- date-accurate historical lot-size and charge schedules;
- an untouched multi-year holdout.

Only after that replication should the project consider capital scaling or any strategy-rule modification.
