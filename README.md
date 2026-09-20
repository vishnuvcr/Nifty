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


## Limited-risk option WFO extension

This branch is the protocol-only starting point for testing option strategies with a finite maximum loss, including both capped-profit and potentially unlimited-profit structures.

- Research plan: docs/limited_risk_option_wfo/RESEARCH_PLAN.md
- Phase status: docs/limited_risk_option_wfo/PHASE_STATUS.md
- Error log: docs/limited_risk_option_wfo/ERROR_LOG.md
- Conversation/audit log: docs/limited_risk_option_wfo/CONVERSATION_LOG.md
- Risk rules: docs/limited_risk_option_wfo/STRATEGY_UNIVERSE_AND_RISK_RULES.md
- Cost/execution policy: docs/limited_risk_option_wfo/COST_AND_EXECUTION_POLICY.md
- Configuration: configs/limited_risk_option_wfo_v1.yaml
- Manual/automatic protocol CI: .github/workflows/limited-risk-option-wfo-v1.yml

Current status: L0 complete. No new performance result is claimed.


## Results — L0-L7 complete

Verified CI run: **35496685719** using parent run **35425922439**.

- [Phase manuscript](reports/limited_risk_wfo/MANUSCRIPT.md)
- [Final phase report](reports/limited_risk_wfo/FINAL_PHASE_REPORT.md)
- [Risk classification](reports/limited_risk_wfo/RISK_CLASSIFICATION.csv)
- [Key validation results](reports/limited_risk_wfo/VALIDATION_KEY_RESULTS.csv)
- [Nested selection](reports/limited_risk_wfo/NESTED_SELECTION.csv)
- [CPCV / multiple-testing](reports/limited_risk_wfo/CPCV_MULTIPLE_TESTING.csv)
- [Cost stress](reports/limited_risk_wfo/CANDIDATE_COST_STRESS.csv)
- [Regime router summary](reports/limited_risk_wfo/REGIME_ROUTER_SUMMARY.csv)

**Decision:** no strategy promoted. The 2025-2026 sample is already exposed; L8 remains HOLD pending genuinely new post-exposure data and deployment-grade bid/ask history.
