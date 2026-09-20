# BATMAN Tuning Research Plan

## Aim
Determine whether controlled changes to BATMAN entry timing and exit management improve out-of-sample performance after brokerage, statutory charges, slippage and realistic execution assumptions.

## Questions
1. Does D0-D6 outperform the frozen D3 entry rule on matched opportunities?
2. Does prior-session signal plus market-open execution differ materially from the same-session 09:30 signal?
3. Do fixed target, fixed stop, trailing target or trailing stop rules improve the realized return distribution relative to the frozen exit?
4. Are gains stable across walk-forward windows, years, volatility regimes, cost assumptions and Monte Carlo seeds?
5. Does any selected candidate survive nested walk-forward selection and multiple-testing diagnostics well enough to justify a new prospective freeze?

## Phase sequence
T0 protocol freeze; T1 data and frozen-control reconstruction; T2 entry tuning; T3 exit tuning; T4 nested WFO; T5 robustness and statistical inference; T6 prospective freeze.

## Anti-leakage rule
A candidate may use only information available at its decision timestamp. Final-holdout and prospective observations cannot influence tuning. Same-bar execution ambiguity must use a pre-declared conservative convention.

## Final outputs
Trade-level results, candidate matrix, nested-WFO results, bootstrap confidence intervals, multiple-testing diagnostics, cost/slippage sensitivity, regime/year tables, figures, limitations, conclusion and prospective deployment specification.
