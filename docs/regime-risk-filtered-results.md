# Regime Router Robustness and Risk-Filtered Candidate — V2 Run 9

Source dataset: strategy-regime-lab-v2 run 35425922439 on branch research/monte-carlo-wfa-v1.

## Phase 1 — rolling robustness result

The original volatility-only mapping was:

- High volatility → Short Strangle
- Medium volatility → Sell Put
- Low volatility → NO_TRADE

It was useful in the single fixed 2020–2022 / 2023–2024 / 2025+ split, but the rolling walk-forward robustness analysis did not support promoting that frozen mapping.

Robustness varied materially with lookback, regime thresholds and stress costs. Stable selections in pre-2026 folds frequently changed strategy, and the stable mappings that were obtained did not remain positive in the untouched 2026 holdout. Therefore the simple volatility-only router is retained as a historical research result, not as the final operational candidate.

## Phase 2 — risk-filtered regime router

The next step kept the strategy identities fixed and searched only for simple, past-only risk filters.

Frozen base strategies:
- High volatility → Short Strangle
- Medium volatility → Sell Put
- Low volatility → NO_TRADE

Filters:
- High volatility: allow Short Strangle only when the trailing p_expand rank is below a threshold.
- Medium volatility: allow Sell Put only when the trailing 60-session trend rank is above a threshold.
- Regime features are calculated from prior observations only.
- MC net-EV > 0 remains mandatory.
- Stress cost is tested at 1, 2, 3 and 4 option points per contract.

Selection was deliberately separated from the holdout:
- Selection years: 2024–2025.
- Untouched holdout: 2026.
- Minimum 10 gated trades in each selection year.
- Candidate must have positive mean P&L and PF > 1 in every selection year.
- The selected configuration is then evaluated on 2026 without using 2026 for parameter choice.

## Selected 2-point research candidate

At the frozen research transaction cost of 2 points/contract, the selected configuration is:

**252-session trailing ranks**

**High volatility** → Short Strangle only when p_expand rank < 0.50

**Medium volatility** → Sell Put only when trend60 rank > 0.20

**Low volatility** → NO_TRADE

This is a simple risk filter rather than a granular 2D strategy-selection map.

## Out-of-sample / holdout results

All P&L values below are strategy points per strategy unit after the specified stress cost; they are not rupee returns.

| Period | Trades | Mean net P&L | PF | Total net P&L |
|---|---:|---:|---:|---:|
| 2024 selection | 16 | +108.37 | 3.33 | +1,733.95 |
| 2025 selection | 19 | +102.67 | 5.01 | +1,950.65 |
| 2026 untouched holdout | 8 | +120.82 | 3.76 | +966.55 |

The 2026 result therefore remains positive after the filter was selected without using 2026 data.

## Transaction-cost sensitivity

| Stress cost | 2026 trades | 2026 mean | 2026 PF | 2026 total |
|---:|---:|---:|---:|---:|
| 1 | 8 | +122.82 | 3.82 | +982.55 |
| 2 | 8 | +120.82 | 3.76 | +966.55 |
| 3 | 8 | +118.82 | 3.70 | +950.55 |
| 4 | 8 | +116.82 | 3.64 | +934.55 |

The selected structure therefore remained positive under the tested higher transaction-cost assumptions.

## Lookback sensitivity

Using the same 0.50 / 0.20 filter thresholds and 2-point stress cost:

| Trailing lookback | 2026 trades | 2026 mean | 2026 PF | 2026 total |
|---:|---:|---:|---:|---:|
| 63 | 9 | +53.42 | 1.47 | +480.80 |
| 126 | 8 | +120.82 | 3.76 | +966.55 |
| 252 | 8 | +120.82 | 3.76 | +966.55 |

The candidate is not dependent on an extremely narrow 252-session choice, although the 252-session configuration has the stronger 2026 holdout result in this run.

## Filter versus unfiltered base router

At 252 sessions and 2-point stress cost:

| Year | Unfiltered mean / PF / total | Filtered mean / PF / total |
|---|---|---|
| 2024 | +84.42 / 2.52 / +2,194.80 | +108.37 / 3.33 / +1,733.95 |
| 2025 | +9.18 / 1.09 / +229.40 | +102.67 / 5.01 / +1,950.65 |
| 2026 holdout | -54.15 / 0.64 / -920.60 | +120.82 / 3.76 / +966.55 |

The filter reduces the number of trades, but in this run it also removes a large portion of the negative 2025–2026 observations.

## Current research conclusion

The useful result from this phase is not that a universal strategy has been discovered.

The current paper-research candidate is:

High volatility + low expansion rank → Short Strangle

Medium volatility + sufficiently positive 60-session trend rank → Sell Put

Low volatility → NO_TRADE

with 252-session trailing feature ranks, a 2-point/contract stress assumption, MC net-EV > 0 gating, and the existing ES95/ES99 risk-sizing framework.

The candidate is supported by the 2026 holdout in this run, but the holdout contains only 8 gated trades. That is too small to treat as evidence of stable future profitability.

## Next operational stage

The candidate should now be moved to prospective paper-trading validation with the existing signal-producer protocol:

1. Freeze information exactly at the 3-session-before-expiry decision point.
2. Use only entry-time quotes available at the decision time.
3. Apply the regime and risk filters.
4. Require MC net EV > 0.
5. Size using the existing ES95/ES99 and 2% risk-budget framework.
6. Record every signal, including NO_TRADE.
7. Hold to expiry under the frozen protocol.
8. Compare prospective results against the unfiltered router and the Batman baseline.

No live/broker execution should be enabled by this research result.
