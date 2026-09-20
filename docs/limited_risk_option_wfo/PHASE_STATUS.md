# Limited-Risk Option WFO — Phase Status

Last updated: 2026-09-20 (Asia/Kolkata)

| Phase | Status | Notes |
|---|---|---|
| L0 Protocol freeze and repository audit | COMPLETE | New branch created from research/monte-carlo-wfa-v1; protocol artifacts added. |
| L1 Literature review and strategy taxonomy | COMPLETE | Literature and methodological references are frozen. |
| L2 Data audit and executable market-data layer | IN PROGRESS | Parent NIFTY archive will be audited in CI; current known schema is EOD close data rather than verified historical bid/ask. |
| L3 Strategy risk-audit engine | PLANNED | Mechanical finite-loss classification is mandatory. |
| L4 WFO strategy-construction engine | PLANNED | Existing MC/WFO methodology remains the baseline. |
| L5 Broad strategy WFO | PLANNED | Descriptive all-candidate comparison; no final candidate promotion. |
| L6 Nested strategy/regime selection | PLANNED | Selection must be frozen before any fresh holdout. |
| L7 Robustness and statistical inference | PLANNED | CPCV + block bootstrap + multiple-testing controls. |
| L8 Fresh untouched holdout | PLANNED | Must be outside the previously exposed 2026 period. |
| L9 Capital/margin/operational feasibility | PLANNED | Current Paytm Money assumptions must be re-verified before deployment. |
| L10 Prospective paper-trading specification | PLANNED | Paper-only; no broker order submission. |
| L11 Final inference and manuscript | PLANNED | Full manuscript with tables, graphs, appendices and supplements. |

## Branch

research/limited-risk-option-wfo-v1

## Parent

research/monte-carlo-wfa-v1

## Baseline parent commit

1cd5b322d5d2ac79caad060c659313822952de26

## Current status

**Protocol-only branch. No new performance result is claimed.**

The next executable step is L1 literature review and strategy taxonomy, followed by L2/L3 data and mechanical risk validation before any strategy ranking is permitted.
