# Statistical Analysis Plan

Primary comparison: paired net P&L difference versus the frozen control on matched eligible opportunities.

Report trade count, mean and median P&L, expectancy, win rate, profit factor, cumulative P&L, maximum drawdown, return on capital, tail losses, maximum adverse excursion, turnover and transaction-cost burden.

Use a circular moving-block bootstrap with 10,000 repetitions for serially dependent trade outcomes. Report 95% intervals for mean P&L and paired differences.

Because the candidate grid is large, raw historical maxima are not evidence of superiority. The final report must include candidate count, nested-WFO selection, bootstrap inference and a multiple-testing/data-snooping diagnostic.

Robustness must include cost and slippage stress, calendar splits, volatility regimes, parameter perturbation and Monte Carlo seed sensitivity.
