# Nifty 50 Monte Carlo & Walk-Forward Research

Research framework for Nifty 50 expiry-range forecasting, bull/bear/neutral classification, and strategy evaluation.

## Research principles
- Strict walk-forward / out-of-sample validation
- No look-ahead leakage
- Separate physical-measure forecasting from option-implied risk-neutral quantities
- Transaction costs, slippage and bid/ask assumptions
- GBM as a baseline, with bootstrap/GARCH/regime-aware extensions
- Reproducible experiments and fixed random seeds

## Expiry-day early-exit sensitivity analysis

A separate sensitivity branch tests the frozen Batman and Adaptive entry rules for NIFTY and SENSEX under three expiry-day exit scenarios: expiry settlement baseline, 15:00 IST, and 15:10 IST. The early-exit scenarios use the exact 1-minute bar OPEN at the chosen timestamp to avoid same-minute look-ahead.

- Branch: https://github.com/vishnuvcr/Nifty/tree/research/expiry-auction-exit-analysis-v1
- Research plan: https://github.com/vishnuvcr/Nifty/blob/research/expiry-auction-exit-analysis-v1/docs/expiry_exit_analysis/RESEARCH_PLAN.md
- Phase status: https://github.com/vishnuvcr/Nifty/blob/research/expiry-auction-exit-analysis-v1/docs/expiry_exit_analysis/PHASE_STATUS.md
- Error log: https://github.com/vishnuvcr/Nifty/blob/research/expiry-auction-exit-analysis-v1/docs/expiry_exit_analysis/ERROR_LOG.md
- Conversation/audit log: https://github.com/vishnuvcr/Nifty/blob/research/expiry-auction-exit-analysis-v1/docs/expiry_exit_analysis/CONVERSATION_LOG.md

**Current status (2026-09-20):** E0 specification, E1 engine, and E2 data workflow are complete. E3 CI execution is in progress; E4 result verification and E5 final comparison are pending. No 15:00/15:10 numerical result is claimed until the CI outputs pass verification.

## Expiry-day early-exit analysis — VERIFIED RESULTS

### Initial capital sizing — research estimate

A capital-sizing analysis has been added to the expiry-exit branch. For SENSEX, the historical MC-risk proxy is ₹66,971/lot maximum for Batman and ₹89,577/lot maximum for Adaptive. With a 20% operational reserve, the single-account SENSEX research reserve is approximately **₹107,500 per active lot-equivalent**. This is explicitly a risk proxy, not a Paytm Money live-margin quote; the exact four-leg basket must be checked in Paytm Money's current margin calculator before deployment.

See `docs/expiry_exit_analysis/CAPITAL_REQUIREMENT.md`.



The dedicated branch `research/expiry-auction-exit-analysis-v1` has completed the frozen Batman/Adaptive exit sensitivity study for NIFTY and SENSEX.

Verified GitHub Actions run: 35492648657 (success).

Published outputs:
- RESULTS.md
- COMBINED_OOS_SUMMARY.csv
- EXIT_SUMMARY_BY_SPLIT.csv
- TRADE_LEVEL_RESULTS.csv

The study compares expiry settlement with exact 15:00 IST and 15:10 IST one-minute bar OPEN exits, keeping entry rules frozen. The SENSEX early-exit rerun uses the cached frozen S5 trade population rather than recomputing entry selection.

## Unified paper-trading GitHub Pages

GitHub Pages now uses a two-level selector:

**Index**
- NIFTY 50
  - BATMAN
  - ADAPTIVE STRATEGY
- BSE SENSEX
  - BATMAN
  - ADAPTIVE STRATEGY

Live Pages: https://vishnuvcr.github.io/Nifty/

Paper-trading publication and scheduling:
- Combined Pages publisher: https://github.com/vishnuvcr/Nifty/blob/main/.github/workflows/publish-paper-pages.yml
- NIFTY paper branch: https://github.com/vishnuvcr/Nifty/tree/research/adaptive-paper-signals-v1
- SENSEX prospective paper branch: https://github.com/vishnuvcr/Nifty/tree/research/sensex-s7-paper-trading-v1
- SENSEX entry scanner: https://github.com/vishnuvcr/Nifty/blob/main/.github/workflows/sensex-paper-signal-producer-v1.yml
- SENSEX settlement/page refresh: https://github.com/vishnuvcr/Nifty/blob/main/.github/workflows/sensex-paper-pages-refresh-v1.yml

Schedule:
- NIFTY entry scanning remains at 09:30 IST on trading weekdays; the existing 16:00 IST publisher is refresh-only.
- SENSEX Batman + Adaptive entry scanners run automatically at 09:30 IST (04:00 UTC) on weekdays and have manual workflow-dispatch buttons.
- SENSEX settlement/page refresh runs automatically at 16:00 IST (10:30 UTC) on weekdays and has a manual workflow-dispatch button.
- After SENSEX scanner/refresh state is pushed, the combined Pages publisher is also triggered immediately; the 16:00 job remains the scheduled settlement/publication backstop.
- The 16:00 jobs do not create a second entry signal.

The SENSEX scanner is paper-only. Live entry requires executable bid/ask data and applies a 0.50-point adverse slippage stress per option leg; missing or malformed quote data becomes NO_TRADE and is logged. No broker order is submitted.

## Parallel SENSEX transfer study

A separate research branch tests the frozen Phase-10 Batman and Adaptive strategies on BSE SENSEX options without contaminating the NIFTY manuscript.

- Historical transfer branch: research/sensex-batman-adaptive-v1
- SENSEX S7 prospective paper branch: research/sensex-s7-paper-trading-v1
- SENSEX research plan: https://github.com/vishnuvcr/Nifty/blob/research/sensex-batman-adaptive-v1/docs/sensex_options/RESEARCH_PLAN.md
- SENSEX S7 phase status: https://github.com/vishnuvcr/Nifty/blob/research/sensex-s7-paper-trading-v1/docs/sensex_options/PHASE_STATUS.md
- SENSEX S7 specification: https://github.com/vishnuvcr/Nifty/blob/research/sensex-s7-paper-trading-v1/docs/sensex_options/S7_PAPER_TRADING.md
- SENSEX error log: https://github.com/vishnuvcr/Nifty/blob/research/sensex-s7-paper-trading-v1/docs/sensex_options/ERROR_LOG.md
- SENSEX conversation/audit log: https://github.com/vishnuvcr/Nifty/blob/research/sensex-s7-paper-trading-v1/docs/sensex_options/CONVERSATION_LOG.md

Current SENSEX status: S0–S6 historical transfer testing and robustness are complete; S7 paper-trading infrastructure is complete, with prospective observations pending. No S7 performance inference has been claimed.

### SENSEX S6 robustness result

The SENSEX transfer study completed S6 robustness/statistical inference on branch research/sensex-s6-robustness-v1. The protocol uses the validated S5 composite MC history, slippage sensitivity at 0.25/0.50/1.00/2.00 points per leg, five fixed Monte Carlo seeds (101/202/303/404/505) on validation and holdout, and a 10,000-repetition circular moving-block bootstrap with block length 3 trades.

- S6 phase status: https://github.com/vishnuvcr/Nifty/blob/research/sensex-s6-robustness-v1/docs/sensex_options/PHASE_STATUS.md
- S6 robustness report: https://github.com/vishnuvcr/Nifty/blob/research/sensex-s6-robustness-v1/reports/sensex_s6/S6_ROBUSTNESS_RESULTS.md
- S6 robustness summary: https://github.com/vishnuvcr/Nifty/blob/research/sensex-s6-robustness-v1/reports/sensex_s6/S6_ROBUSTNESS_SUMMARY.json
- S6 slippage table: https://github.com/vishnuvcr/Nifty/blob/research/sensex-s6-robustness-v1/reports/sensex_s6/S6_SLIPPAGE_SUMMARY.csv
- S6 seed table: https://github.com/vishnuvcr/Nifty/blob/research/sensex-s6-robustness-v1/reports/sensex_s6/S6_SEED_SUMMARY.csv

Final base-slippage combined OOS inference: Adaptive n=64, mean ₹2,612.93, bootstrap 95% CI -₹804.31 to ₹6,133.11; Batman n=44, mean ₹5,742.06, bootstrap 95% CI ₹662.67 to ₹10,341.49. These remain one-lot transfer-edge results; the SENSEX holdout is limited by the available options archive through 2026-05-21.

The SENSEX study is intentionally separate from the NIFTY MC-WFO manuscript.

## Initial structure
- src/ model and simulation code
- configs/ experiment settings
- tests/ unit/integration tests
- notebooks/ research notebooks
- reports/ generated research outputs
- data/ local-only datasets (not committed)

See the active research branch for the relevant experiment protocol.


## Planned next research phase — limited-risk option WFO

A separate research branch has been created to test option strategies with a finite maximum loss, including limited-loss structures with either limited or potentially unlimited profit. Batman remains outside this risk-bounded universe.

- Branch: https://github.com/vishnuvcr/Nifty/tree/research/limited-risk-option-wfo-v1
- Research plan: https://github.com/vishnuvcr/Nifty/blob/research/limited-risk-option-wfo-v1/docs/limited_risk_option_wfo/RESEARCH_PLAN.md
- Phase status: https://github.com/vishnuvcr/Nifty/blob/research/limited-risk-option-wfo-v1/docs/limited_risk_option_wfo/PHASE_STATUS.md
- Error log: https://github.com/vishnuvcr/Nifty/blob/research/limited-risk-option-wfo-v1/docs/limited_risk_option_wfo/ERROR_LOG.md
- Strategy/risk rules: https://github.com/vishnuvcr/Nifty/blob/research/limited-risk-option-wfo-v1/docs/limited_risk_option_wfo/STRATEGY_UNIVERSE_AND_RISK_RULES.md

**Current status (2026-09-20):** L0 protocol freeze is complete. No new performance result is claimed. The next phase is literature/data review followed by mechanical payoff-risk auditing before any strategy ranking.


## Limited-risk option WFO — current result

The separate branch `research/limited-risk-option-wfo-v1` has completed its historical L0-L7 analysis. It mechanically identified 27/36 finite-loss core strategies, with Jade Lizard and Put Ratio Spread among the strongest development-to-validation candidates. However, the cross-strategy multiple-testing diagnostic was not supportive (Reality-Check-style block-bootstrap p=0.7426), and the available 2025-2026 period is already exposed by the parent research.

- Branch: https://github.com/vishnuvcr/Nifty/tree/research/limited-risk-option-wfo-v1
- Final phase report: https://github.com/vishnuvcr/Nifty/blob/research/limited-risk-option-wfo-v1/reports/limited_risk_wfo/FINAL_PHASE_REPORT.md
- Phase status: https://github.com/vishnuvcr/Nifty/blob/research/limited-risk-option-wfo-v1/docs/limited_risk_option_wfo/PHASE_STATUS.md

**Current decision (2026-09-20):** no strategy promoted. Fresh-holdout confirmation is HOLD until genuinely new post-exposure data and deployment-grade execution data are available.


## Next research phases — frozen defined-risk prospective validation and long-premium study

### A. Two frozen finite-loss candidates — NIFTY + SENSEX

Two candidates are retained for frozen prospective validation, without retrospective strategy selection:

- Jade Lizard
- Put Ratio Spread

Sell Put and Bull Put Spread are retained only as historical limited-risk research candidates and are excluded from the new prospective validation stream.

NIFTY:
- Branch: https://github.com/vishnuvcr/Nifty/tree/research/prospective-defined-risk-nifty-v1
- Plan: https://github.com/vishnuvcr/Nifty/blob/research/prospective-defined-risk-nifty-v1/docs/prospective_defined_risk_nifty_v1/RESEARCH_PLAN.md
- Phase status: https://github.com/vishnuvcr/Nifty/blob/research/prospective-defined-risk-nifty-v1/docs/prospective_defined_risk_nifty_v1/PHASE_STATUS.md

SENSEX:
- Branch: https://github.com/vishnuvcr/Nifty/tree/research/prospective-defined-risk-sensex-v1
- Plan: https://github.com/vishnuvcr/Nifty/blob/research/prospective-defined-risk-sensex-v1/docs/prospective_defined_risk_sensex_v1/RESEARCH_PLAN.md
- Phase status: https://github.com/vishnuvcr/Nifty/blob/research/prospective-defined-risk-sensex-v1/docs/prospective_defined_risk_sensex_v1/PHASE_STATUS.md

Each retained strategy has a separate dashboard/ledger under the Pages tree. Entry scans are scheduled at 09:30 IST and settlement/page refresh at 16:00 IST. The prospective pages use the same mobile-friendly paper-trading dashboard style as the existing SENSEX Batman dashboard. No broker orders are submitted. Sell Put and Bull Put Spread are excluded from the prospective stream.

### B. NIFTY long-premium MC/WFO

New research question: can MC/WFO identify sufficiently cheap Buy Call / Buy Put opportunities with positive expected value after premium, brokerage, slippage and expiry time decay?

- Branch: https://github.com/vishnuvcr/Nifty/tree/research/long-premium-mcwfo-v1
- Research plan: https://github.com/vishnuvcr/Nifty/blob/research/long-premium-mcwfo-v1/docs/long_premium_mcwfo_v1/RESEARCH_PLAN.md
- Final report: https://github.com/vishnuvcr/Nifty/blob/research/long-premium-mcwfo-v1/reports/long_premium_mcwfo_v1/FINAL_PHASE_REPORT.md

Historical result: the development-frozen Buy Call <=0.55% of spot rule failed 2023-2024 validation (mean -1.68 points, PF 0.968; block-bootstrap 95% CI -24.92 to +29.70). The 22-rule multiple-testing diagnostic was p=0.886. The 2025-2026 period is already exposed by the parent study and is descriptive only. No long-premium rule is promoted.

The current live Pages selector is https://vishnuvcr.github.io/Nifty/; the root selector and prospective dashboard sources have been updated for Jade Lizard and Put Ratio Spread, and the Pages publisher is redeploying the corrected tree.


## BATMAN Tuning V1

A separate research branch has been created to test whether the promoted BATMAN strategy can be improved without changing the promoted control.

- Branch: https://github.com/vishnuvcr/Nifty/tree/research/batman-tuning-v1
- Research plan: https://github.com/vishnuvcr/Nifty/blob/research/batman-tuning-v1/docs/batman_tuning/RESEARCH_PLAN.md
- Protocol freeze: https://github.com/vishnuvcr/Nifty/blob/research/batman-tuning-v1/docs/batman_tuning/PROTOCOL_FREEZE.md
- Parameter grid: https://github.com/vishnuvcr/Nifty/blob/research/batman-tuning-v1/docs/batman_tuning/PARAMETER_GRID.md
- Phase status: https://github.com/vishnuvcr/Nifty/blob/research/batman-tuning-v1/docs/batman_tuning/PHASE_STATUS.md
- Error log: https://github.com/vishnuvcr/Nifty/blob/research/batman-tuning-v1/docs/batman_tuning/ERROR_LOG.md

T0 protocol freeze is complete. The study will test D0-D6 entry offsets, prior-session signal to market-open execution, same-session 09:30 execution, fixed targets, fixed stops, trailing targets and trailing stops. No tuned result is claimed yet. The promoted BATMAN prospective-validation stream remains untouched.


### BATMAN Tuning V1 — T1 data audit status

T1 has been audited against historical BATMAN backfill commits and GitHub Actions runs. The parent backfill record is a reconstructed close-price paper entry and explicitly lacks historical bid/ask quotes; no reusable workflow artifact containing the required intraday option history was retained. Therefore D0-D6 and target/stop/trailing tuning remain blocked rather than being estimated from insufficient data.

- T1 cache contract: https://github.com/vishnuvcr/Nifty/blob/research/batman-tuning-v1/data/batman_tuning_cache/README.md
- T1 validator: https://github.com/vishnuvcr/Nifty/blob/research/batman-tuning-v1/scripts/batman_tuning_t1_data_check.py
- T1 audit: https://github.com/vishnuvcr/Nifty/blob/research/batman-tuning-v1/docs/batman_tuning/T1_DATA_AUDIT.md
- Phase status: https://github.com/vishnuvcr/Nifty/blob/research/batman-tuning-v1/docs/batman_tuning/PHASE_STATUS.md

No tuning P&L or parameter winner is claimed until the immutable historical cache passes validation.


### BATMAN Tuning V1 — T1 source acquisition

T1 now has a reproducible historical-source acquisition layer covering the original 2020-01-01 to 2026-03-30 study horizon. The workflow uses a persistent GitHub Actions cache for large raw archives and writes SHA-256 provenance manifests. Public historical option archives are treated as bar-level data, not historical bid/ask feeds.

- Source decision: https://github.com/vishnuvcr/Nifty/blob/research/batman-tuning-v1/docs/batman_tuning/DATA_SOURCE_DECISION.md
- Acquisition workflow: https://github.com/vishnuvcr/Nifty/blob/research/batman-tuning-v1/.github/workflows/batman-tuning-t1-acquire.yml
- Source manifest schema: https://github.com/vishnuvcr/Nifty/blob/research/batman-tuning-v1/data/batman_tuning_cache/source_manifest.schema.json
- T1 audit: https://github.com/vishnuvcr/Nifty/blob/research/batman-tuning-v1/docs/batman_tuning/T1_DATA_AUDIT.md

T1 remains gated until the raw archives are normalized and the compact BATMAN-specific derived cache passes coverage, contract, timestamp, zero-volume, and expiry-resolution checks. No tuning result is claimed before that gate.


## BATMAN Tuning V1 — Final Status

Research branches:
- T0/T1/T2: `research/batman-tuning-v1`
- T2 corrected entry branch: `research/batman-tuning-t2-entry-v2`
- T3 corrected exit branch: `research/batman-tuning-t3-exit-v1`
- T4 nested WFO + holdout: `research/batman-tuning-t4-wfo-v1`
- T5 robustness: `research/batman-tuning-t5-robustness-v1`
- T6 prospective freeze: `research/batman-tuning-t6-prospective-v1`

Final disposition: the D3/09:30 BATMAN + trailing-target (20% activation / 10% retracement) candidate produced positive net P&L on 7 untouched holdout trades, but it is **not promoted** because the holdout is too small and expiry control outperformed it on 6 comparable trades. See `docs/batman_tuning_t5/T5_FINAL_CONCLUSION.md` and `docs/batman_tuning_t6/PROSPECTIVE_FREEZE.md`.


## BATMAN Tuning T7 — Joint entry × timing × exit

The T7 development selector is frozen before the untouched holdout.

- Branch: https://github.com/vishnuvcr/Nifty/tree/research/batman-tuning-t7-joint-wfo-v1
- Research plan: https://github.com/vishnuvcr/Nifty/blob/research/batman-tuning-t7-joint-wfo-v1/docs/batman_tuning_t7/RESEARCH_PLAN.md
- Protocol freeze: https://github.com/vishnuvcr/Nifty/blob/research/batman-tuning-t7-joint-wfo-v1/docs/batman_tuning_t7/PROTOCOL_FREEZE.md
- Phase status: https://github.com/vishnuvcr/Nifty/blob/research/batman-tuning-t7-joint-wfo-v1/docs/batman_tuning_t7/PHASE_STATUS.md
- Error log: https://github.com/vishnuvcr/Nifty/blob/research/batman-tuning-t7-joint-wfo-v1/docs/batman_tuning_t7/ERROR_LOG.md
- Holdout workflow: https://github.com/vishnuvcr/Nifty/blob/research/batman-tuning-t7-joint-wfo-v1/.github/workflows/batman-tuning-t7-holdout.yml

**Frozen development configuration:** D4 / same-session 09:30 / trailing target with 30% activation and 30% retracement. The 2025–2026 holdout remains untouched and is evaluated separately against the original D3/09:30/expiry control and the prior D3/09:30 20%/10% trailing-target candidate.

No holdout result is claimed until the holdout workflow outputs pass verification.
