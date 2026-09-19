# SENSEX Options Research Phase Status

Last updated: 2026-09-20 (Asia/Kolkata) — S6 robustness execution gate

| Phase | Status | Evidence / next gate |
|---|---|---|
| S0 Transfer specification freeze | COMPLETE | Frozen parent specification and provenance recorded. |
| S1 Data-source and contract audit | COMPLETE | Source register and data-contract audit documented; dataset limitations explicitly recorded. |
| S2 Execution-cost model | COMPLETE | SENSEX-specific transaction-cost and slippage model implemented and deducted from net P&L. |
| S3 SENSEX Batman implementation | COMPLETE | Frozen Batman engine implemented and deterministic candidate/expiry evaluation is reproducible. |
| S4 SENSEX Adaptive implementation | COMPLETE | Frozen regime-conditioned candidate router implemented without SENSEX outcome retuning. |
| S5 Historical walk-forward transfer test | COMPLETE | Development 2024, validation 2025, and available 2026 holdout through 2026-05-21 were completed in one-lot transfer-edge mode; account-affordability results are separately reported. |
| S6 Robustness/statistical inference | RUNNING | Slippage grid, Monte Carlo seed sensitivity, and dependence-aware block bootstrap are being executed on the frozen rules. |
| S7 Prospective paper trading | NOT STARTED | Allowed only after S6 integrity and interpretation gates pass. |
| S8 Separate SENSEX report | NOT STARTED | Will summarize the completed transfer study without modifying the NIFTY manuscript. |

## Scientific boundary

The SENSEX study remains strictly separate from the NIFTY MC-WFO manuscript. One-lot results are transfer-edge evidence, not an assertion of deployable capital efficiency at any particular account size. The 2026 holdout is limited by the available SENSEX option dataset to 2026-01-01 through 2026-05-21.

## Current S6 controls

- Slippage sensitivity: 0.25, 0.50, 1.00, and 2.00 option points per executed option leg.
- Monte Carlo seed sensitivity: 101, 202, 303, 404, 505 on validation and holdout at 0.50-point slippage.
- Dependence-aware inference: circular moving-block bootstrap, block length 3 trades, 10,000 replications on validation + holdout closed trades at base slippage.
- No quote-source substitution: the underlying archive provides OHLCV/OI, not historical point-in-time bid/ask snapshots.
- No re-optimization after seeing SENSEX holdout outcomes.

## Branch

research/sensex-s6-robustness-v1
