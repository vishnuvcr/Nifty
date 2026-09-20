# Nifty 50 Monte Carlo & Walk-Forward Research

Research framework for Nifty 50 expiry-range forecasting, bull/bear/neutral classification, and strategy evaluation.

## Research principles
- Strict walk-forward / out-of-sample validation
- No look-ahead leakage
- Separate physical-measure forecasting from option-implied risk-neutral quantities
- Transaction costs, slippage and bid/ask assumptions
- GBM as a baseline, with bootstrap/GARCH/regime-aware extensions
- Reproducible experiments and fixed random seeds

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
- S6 bootstrap table: https://github.com/vishnuvcr/Nifty/blob/research/sensex-s6-robustness-v1/reports/sensex_s6/S6_BLOCK_BOOTSTRAP.csv

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
