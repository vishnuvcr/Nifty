# SENSEX Options Research Phase Status

Last updated: 2026-09-21 (Asia/Kolkata) — S7 decision-time observation published

| Phase | Status | Evidence / next gate |
|---|---|---|
| S0 Transfer specification freeze | COMPLETE | Frozen parent specification and provenance recorded. |
| S1 Data-source and contract audit | COMPLETE | Source register and data-contract audit documented; dataset limitations explicitly recorded. |
| S2 Execution-cost model | COMPLETE | SENSEX-specific transaction-cost and slippage model implemented and deducted from net P&L. |
| S3 SENSEX Batman implementation | COMPLETE | Frozen Batman engine implemented and deterministic candidate/expiry evaluation is reproducible. |
| S4 SENSEX Adaptive implementation | COMPLETE | Frozen regime-conditioned candidate router implemented without SENSEX outcome retuning. |
| S5 Historical walk-forward transfer test | COMPLETE | Development 2024, validation 2025, and available 2026 holdout through 2026-05-21 completed in one-lot transfer-edge mode. |
| S6 Robustness/statistical inference | COMPLETE | Slippage grid, five fixed MC seeds, S5 reproducibility gate, and 10,000-repetition circular moving-block bootstrap completed on frozen rules. |
| S7 Prospective paper trading | ACTIVE — DATA-LIMITED OBSERVATION RECORDED / EXECUTABLE OBSERVATION PENDING | The 21-Sep-2026 09:30 decision-time observation was published from available underlying/past-only data as DATA_LIMITED_CANDIDATE for Batman and Adaptive. No executable option premium/bid-ask was available, so no paper trade was opened and no realized performance was recorded. |
| S8 Separate SENSEX report | NOT STARTED | Will summarize the completed transfer study and any completed prospective evidence without modifying the NIFTY manuscript. |

## Scientific boundary

The SENSEX study remains strictly separate from the NIFTY MC-WFO manuscript. S7 creates a new prospective observation stream and does not reopen, backfill, or retune the historical S5/S6 holdout. One-lot results remain transfer-edge evidence, not an assertion of deployable capital efficiency at any particular account size.

## S7 controls

- Entry scanner: weekdays at 09:30 IST / 04:00 UTC.
- Page/settlement refresh: weekdays at 16:00 IST / 10:30 UTC.
- Manual workflow_dispatch is enabled for both workflows.
- Batman and Adaptive use the frozen S0–S6 strategy definitions.
- The frozen model targets 5,000 Monte Carlo paths and a 756-session lookback; today's data-limited observation explicitly records the short-history limitation.
- Regime is computed past-only from RV20 ranked over the prior 252 observations.
- Live executable entries require bid/ask. When bid/ask is unavailable but underlying/model data exist, publish DATA_LIMITED_CANDIDATE with zero executable lots and no P&L claim. No LTP fallback is allowed.
- 0.50 option-point adverse slippage per executed leg is applied to the prospective paper entry proxy.
- SENSEX transaction-cost rules remain the frozen S2 model.
- Paper trading is one-lot transfer-edge mode; no broker order is submitted.
- True scanner/runtime failures are written to the SENSEX error log and are not silently converted to zero-return trades.
- After successful SENSEX state publication, the scanner/refresh workflows trigger the combined main Pages publisher; the existing 16:00 publisher remains the scheduled backstop.

## Workflows

- .github/workflows/sensex-paper-signal-producer-v1.yml on main — weekdays 09:30 IST decision-time scanner; Batman + Adaptive; manual dispatch available; no backfill mode.
- .github/workflows/sensex-paper-pages-refresh-v1.yml — 16:00 IST settlement/page refresh; manual dispatch available.
- .github/workflows/publish-paper-pages.yml on main — publishes the combined NIFTY + SENSEX GitHub Pages dashboard at 16:00 IST.

## Branch

research/sensex-s7-paper-trading-v1

### S5/S6 historical conclusion

The SENSEX transfer test is complete for the available public dataset. The ₹1 lakh/2% account gate produced no executable trades; the one-lot edge test produced positive validation/holdout results for the frozen Adaptive router and positive holdout results for the frozen Batman MC-gated subset. Evidence remains limited by data coverage and quote-quality constraints. S7 is now a separate prospective observation phase; its outcomes must not be mixed into the historical inference until the prospective data stream is complete.
