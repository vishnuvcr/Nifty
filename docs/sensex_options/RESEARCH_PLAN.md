# SENSEX Options Transfer Research — Batman + Adaptive v1

## Research boundary

This is a separate transfer-validation study for BSE SENSEX index options. It does not modify, backfill, re-optimize, or contaminate the NIFTY MC-WFO research manuscript.

The purpose is to test whether the two frozen Phase-10 NIFTY strategy specifications retain evidence of utility when transferred to SENSEX options under SENSEX-specific contract, calendar, liquidity, quote, and transaction-cost assumptions.

### Frozen NIFTY research components being transferred

Batman:
- Entry timing: 09:30 IST.
- Target expiry: exactly 3 future trading sessions from entry.
- 5,000 bootstrap Monte Carlo paths.
- 756 completed daily log-return lookback.
- Terminal quantiles P20/P35/P65/P80 mapped to nearest unique listed strikes.
- Buy 1×P35, sell 2×P20, buy 1×C65, sell 2×C80.
- Entry gate: net MC EV > 0 and at least one risk-sized lot.
- Risk sizing proxy: max(ES95, ES99).
- NIFTY research stress cost of 2 option points/contract is not assumed valid for SENSEX; SENSEX-specific execution costs must be sourced.

Adaptive:
- Frozen candidate sets: low = Risk Reversal, Long Synthetic Future, Buy Call; medium = Short Straddle, Put Ratio Spread, Short Strangle, Strip, Buy Put; high = Sell Put, Risk Reversal, Long Synthetic Future, Batman.
- Candidate eligibility: net MC EV > 0 and at least one risk-sized lot.
- Primary candidate: highest net MC EV among eligible candidates.
- The primary-selection rule remains explicitly prospective/unvalidated on the original NIFTY study and is not retuned on SENSEX before the first holdout.

## Phase structure

### Phase S0 — Transfer specification freeze
Status: IN PROGRESS

Freeze the exact NIFTY Batman and Adaptive code/configuration used as the parent specification. Record source commit SHA and configuration hashes. Define all SENSEX-specific substitutions before looking at SENSEX outcome data.

Exit criterion: signed-off transfer specification and no unresolved leakage or universe-definition ambiguity.

### Phase S1 — SENSEX data-source and contract audit
Status: NOT STARTED

Establish auditable sources for SENSEX daily closes, trading calendar/holidays, BSE SENSEX option expiries, historical option chains, and contract/lot-size history.

Requirements: point-in-time data; historical lot-size changes represented explicitly; missing bid/ask never silently replaced by LTP; source provenance and retrieval metadata cached with the dataset.

Exit criterion: reproducible schema-validated SENSEX data manifest covering the intended study period.

### Phase S2 — SENSEX execution-cost model
Status: NOT STARTED

Model Paytm Money brokerage per executed order, BSE turnover charges, STT, GST, SEBI charges, stamp duty, bid/ask spread, explicit slippage stress, and relevant conditional fees. Do not copy NIFTY cost assumptions without evidence.

Exit criterion: reproducible per-leg and per-trade net-P&L calculator with a sensitivity grid around the base cost.

### Phase S3 — SENSEX Batman implementation
Status: NOT STARTED

Port frozen Batman logic without optimizing research degrees of freedom. Allowed changes are instrument/data source, SENSEX calendar, expiry schedule, historical lot size, listed strike grid/available strikes, execution costs, and data-quality controls.

Exit criterion: unit tests plus deterministic replay on hand-checked SENSEX cases.

### Phase S4 — SENSEX Adaptive implementation
Status: NOT STARTED

Port the frozen Adaptive candidate router exactly. Do not reselect candidates using SENSEX outcomes before the primary holdout. Regime classification must be strictly past-only.

Exit criterion: unit tests plus candidate-screen audit showing no future-data dependence.

### Phase S5 — Historical walk-forward transfer test
Status: NOT STARTED

Use chronological train/development, validation, and untouched final holdout periods. Evaluate Batman standalone, the Adaptive primary signal, and every Adaptive candidate diagnostically. Report no-trade frequency, year/regime splits, cost sensitivity, quote-quality sensitivity, strike-gap/rounding sensitivity, and lot-size-aware P&L.

Primary inference must follow the pre-registered rule, not post-hoc strategy selection.

### Phase S6 — Robustness and statistical inference
Status: NOT STARTED

Report trade count, total/mean/median P&L, expectancy, win rate, profit factor, max drawdown, Sharpe/Sortino where sample size permits, tail losses, turnover, net versus gross P&L, dependence-aware bootstrap intervals, yearly/regime stratification, MC seed sensitivity, transaction-cost sensitivity, and quote-source sensitivity.

### Phase S7 — Prospective paper-trading gate
Status: NOT STARTED

Only after S1–S6 pass their data-integrity and scientific-validity checks. Generate a SENSEX-only paper ledger using the frozen rules. The first prospective observation must never be backfilled.

### Phase S8 — Conclusion and separate manuscript supplement
Status: NOT STARTED

Produce a standalone SENSEX transfer report with methods, data provenance, results, uncertainty, comparison with the frozen NIFTY source strategy, limitations, practical conclusion, and future research directions. The main NIFTY manuscript remains NIFTY-only unless a separate cross-index study is later approved.

## Bias controls
1. No tuning on the final SENSEX holdout.
2. No reopening of the already-used NIFTY holdout.
3. No candidate replacement based on SENSEX hindsight.
4. No LTP substitution when executable quotes are missing.
5. No future expiry/strike availability used at decision time.
6. Historical contract-size changes are applied by effective date.
7. All transaction costs and slippage are deducted from reported net results.
8. Any deviation from the frozen rule set is logged before results are interpreted.

## Required repository artefacts
- docs/sensex_options/RESEARCH_PLAN.md
- docs/sensex_options/PHASE_STATUS.md
- docs/sensex_options/ERROR_LOG.md
- docs/sensex_options/CONVERSATION_LOG.md
- docs/sensex_options/DATA_MANIFEST.md
- configs/sensex_batman_v1.json
- configs/sensex_adaptive_v1.json
- data/sensex_options/ for cached/validated source data where licensing permits
- reports/sensex_options/ for immutable experiment outputs
- phase workflows with manual workflow_dispatch, one phase per phase branch