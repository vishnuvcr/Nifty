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

Current SENSEX status: S0 transfer freeze complete; S1 data/contract audit in progress; no SENSEX performance conclusion yet.

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
