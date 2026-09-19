# Regime-Specific Strategy Results — V2 Run 9

Source: `strategy-regime-lab-v2` run **35425922439** on branch `research/monte-carlo-wfa-v1`.

## Method

- All 36 strategies were evaluated.
- Entry timing remains the frozen 3-session-before-expiry decision point.
- Monte Carlo: 5,000 paths, 756-session return lookback.
- Stress cost: 2 option points per contract.
- Trade gate: net MC EV > 0 after stress cost.
- Regimes are classified using trailing, past-only ranks of trend and volatility features.
- Development: 2020–2022.
- Validation: 2023–2024.
- Final holdout: 2025 onward.
- A strategy is selected for a regime from development candidates, then screened on validation. The final period is not used for selection.

## Volatility regimes

### High volatility → Short Strangle

Validation:
- n = 20
- Mean net P&L = +138.96 points/trade
- PF = 5.51

Final holdout:
- n = 32
- Mean net P&L = +35.65 points/trade
- Total = +1,140.70 points
- Win rate = 59.38%
- PF = 1.29

### Medium volatility → Sell Put

Validation:
- n = 11
- Mean net P&L = +87.36 points/trade
- PF = 3.50

Final holdout:
- n = 13
- Mean net P&L = +26.90 points/trade
- Total = +349.75 points
- Win rate = 76.92%
- PF = 1.48

### Low volatility → NO_TRADE

The development→validation process identified candidates, but the best validation candidate did not survive the final holdout:

- Best validation candidate: Buy Call
- Validation mean: +20.48 points/trade
- Final mean: -30.93 points/trade
- Final PF: 0.68

Therefore low-volatility is currently treated as **NO_TRADE**.

## Direction regimes

The only direction-only mapping that survived both validation and final holdout was:

### Neutral direction → Jade Lizard

Validation:
- n = 17
- Mean net P&L = +88.68 points/trade
- PF = 3.48

Final holdout:
- n = 16
- Mean net P&L = +14.77 points/trade
- Total = +236.30 points
- Win rate = 62.50%
- PF = 1.15

Other direction candidates did not remain positive in the final holdout under the frozen selection procedure.

## Important interpretation

The evidence does **not** support one universal strategy.

The strongest regime-specific findings are:

| Regime lens | Regime | Strategy | Final mean P&L | Final PF | Current status |
|---|---|---|---:|---:|---|
| Volatility | High | Short Strangle | +35.65 | 1.29 | Retain for paper research |
| Volatility | Medium | Sell Put | +26.90 | 1.48 | Retain for paper research |
| Volatility | Low | — | -30.93 for best validation candidate | 0.68 | NO_TRADE |
| Direction | Neutral | Jade Lizard | +14.77 | 1.15 | Retain as separate direction-based candidate |

The 2D direction×volatility cells were too sparse/unstable to justify a more granular frozen router yet. Therefore the current evidence supports **regime-dependent strategy selection at the volatility level**, with the neutral-direction Jade Lizard as a separate secondary candidate rather than combining the two rules into one over-fitted router.

These are paper-trading research results, not guarantees of future profitability. Short Strangle and Sell Put have substantial tail risk and require strict predefined risk limits.

## Robustness status update

The volatility-only mapping documented above is a **historical run-9 selection snapshot**, not the final promoted router. A subsequent rolling walk-forward robustness phase varied lookback, regime thresholds and stress costs. The simple frozen mapping did not remain stable and positive in the untouched 2026 holdout, so it was **not promoted**.

The next research phase added simple past-only risk filters while keeping the strategy identities fixed. The resulting candidate is documented in `docs/regime-risk-filtered-results.md` and is the current paper-research candidate.
