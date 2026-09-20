# Nifty 50 Monte Carlo & Walk-Forward Research

Research framework for Nifty 50 expiry-range forecasting, bull/bear/neutral classification, and Long Iron Condor evaluation.

## Research branches

Primary NIFTY research remains separate from the SENSEX transfer study.

- NIFTY Phase-10 Adaptive research: `research/adaptive-paper-signals-v1`
- SENSEX Batman + Adaptive transfer study: `research/sensex-batman-adaptive-v1`

## SENSEX transfer study

The SENSEX study tests the frozen Phase-10 Batman and Adaptive strategy specifications on BSE SENSEX options without retuning them on SENSEX outcomes.

Study files:
- [SENSEX research plan](docs/sensex_options/RESEARCH_PLAN.md)
- [Phase status](docs/sensex_options/PHASE_STATUS.md)
- [Error log](docs/sensex_options/ERROR_LOG.md)
- [Conversation/audit log](docs/sensex_options/CONVERSATION_LOG.md)
- [Data manifest](docs/sensex_options/DATA_MANIFEST.md)
- [Batman config](configs/sensex_batman_v1.json)
- [Adaptive config](configs/sensex_adaptive_v1.json)

Current status: **S0 transfer-specification freeze in progress; no SENSEX performance conclusion yet.**

The SENSEX study is intentionally excluded from the NIFTY MC-WFO manuscript until and unless a separate cross-index analysis is formally created.

## NIFTY research principles

- Strict walk-forward / out-of-sample validation
- No look-ahead leakage
- Separate physical-measure forecasting from option-implied risk-neutral quantities
- Transaction costs, slippage and bid/ask assumptions
- GBM as a baseline, with bootstrap/GARCH/regime-aware extensions
- Reproducible experiments and fixed random seeds

No live-trading claim is made by this repository research framework.


## Frozen defined-risk prospective validation

This branch currently observes two transferred candidates prospectively: **Jade Lizard** and **Put Ratio Spread**. Sell Put and Bull Put Spread were removed before the first eligible observation. See `docs/prospective_defined_risk_sensex_v1/RESEARCH_PLAN.md` and `docs/prospective_defined_risk_sensex_v1/PHASE_STATUS.md`.
