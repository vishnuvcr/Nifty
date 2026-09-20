# Nifty 50 Monte Carlo & Walk-Forward Research

Research framework for Nifty 50 expiry-range forecasting, bull/bear/neutral classification, and Long Iron Condor evaluation.

## Branch
Primary research branch: `research/monte-carlo-wfa-v1`

## Current modules
- `src/nifty_mc/gbm.py`: physical-measure GBM terminal simulations
- `src/nifty_mc/volatility.py`: realized/EWMA volatility estimators
- `src/nifty_mc/trend.py`: bull/bear/neutral classifier
- `src/nifty_mc/iron_condor.py`: expiration payoff and Monte Carlo metrics
- `src/nifty_mc/walk_forward.py`: chronological out-of-sample forecast engine
- `src/nifty_mc/run_experiment.py`: CSV-driven research runner
- `docs/RESEARCH_SPEC.md`: research protocol
- `configs/default.yaml`: baseline experiment parameters

## Data contract
Price CSV must contain a date/datetime field and a close/price field.

Origin CSV:
`decision_date,expiry_date`

Historical option-chain data will be added as a separate layer. It must contain timestamp/expiry/strike/type plus executable bid/ask or a documented reconstruction method.

## Important
This repository currently contains the research scaffold; no live-trading claim is made. The next stage is historical data ingestion and a full option-chain walk-forward experiment.


## Unified paper-trading Pages
The published dashboard is organized as Index -> Strategy: NIFTY -> Batman/Adaptive and SENSEX -> Batman/Adaptive. SENSEX prospective paper trading is sourced from research/sensex-s7-paper-trading-v1 and synchronized by the main Pages publisher.


## Combined NIFTY + SENSEX Batman capital study
A provisional simultaneous-trading capital analysis is documented at [docs/combined_batman_capital/CAPITAL_REQUIREMENT.md](docs/combined_batman_capital/CAPITAL_REQUIREMENT.md). For one NIFTY Batman lot plus one SENSEX Batman lot, the current repository-backed research reserve is **₹1.51 lakh**, rounded to **₹1.55 lakh** as a working minimum before a separate operating cash cushion. This remains provisional because the retained NIFTY risk population is incomplete and the exact Paytm Money basket margin must be captured before deployment.

Related phase records: [research plan](docs/combined_batman_capital/RESEARCH_PLAN.md) · [phase status](docs/combined_batman_capital/PHASE_STATUS.md) · [error log](docs/combined_batman_capital/ERROR_LOG.md) · [conversation log](docs/combined_batman_capital/CONVERSATION_LOG.md)
