# SENSEX Options Research Phase Status

Last updated: 2026-09-20 (Asia/Kolkata)

| Phase | Status | Evidence / next gate |
|---|---|---|
| S0 Transfer specification freeze | COMPLETE | Frozen parent branch tip and producer/config blob SHAs recorded in FROZEN_PROVENANCE.md. |
| S1 Data-source and contract audit | IN PROGRESS | BSE provides an equity-derivatives Bhav Copy schema, while historical executable bid/ask/intraday data may require an exchange data product or licensed feed. Contract/expiry history is being audited date-by-date. |
| S2 Execution-cost model | NOT STARTED | Source Paytm Money, BSE and statutory cost rules with effective dates. |
| S3 SENSEX Batman implementation | NOT STARTED | Port only instrument/data/calendar/contract mechanics. |
| S4 SENSEX Adaptive implementation | NOT STARTED | Port frozen candidate router without SENSEX-driven re-selection. |
| S5 Historical walk-forward transfer test | NOT STARTED | Untouched final SENSEX holdout required. |
| S6 Robustness/statistical inference | NOT STARTED | Dependence-aware bootstrap + cost/quote/seed sensitivity. |
| S7 Prospective paper trading | NOT STARTED | Allowed only after S1-S6 integrity gates. |
| S8 Separate SENSEX report | NOT STARTED | Standalone manuscript/report; NIFTY manuscript remains untouched. |

## Branch
research/sensex-batman-adaptive-v1

Parent research branch: research/adaptive-paper-signals-v1

## Current scientific position
No SENSEX performance conclusion has been made. This branch currently contains the transfer-study specification and audit scaffolding only.