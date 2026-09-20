# Limited-Risk Option WFO Research — v1

## 1. Research identity

Parent research: NIFTY MC-WFO (research/monte-carlo-wfa-v1)

New research branch: research/limited-risk-option-wfo-v1

Purpose: extend the NIFTY Monte Carlo + Walk-Forward framework to option strategies whose maximum loss is finite and known from the strategy/payoff definition, while retaining both:
- strategies with limited loss + limited profit; and
- strategies with limited loss + potentially unlimited profit.

Batman remains outside this study's eligible universe because its tail loss is not bounded by a predefined maximum loss.

This branch is an independent strategy-family study and must not contaminate the conclusions of the existing NIFTY MC-WFO manuscript until its results are completed and independently reviewed.

---

## 2. Research questions

### Primary question

Does the existing leakage-resistant NIFTY Monte Carlo / walk-forward forecasting framework produce a reproducible, economically meaningful out-of-sample advantage when translated into defined-loss option strategies, after realistic transaction costs, brokerage, bid/ask execution and slippage?

### Secondary questions

1. Which limited-loss strategy families are robust across directional and volatility regimes?
2. Which strategies have limited loss with unlimited upside, and do they retain positive OOS expectancy after costs?
3. Which strategies have both limited loss and limited profit, and do their capped payoffs compensate adequately for capital at risk?
4. Does the edge come from the MC distribution forecast itself, from regime classification, from strike placement, or from option-market pricing/selection?
5. Does strategy selection remain stable under expanding and rolling WFO rather than one fixed train/validation split?
6. Does performance survive cost/slippage stress and realistic execution assumptions for an Indian retail account?
7. Does any selected strategy pass CPCV, block-bootstrap, multiple-testing, and data-snooping controls?
8. Does any strategy survive a fresh holdout period that was not used in the already-exposed 2026 research?
9. What minimum capital and risk budget are required when maximum loss is used as the hard per-trade risk constraint?
10. Can a strategy be promoted to prospective paper trading without relying on model results selected after seeing its final holdout?

---

## 3. Aims

### Aim 1 — Build a mechanically verified limited-risk universe

Identify every strategy in the existing strategy catalog whose terminal loss is finite under the declared entry convention and whose payoff can be independently audited.

### Aim 2 — Integrate limited-risk strategies with the frozen MC-WFO signal stack

Use only information available at each historical decision timestamp to forecast the expiry distribution, construct strikes, estimate execution prices and calculate expected strategy P&L.

### Aim 3 — Compare strategy families on a common economic basis

Evaluate raw P&L, P&L after costs, return on maximum loss/risk capital, drawdown, tail loss, probability of profit, forecast calibration and capital efficiency.

### Aim 4 — Quantify robustness and selection risk

Use nested WFO, CPCV, moving-block bootstrap, cost/slippage sensitivity and multiple-testing controls before any candidate is considered suitable for prospective paper trading.

### Aim 5 — Establish a clean validation boundary

Do not reuse the already-exposed 2026 holdout for model selection. Any post-selection confirmation must use a later observation window that is demonstrably outside all prior selection and reporting.

---

## 4. Objectives

1. Produce a deterministic strategy risk-audit engine.
2. Produce a single frozen strategy-eligibility table with evidence for every catalog strategy.
3. Verify strike construction and quote availability for every candidate.
4. Reuse cached historical option-chain artifacts wherever possible.
5. Model executable entry and exit prices using bid/ask rules before computing P&L.
6. Include brokerage, exchange/statutory charges, GST where applicable, slippage and turnover-related costs.
7. Preserve the existing 3-session-before-expiry MC framework as a baseline comparator.
8. Test both expanding and rolling WFO configurations.
9. Separate development, validation and untouched test selection at every nested layer.
10. Report results by calendar year, volatility regime, direction regime and strategy family.
11. Apply a predeclared acceptance gate; no candidate can be promoted because its holdout result looks attractive.
12. Produce a full manuscript-ready evidence package, not a single headline backtest.

---

# 5. Eligibility and risk taxonomy

## 5.1 Mechanical definition of limited loss

A candidate is eligible only when the strategy risk auditor can establish a finite upper bound on terminal loss over the full relevant underlying-price domain, using the exact leg quantities and strikes.

The auditor must evaluate:
- terminal payoff on a dense underlying-price grid;
- both far-tail limits;
- maximum loss and its location;
- maximum profit when finite;
- whether profit is mathematically unbounded on either tail;
- net entry debit/credit under the execution model;
- per-strategy-unit and per-contract maximum rupee loss.

No manual risk label is authoritative.

## 5.2 Candidate families

### Family A — Limited loss + potentially unlimited profit

Initial candidates from the existing catalog include:
- Buy Call
- Buy Put
- Long Straddle
- Long Strangle
- Strip
- Strap
- Call Ratio Back Spread
- Put Ratio Back Spread

These require exact debit/credit and payoff verification. A ratio backspread is eligible only if the realized structure has finite maximum loss under the selected strikes/prices.

### Family B — Limited loss + limited profit

Initial candidates include:
- Bull Call Spread
- Bear Put Spread
- Bull Put Spread
- Bear Call Spread
- Bull Condor
- Bear Condor
- Bull Butterfly
- Bear Butterfly
- Long Iron Butterfly
- Long Iron Condor
- Iron Butterfly
- Short Iron Condor

A strategy must still pass the mechanical risk audit; the catalog name alone is not sufficient.

### Family C — Path-/expiry-dependent limited-risk structures

Initial candidates:
- Long Calendar with Calls
- Long Calendar with Puts
- any other catalog structure whose risk cannot be established from a single terminal payoff.

These are a separate sub-study and must not be mixed with single-expiry terminal-payoff statistics unless the multi-expiry valuation and path assumptions are explicitly specified.

### Explicitly excluded from the limited-risk core

The following are not eligible for the core phase because they have an unbounded adverse tail under their stated structure:
- Batman
- Short Straddle
- Short Strangle
- Call Ratio Spread
- Put Ratio Spread
- Jade Lizard
- Reverse Jade Lizard
- Long Synthetic Future
- Short Synthetic Future
- Risk Reversal
- any other strategy that fails the mechanical risk audit.

An exclusion can be revisited only if the structure itself is changed so that maximum loss becomes finite.

---

# 6. Scientific phases

## L0 — Protocol freeze and repository audit

Purpose: establish the immutable protocol before new historical results are generated.

Tasks:
- freeze this research question, eligibility rule and acceptance criteria;
- verify parent-branch commit and inherited methodology;
- inventory existing WFO, regime, cost, option-chain and test artifacts;
- identify which dates have already been exposed in previous research;
- define the fresh-holdout boundary;
- create phase-specific branches;
- record inherited errors and controls.

Deliverables:
- protocol document;
- baseline commit SHA;
- exposure map;
- phase status;
- error log;
- conversation/audit log.

Gate: protocol is frozen; no performance result is used for selection yet.

---

## L1 — Literature review and strategy taxonomy

Purpose: establish the theoretical and empirical basis for limited-loss option strategy selection.

Search and extract evidence from:
- peer-reviewed option-pricing and strategy literature;
- academic work on volatility risk premia and option strategies;
- walk-forward and backtest-overfitting literature;
- CPCV / purged validation literature;
- bootstrap and multiple-testing literature;
- exchange/broker documentation relevant to Indian option execution;
- authoritative NSE/BSE/SEBI and Paytm Money documentation for trading mechanics and charges.

The review must distinguish:
- theoretical payoff properties;
- empirical historical findings;
- broker/exchange implementation rules;
- claims that are not directly relevant to the NIFTY weekly-option setting.

Deliverables:
- literature evidence table;
- strategy taxonomy;
- citation file;
- exact definitions used by this study.

Gate: every tested strategy family has a documented rationale and a declared risk class.

---

## L2 — Data audit and executable market-data layer

Purpose: verify that every backtest uses real observations and a reproducible execution convention.

Tasks:
- inspect cached historical option-chain artifacts;
- verify timestamps, expiries, strikes, option type and quote fields;
- identify whether bid/ask is available or reconstructed;
- verify actual listed expiries rather than calendar assumptions;
- document missing observations;
- do not impute missing executable quotes;
- preserve the cached-data-first workflow;
- record data coverage and final usable date.

Execution rules:
- long legs use ask for conservative entry;
- short legs use bid for conservative entry;
- exits use bid for closing longs and ask for closing shorts;
- if bid/ask is unavailable, use only a separately documented reconstruction rule;
- same-bar look-ahead is prohibited.

Costs:
- retain the existing research stress convention as a baseline;
- separately model brokerage, exchange/statutory charges, GST and other applicable costs;
- include adverse slippage per leg;
- run a predefined sensitivity grid;
- retain exact cost assumptions with every run artifact;
- live Paytm Money deployment assumptions must be re-verified from the then-current broker documentation and/or captured broker margin/charges snapshot before paper/live use.

Gate: data-quality report passes all schema and coverage checks.

---

## L3 — Strategy risk-audit engine

Purpose: mechanically prove whether each catalog structure has finite maximum loss.

For every strategy/strike set:
1. construct all legs;
2. calculate net premium cashflow from executable prices;
3. evaluate payoff over a dense underlying-price grid;
4. evaluate both tails;
5. determine max loss and max profit;
6. identify unlimited-profit side, when present;
7. calculate maximum loss in option points and rupees;
8. compare analytical and numerical risk bounds where possible;
9. reject ambiguous or discontinuous results.

Tests must include:
- strike ordering;
- sign of quantities;
- expiry consistency;
- premium sign;
- extreme-underlying tails;
- zero/near-zero premium handling;
- missing-leg handling.

Gate: risk-classification table is deterministic and all eligible structures have unit tests.

---

## L4 — WFO strategy-construction engine

Purpose: connect forecast distributions to limited-risk structures without look-ahead.

For each decision date:
- freeze model data at the decision cutoff;
- generate the existing MC terminal distribution;
- derive any target strikes from declared quantiles/deltas/ranks;
- obtain executable historical quotes at the decision time;
- construct only strategies meeting the declared risk class;
- calculate gross and net MC EV;
- calculate MC probability of profit;
- calculate maximum loss and return-on-risk;
- record all inputs used for the decision;
- freeze the trade before observing expiry outcome.

Core baseline:
- 3 trading sessions before expiry;
- 5,000 MC paths for the strategy lab unless a predeclared phase changes the path count;
- 756 completed daily-return lookback;
- deterministic seed sequence.

Gate: unit/integration tests prove that no future observation enters strike selection, strategy selection, cost calculation or entry eligibility.

---

## L5 — Broad strategy WFO

Purpose: establish an unbiased comparison across the full eligible universe before any selection.

Evaluate:
- all eligible limited-risk strategies;
- expanding and rolling training windows;
- existing forecast model variants;
- declared strike-selection rules;
- declared cost/slippage scenarios.

Required outputs:
- trade count;
- win rate;
- mean/median P&L;
- total P&L;
- profit factor;
- maximum drawdown;
- worst trade;
- maximum-loss utilization;
- return on maximum risk;
- Sharpe/Sortino;
- MC EV and realized P&L;
- MC PoP vs realized hit rate;
- interval/forecast metrics where applicable.

Report:
- pooled;
- calendar year;
- volatility regime;
- direction regime;
- strategy family.

Gate: descriptive comparison only; no final candidate promotion.

---

## L6 — Nested strategy/regime selection

Purpose: select strategies only from information available before each test period.

Protocol:
- development data only for candidate generation;
- validation for model/strategy selection;
- final holdout never inspected until the selection pipeline is frozen;
- nested selection at the regime level;
- allow NO_TRADE;
- minimum trade-count thresholds;
- conservative score based on mean minus standard error or a predeclared equivalent;
- strategy-family constraints only when justified before selection.

Selection must be deterministic and use fixed seeds. Do not use Python's randomized hash() to construct bootstrap seeds.

Gate: a frozen strategy map exists before fresh holdout evaluation.

---

## L7 — Robustness and statistical inference

Purpose: test whether observed performance survives dependence, multiple testing and reasonable execution perturbations.

Required analyses:
- CPCV;
- circular/moving-block bootstrap;
- confidence intervals for mean P&L and return-on-risk;
- annual and regime stability;
- cost/slippage sensitivity;
- strike perturbation;
- MC path-count sensitivity;
- volatility-model sensitivity;
- expanding vs rolling WFO;
- alternative predeclared entry timing;
- missing-quote sensitivity.

Multiple-testing controls:
- predeclare the candidate universe before evaluation;
- report all tested strategies;
- use a data-snooping control such as White's Reality Check and/or Hansen SPA where computationally appropriate;
- report selection frequency and false-discovery diagnostics;
- do not report only the surviving strategy.

Gate: candidate must survive all mandatory robustness tests, not just average P&L.

---

## L8 — Fresh untouched holdout

Purpose: obtain genuinely new OOS confirmation.

Important control:
- the historical 2026 period already exposed by prior NIFTY MC-WFO research is not a fresh holdout;
- this phase may only use observations after the frozen prior exposure boundary and only if those observations were not used for strategy design, tuning or reporting;
- if the cached dataset does not extend far enough, the correct result is HOLD — insufficient fresh data, not a backtest using an exposed period.

Required outputs:
- frozen strategy and parameters;
- first/last fresh-holdout observation;
- no tuning on the fresh period;
- full trade-level audit trail.

Gate: positive evidence is necessary but not sufficient; no promotion is allowed unless all preceding gates also pass.

---

## L9 — Capital, margin and operational feasibility

For each surviving strategy:
- calculate maximum loss per strategy unit;
- calculate maximum rupee loss using the applicable lot-size schedule;
- calculate conservative capital reserve;
- separate maximum-loss capital from broker margin;
- capture current Paytm Money margin/charge information for the exact basket before deployment;
- include a reserve for slippage and execution failures;
- model simultaneous positions where relevant;
- calculate portfolio-level worst-case loss under correlated signals;
- test whether simultaneous strategies can coexist inside the risk budget.

Gate: strategy has a clear finite loss limit and operationally feasible position sizing.

---

## L10 — Prospective paper-trading specification

Only a strategy that passes L0-L9 may enter paper trading.

The paper signal must publish:
- entry timestamp;
- model cutoff;
- strategy and risk class;
- strikes;
- executable entry quotes;
- net debit/credit;
- maximum loss;
- MC EV;
- MC PoP;
- position size;
- capital reserved;
- exit rule;
- actual quote timestamp;
- NO_TRADE reason when data are invalid.

No broker order is placed.

Gate: paper-trading specification is reproducible and auditable.

---

## L11 — Final inference and manuscript

The final manuscript must contain:
1. abstract;
2. introduction and literature review;
3. research questions;
4. aims and objectives;
5. data sources and data audit;
6. mathematical strategy definitions;
7. risk-classification method;
8. Monte Carlo forecasting method;
9. WFO protocol;
10. transaction-cost/slippage model;
11. statistical analysis;
12. results;
13. robustness and multiple-testing controls;
14. capital/risk analysis;
15. discussion;
16. strengths and limitations;
17. conclusion;
18. future research;
19. appendices;
20. complete strategy-level tables;
21. graphs and charts;
22. reproducibility appendix with commit IDs, seeds and workflow runs.

The existing NIFTY MC-WFO manuscript remains separate until this branch is complete.

---

# 7. Acceptance criteria

A strategy may become a research candidate only when all of the following are true:

1. mechanically verified finite maximum loss;
2. no look-ahead leakage;
3. executable or explicitly reconstructed bid/ask prices;
4. net positive MC-EV gate evaluated without future data;
5. minimum sample size met in all required selection stages;
6. positive OOS mean P&L and economically meaningful return-on-risk;
7. profit factor > 1 on required validation/holdout sets;
8. robust under predefined cost/slippage stresses;
9. no material failure in CPCV/block-bootstrap diagnostics;
10. no decisive failure from multiple-testing controls;
11. survives the fresh untouched holdout;
12. capital sizing is consistent with the finite maximum-loss rule.

A strategy that fails any mandatory gate is not promoted, even if another metric looks attractive.

---

# 8. Primary comparators

Every surviving strategy is compared with:
- no-trade;
- always-neutral/no-position benchmark;
- existing Long Iron Condor baseline;
- existing Batman strategy as a descriptive comparator only, never as an eligible limited-risk candidate;
- simple directional option benchmarks where applicable;
- equally weighted strategy-family portfolio, if the portfolio test is predeclared.

No comparator may be removed after results are known.

---

# 9. Reproducibility controls

- fixed random seeds;
- deterministic bootstrap seeds;
- immutable acquisition run IDs;
- cached data artifacts preferred over repeated downloads;
- phase-specific Git branches;
- GitHub Actions with workflow_dispatch;
- tests required before long historical runs;
- every error entered in the phase error log;
- every phase status updated after every execution;
- every research decision entered in the conversation/audit log;
- main README updated with links to current branch/status/results.

---

# 10. Known methodological controls carried forward

1. Never use same-minute bar closes to represent a decision or exit at the bar open.
2. Never infer exchange expiry from a calendar rule when an actual listed expiry is available.
3. Never impute missing executable quotes silently.
4. Never use the already-exposed 2026 holdout to tune a new strategy.
5. Never equate positive MC expected value with guaranteed market edge.
6. Never substitute historical P&L for live broker margin.
7. Never rely on manually curated risk labels when mechanical payoff analysis is available.
8. Never use process-randomized hashing for statistical seeds.
9. Never present pooled positive results without year/regime and drawdown analysis.
10. Never promote a candidate from a single strategy-selection screen without robustness and multiple-testing controls.

---

# 11. Planned artifacts

- docs/limited_risk_option_wfo/RESEARCH_PLAN.md
- docs/limited_risk_option_wfo/PHASE_STATUS.md
- docs/limited_risk_option_wfo/ERROR_LOG.md
- docs/limited_risk_option_wfo/CONVERSATION_LOG.md
- docs/limited_risk_option_wfo/STRATEGY_UNIVERSE_AND_RISK_RULES.md
- docs/limited_risk_option_wfo/COST_AND_EXECUTION_POLICY.md
- configs/limited_risk_option_wfo_v1.yaml
- phase-specific analysis scripts, tests and results
- GitHub Actions workflows with manual dispatch
- manuscript, figures, tables and supplements

---

# 12. Stopping rule

The research stops after L11.

It must not continue indefinitely through ad-hoc strategy additions. Any strategy not declared in the frozen universe is a separate future research project with a new protocol and fresh validation boundary.
