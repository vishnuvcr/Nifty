# NIFTY Monte Carlo Walk-Forward Research
## Limited-Loss Option Strategy Extension v1

### Abstract

This study extends the NIFTY Monte Carlo and walk-forward framework to option strategies with finite maximum terminal loss. The starting universe contains 36 strategies from the existing NIFTY MC-WFO catalogue. A mechanical payoff audit over the economically admissible index domain S >= 0 classified 27 strategies as finite-loss core candidates, two as multi-expiry/path-dependent structures, and seven as unbounded-adverse-loss structures. Batman was correctly excluded because its aggregate short-call tail produces unbounded loss as the index rises without bound.

Using the frozen parent strategy-regime artifact, the limited-risk branch performed a historical development/validation study with a net Monte Carlo expected-P&L gate and a 2-option-point-per-contract execution stress. Jade Lizard and Put Ratio Spread were among the strongest validation candidates. A pre-2025 CPCV/block-bootstrap analysis produced a positive confidence interval for selected path means. However, a cross-strategy max-statistic block bootstrap across the 27 eligible strategies produced p=0.7426, indicating that the strongest observed mean is not statistically distinguished under the implemented multiple-testing diagnostic. The parent research has also already exposed the 2025-2026 period, so it cannot serve as a fresh final holdout.

The resulting conclusion is therefore conservative: finite-loss strategies show promising historical conditional performance, but no strategy is promoted to paper or live trading from this phase. Fresh post-exposure data and deployment-grade historical bid/ask records are required.

---

## 1. Introduction

The parent NIFTY MC-WFO project uses a Monte Carlo model and chronological walk-forward evaluation to study expiry-range forecasts and option strategies. A key weakness of the Batman structure is its unbounded adverse terminal tail. This motivates a separate study of strategies whose structural loss can be bounded before position sizing.

The research objective is not simply to find the highest historical P&L. The branch is designed to control look-ahead leakage, execution optimism, strategy-search bias and holdout contamination.

---

## 2. Research questions

1. Which strategies in the existing catalogue have a finite maximum terminal loss on the S >= 0 NIFTY domain?
2. Which finite-loss strategies produce positive net historical out-of-sample performance under the frozen MC gate?
3. Are candidate strategies stable under development/validation selection and CPCV?
4. Does performance survive explicit adverse transaction-cost stress?
5. Is the observed best strategy distinguishable from a strategy-search null?
6. Is there an untouched future dataset suitable for confirmation?

---

## 3. Aims and objectives

The study aimed to create a mechanically verified finite-loss strategy universe, connect it to the existing MC-WFO framework, compare candidate families, quantify robustness, incorporate costs/slippage, and prohibit promotion unless a clean future holdout is available.

Operational objectives included deterministic statistical seeds, cached-data-first execution, auditable phase logs, strategy-level result tables, and explicit separation of research risk from current broker margin.

---

## 4. Scientific methodology

### 4.1 Parent MC/WFO framework

The frozen parent artifact uses:
- 3 trading sessions before expiry;
- 5,000 Monte Carlo terminal paths;
- 756 completed daily log-return observations;
- a net MC expected-P&L > 0 trade gate;
- past-only regime features;
- chronological development, validation and later-period evaluation.

### 4.2 Risk classification

For each catalogue strategy, the exact leg quantities are constructed from the executable strategy catalogue. The audit evaluates:
- the aggregate call payoff slope as S -> infinity;
- a dense S >= 0 payoff grid;
- expiry structure;
- finite versus unbounded terminal loss;
- finite versus potentially unbounded favourable profit.

A negative aggregate call slope produces an unbounded adverse upper tail. Put-only short exposure remains finite as S approaches zero because the index domain is non-negative.

### 4.3 Execution assumptions

The inherited archive provides EOD option close prices, not a verified historical bid/ask stream. Therefore the backtest is explicitly labelled an EOD reconstruction.

The comparative research stress is 2 option points per contract. A selected-candidate sensitivity grid uses 0, 0.5, 1, 2 and 3 points per contract.

### 4.4 Validation

Strategy selection is separated into development and validation. A volatility-regime selection layer is evaluated separately. Robustness includes:
- CPCV;
- moving-block bootstrap;
- a cross-strategy max-statistic block bootstrap;
- cost stress.

The multiple-testing diagnostic is described as Reality-Check-style rather than claimed to be a full Hansen SPA implementation.

---

## 5. Results

### 5.1 Mechanical risk audit

27 of 36 strategies passed the finite-loss core audit.

Batman was classified:
- risk class X;
- loss_unbounded = true;
- profit_unbounded = false;
- core_limited_risk = false.

Two calendars were placed in R3 because their multi-expiry/path-dependent valuation cannot be represented by a single terminal intrinsic payoff.

Seven strategies with unbounded adverse upper tails were excluded from the core.

### 5.2 Validation leaders

At the 2-point-per-contract stress and net-MC-EV gate:

| Strategy | n | Mean P&L | PF | Win rate |
|---|---:|---:|---:|---:|
| Jade Lizard | 29 | +98.19 | 4.02 | 72.41% |
| Short Iron Condor | 19 | +66.49 | 2.85 | 73.68% |
| Put Ratio Spread | 35 | +61.88 | 3.16 | 80.00% |
| Strip | 168 | +52.15 | 1.59 | 41.67% |
| Strap | 176 | +31.08 | 1.29 | 45.45% |
| Long Straddle | 173 | +29.09 | 1.50 | 46.24% |
| Long Strangle | 171 | +26.52 | 1.52 | 38.60% |
| Sell Put | 49 | +22.95 | 1.29 | 69.39% |

### 5.3 Nested global selection

Four strategies passed the predeclared development-to-validation gate:

| Strategy | Development n | Validation n | Validation mean | Validation PF |
|---|---:|---:|---:|---:|
| Jade Lizard | 98 | 29 | +98.19 | 4.02 |
| Put Ratio Spread | 97 | 35 | +61.88 | 3.16 |
| Sell Put | 113 | 49 | +22.95 | 1.29 |
| Bull Put Spread | 123 | 28 | +16.23 | 1.36 |

The frozen global candidate was Jade Lizard.

### 5.4 Volatility regime

Only the medium-volatility -> Jade Lizard map passed the predefined validation gate.

Validation result:
- 13 trades;
- mean +101.93 points;
- PF 6.95.

The later 2025-2026 result is explicitly exposed and cannot be considered fresh confirmation.

### 5.5 CPCV and bootstrap

Fifteen CPCV paths were evaluated.

The block-bootstrap 95% confidence interval for selected path means was:

**+31.62 to +49.93 points**

Bootstrap probability of a non-positive mean was 0.000.

### 5.6 Multiple-testing diagnostic

Across 27 eligible strategies and 480 decision dates:
- observed best mean per decision: +17.74;
- block length: 5;
- repetitions: 5,000;
- bootstrap p-value: **0.7426**.

This is the principal reason the study does not promote the historically strongest strategy.

### 5.7 Cost stress

For Jade Lizard in the already-exposed later sample, mean P&L remained positive from 0 to 3 stress points per contract, including +38.01 points/trade at the 3-point stress. Because that sample is already exposed, this is a robustness description rather than new OOS evidence.

---

## 6. Statistical inference

The positive CPCV result shows historical stability of selected path returns. However, the broad strategy-search diagnostic indicates that the best observed result can plausibly arise from selection across many candidate strategies.

This is consistent with published work on backtest overfitting and data-snooping correction, which motivates combinatorial validation and reality-check-style procedures when many rules are searched.

Accordingly, the evidence supports a hypothesis-generation conclusion, not a deployment conclusion.

---

## 7. Discussion

The most important result is not the raw +98.19-point Jade Lizard validation mean. It is the combination of:
1. a substantial historical effect under the MC gate;
2. a positive CPCV sensitivity;
3. a non-supportive cross-strategy multiple-testing diagnostic;
4. an already-exposed later sample;
5. the absence of historical bid/ask execution data.

Taken together, these findings are insufficient to call the strategy validated.

The branch nevertheless demonstrates that the finite-loss universe is materially different from Batman. Structural maximum loss can be established before sizing, and the research can therefore move toward risk-budgeted strategies without relying on Monte Carlo ES as a substitute for a hard loss boundary.

---

## 8. Strengths

- Mechanical risk audit rather than manual risk labels.
- Frozen parent MC/WFO process.
- Explicit development/validation separation.
- CPCV and block-bootstrap analysis.
- Multiple-testing diagnostic.
- Cost/slippage sensitivity.
- Prior holdout contamination explicitly recognized.
- Reproducible GitHub Actions run and artifact provenance.

---

## 9. Limitations

1. Historical option data are EOD close, not verified bid/ask.
2. Parent trade artifact does not contain complete leg-level execution records needed for deployment-grade capital reconstruction.
3. The 2025-2026 period has already been exposed.
4. The max-statistic diagnostic is not a full Hansen SPA implementation.
5. Calendars are outside the single-expiry core.
6. Current broker margin must be checked against the exact basket at deployment time.

---

## 10. Capital and operational implications

Finite structural loss is the primary risk bound in this branch. Monte Carlo ES95/ES99 is secondary.

Current external execution parameters must be refreshed at deployment:
- NSE published the current option-sale STT schedule effective 1 April 2026;
- Paytm Money's current F&O FAQ lists ₹10 brokerage per unique executed order;
- exact option-writer margin is dynamic and must be obtained from the current broker margin calculator;
- applicable NIFTY lot size depends on the contract schedule.

No deployment-grade capital figure is claimed from this phase.

---

## 11. Conclusion

The limited-risk phase produced several historically attractive candidates, especially Jade Lizard and Put Ratio Spread. However, the evidence does not survive the full inferential standard required for promotion because strategy-search multiplicity remains unresolved and the apparent final period is already exposed.

**Final research decision for this phase: HOLD. No paper/live strategy is promoted.**

---

## 12. Future research

The next valid step is:
1. acquire genuinely new NIFTY option observations after the frozen exposure boundary;
2. preserve complete leg-level bid/ask or a validated reconstruction;
3. freeze the candidate set before opening the fresh holdout;
4. rerun the fixed candidate rules without retuning;
5. apply the same statistical and multiple-testing gates;
6. only then evaluate prospective paper trading.

---

## Appendix A — Provenance

Parent strategy artifact:
- workflow run: 35425922439
- artifact: strategy-regime-lab-v2-results

Limited-risk workflow:
- workflow run: 35496685719
- artifact: limited-risk-option-wfo-v1-results

Repository branch:
- research/limited-risk-option-wfo-v1

## Appendix B — Repository outputs

- reports/limited_risk_wfo/FINAL_PHASE_REPORT.md
- reports/limited_risk_wfo/RISK_CLASSIFICATION.csv
- reports/limited_risk_wfo/VALIDATION_KEY_RESULTS.csv
- reports/limited_risk_wfo/NESTED_SELECTION.csv
- reports/limited_risk_wfo/CPCV_MULTIPLE_TESTING.csv
- reports/limited_risk_wfo/CANDIDATE_COST_STRESS.csv
- reports/limited_risk_wfo/REGIME_ROUTER_SUMMARY.csv

## Appendix C — Literature

- Bailey et al., The Probability of Backtest Overfitting.
- Bailey & López de Prado, The Deflated Sharpe Ratio.
- Sullivan, Timmermann & White, Data-Snooping, Technical Trading Rule Performance, and the Bootstrap.
- Hsu & Kuan, Re-Examining the Profitability of Technical Analysis with White's Reality Check and Hansen's SPA.
