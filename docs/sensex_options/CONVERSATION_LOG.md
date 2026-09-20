# SENSEX Options Research Conversation Log

## 2026-09-20

### User instruction
Start a separate branch to test the final derived Batman strategy and the Adaptive strategy in SENSEX options trading.

### Recorded research decision
- Dedicated branch: research/sensex-batman-adaptive-v1.
- Keep this study separate from the NIFTY MC-WFO manuscript.
- Treat the NIFTY Phase-10 Batman and Adaptive specifications as frozen parent protocols.
- Validate SENSEX-specific data, contract rules, expiry calendar, quote quality and transaction costs before running performance tests.
- Do not tune the SENSEX study using its final holdout.

### Audit note
This repository log records user-visible instructions and research decisions. It does not store private chain-of-thought or hidden reasoning.\n\n### S6 execution update — 2026-09-20
User instruction: proceed without stopping until usable results are obtained.

Research action:
- Corrected the S6 workflow before execution because the initial version was insufficient for the planned robustness phase.
- Added persistent Actions caching for the frozen SENSEX option dataset.
- Added fixed slippage grid: 0.25, 0.50, 1.00, 2.00 option points per executed leg.
- Added five fixed Monte Carlo seed scenarios (101, 202, 303, 404, 505) on validation and holdout at 0.50-point slippage.
- Added dependence-aware circular moving-block bootstrap (block length 3 trades, 10,000 replications) over validation + holdout base-slippage closed trades.
- Kept one-lot transfer-edge mode separate from the original ₹100k/2% account-affordability gate.
- No SENSEX outcome is used to change the frozen strategy rules.
\n\n### S6 provenance correction — 2026-09-20\nA reproducibility audit found that the initial S6 workflow did not reproduce the validated S5 Monte Carlo/regime-history input. The S6 workflow was corrected to rebuild the exact composite daily SENSEX history used by the completed S5 transfer run and to use --mc-index-path for all scenarios.\n\n### S6 completion — 2026-09-20\nNumerical robustness phase completed. Clean committed outputs now include the slippage grid, five-seed OOS sensitivity, and 10,000-repetition circular moving-block bootstrap. Final combined validation+holdout base-slippage results: Adaptive n=64, mean ₹2,612.93, bootstrap 95% CI -₹804.31 to ₹6,133.11; Batman n=44, mean ₹5,742.06, bootstrap 95% CI ₹662.67 to ₹10,341.49.