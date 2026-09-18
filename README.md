# Nifty 50 Monte Carlo & Walk-Forward Research

Research framework for Nifty 50 expiry-range forecasting, bull/bear/neutral classification, and Long Iron Condor evaluation.

## Research principles
- Strict walk-forward / out-of-sample validation
- No look-ahead leakage
- Separate physical-measure forecasting from option-implied risk-neutral quantities
- Transaction costs, slippage and bid/ask assumptions
- GBM as a baseline, with bootstrap/GARCH/regime-aware extensions
- Reproducible experiments and fixed random seeds

Initial structure:
- `src/` model and simulation code
- `configs/` experiment settings
- `tests/` unit/integration tests
- `notebooks/` research notebooks
- `reports/` generated research outputs
- `data/` local-only datasets (not committed)

See `docs/RESEARCH_SPEC.md` for the experiment protocol.
