# Adaptive Paper Trading v1 — design and validation boundary

## Why this exists

The pre-2026 CPCV robustness phase showed positive pooled selected-strategy performance and positive block-bootstrap confidence bounds, but strategy identity was unstable across CPCV paths. The appropriate prospective test is therefore a regime-conditioned **candidate set**, not a newly invented single fixed mapping.

## Frozen candidate universe

| Regime | CPCV-selected candidates | Selection frequency across 15 paths |
|---|---|---|
| Low | Risk Reversal; Long Synthetic Future; Buy Call | 9; 4; 2 |
| Medium | Short Straddle; Put Ratio Spread; Short Strangle; Strip; Buy Put | 4; 4; 3; 3; 1 |
| High | Sell Put; Risk Reversal; Long Synthetic Future; Batman | 5; 5; 3; 2 |

These frequencies are descriptive diagnostics from the completed CPCV study. They are not treated as performance scores.

## Entry, gating and automation

The model uses the latest completed session before the entry date. New entry signals are generated at 09:30 IST on NIFTY trading weekdays. A separate 16:00 IST refresh job only settles matured paper trades and republishes the dashboards; it never creates a second entry signal. The front expiry must have exactly three future trading sessions remaining. The terminal distribution is generated from the previous 756 daily log returns using 5,000 bootstrap paths.

For every regime candidate:

1. Map the strategy's required MC quantiles to the nearest unique listed strikes.
2. Price buys from the ask and sells from the bid.
3. Subtract 2 option points per contract as stressed transaction cost.
4. Calculate net MC EV, MC POP, ES95 and ES99.
5. Size with `max(ES95, ES99)` and a 2% paper-account risk budget.
6. Mark the candidate eligible only if net MC EV is positive and at least one risk-sized lot fits.

The primary paper candidate is the eligible candidate with the highest net MC EV. That ranking rule is **not historically validated** and is being tested prospectively.

## Validation boundary

The 2026 holdout that was already used in earlier research is not reopened or re-optimized. This page is a new prospective collection layer. Any future promotion decision must use new observations collected after the existing cutoff and must be evaluated separately.

## Separation from Batman

Adaptive state is stored only under:

- `paper_trading/adaptive_*`
- `site/adaptive/*`

Batman state is stored only under:

- `paper_trading/batman_*`
- `site/batman/*`

Both pages are published together under one root selector so the two systems can be opened independently.
