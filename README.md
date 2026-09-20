# Nifty 50 Monte Carlo & Walk-Forward Research

Research framework for Nifty 50 expiry-range forecasting, bull/bear/neutral classification, and strategy evaluation.

## Research principles
- Strict walk-forward / out-of-sample validation
- No look-ahead leakage
- Separate physical-measure forecasting from option-implied risk-neutral quantities
- Transaction costs, slippage and bid/ask assumptions
- GBM as a baseline, with bootstrap/GARCH/regime-aware extensions
- Reproducible experiments and fixed random seeds

## Parallel SENSEX transfer study

A separate research branch has been created to test the frozen Phase-10 Batman and Adaptive strategies on BSE SENSEX options without contaminating the NIFTY manuscript.

- Branch: research/sensex-batman-adaptive-v1
- Active phase branch: research/sensex-s1-data-audit-v1
- SENSEX research plan: https://github.com/vishnuvcr/Nifty/blob/research/sensex-batman-adaptive-v1/docs/sensex_options/RESEARCH_PLAN.md
- SENSEX phase status: https://github.com/vishnuvcr/Nifty/blob/research/sensex-s1-data-audit-v1/docs/sensex_options/PHASE_STATUS.md
- SENSEX source register: https://github.com/vishnuvcr/Nifty/blob/research/sensex-s1-data-audit-v1/docs/sensex_options/SOURCE_REGISTER.md
- SENSEX error log: https://github.com/vishnuvcr/Nifty/blob/research/sensex-s1-data-audit-v1/docs/sensex_options/ERROR_LOG.md

Current SENSEX status: S0–S6 complete through robustness/statistical inference on the validated transfer study; S7 prospective paper trading is not started.

### SENSEX S6 robustness result
The SENSEX transfer study has completed S6 robustness/statistical inference on branch `research/sensex-s6-robustness-v1`. The completed protocol uses the validated S5 composite MC history, slippage sensitivity at 0.25/0.50/1.00/2.00 points per leg, five fixed Monte Carlo seeds (101/202/303/404/505) on validation and holdout, and a 10,000-repetition circular moving-block bootstrap with block length 3 trades.

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

### SENSEX execution note
The frozen S5 backtest workflow is `.github/workflows/sensex-s5-wfa-backtest-dispatcher.yml` on `main`; it checks out `research/sensex-s5-wfa-backtest-v1`, downloads the validated public SENSEX 1-minute dataset, and runs development/validation/holdout with the frozen Batman and Adaptive rules. No numerical result is considered valid until a successful run commits `reports/sensex_options/`.


SENSEX results: https://github.com/vishnuvcr/Nifty/blob/research/sensex-s5-wfa-backtest-v1/reports/sensex_options/RESULT_SUMMARY.md


### SENSEX backtest result
See `docs/sensex_options/SENSEX_BACKTEST_RESULT.md` for the frozen-method result, validation/holdout statistics, slippage sensitivity, account-affordability analysis, limitations, and next research phase.
