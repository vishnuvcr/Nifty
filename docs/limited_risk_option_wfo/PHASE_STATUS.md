# Limited-Risk Option WFO — Phase Status

Last updated: 2026-09-20 (Asia/Kolkata)

| Phase | Status | Notes |
|---|---|---|
| L0 Protocol freeze and repository audit | COMPLETE | New branch created from research/monte-carlo-wfa-v1; protocol artifacts added. |
| L1 Literature review and strategy taxonomy | COMPLETE | Literature and methodological references are frozen. |
| L2 Data audit and executable market-data layer | COMPLETE | Parent NIFTY archive will be audited in CI; current known schema is EOD close data rather than verified historical bid/ask. |
| L3 Strategy risk-audit engine | COMPLETE | Mechanical finite-loss classification is mandatory. |
| L4 WFO strategy-construction engine | COMPLETE | Existing MC/WFO methodology remains the baseline. |
| L5 Broad strategy WFO | COMPLETE | Descriptive all-candidate comparison; no final candidate promotion. |
| L6 Nested strategy/regime selection | COMPLETE | Selection must be frozen before any fresh holdout. |
| L7 Robustness and statistical inference | COMPLETE | CPCV + block bootstrap + multiple-testing controls. |
| L8 Fresh untouched holdout | HOLD | Must be outside the previously exposed 2026 period. |
| L9 Capital/margin/operational feasibility | COMPLETE — STRUCTURAL ONLY | Current Paytm Money assumptions must be re-verified before deployment. |
| L10 Prospective paper-trading specification | HOLD — NOT ELIGIBLE | Paper-only; no broker order submission. |
| L11 Final inference and manuscript | COMPLETE — PHASE MANUSCRIPT | Full manuscript with tables, graphs, appendices and supplements. |

## Branch

research/limited-risk-option-wfo-v1

## Parent

research/monte-carlo-wfa-v1

## Baseline parent commit

1cd5b322d5d2ac79caad060c659313822952de26

## Current status

**L0-L7 complete. L8 HOLD. L9 structural feasibility complete. L10 not eligible. L11 phase report complete.**

Verified clean CI run: **35496685719**.

Core result: 27/36 strategies pass the mechanical finite-loss audit. Historical candidates include Jade Lizard and Put Ratio Spread, but the cross-strategy multiple-testing diagnostic is not supportive (Reality-Check-style block-bootstrap p=0.7426).

No strategy is promoted. Fresh post-exposure data and deployment-grade bid/ask execution data are required before paper trading.
