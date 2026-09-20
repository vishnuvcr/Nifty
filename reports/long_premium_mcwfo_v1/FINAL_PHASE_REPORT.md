# NIFTY Long-Premium MC/WFO v1 — Final Phase Report

## Executive result

The study asked whether the NIFTY MC/WFO forecast could identify sufficiently cheap Buy Call or Buy Put opportunities with positive expected value after execution stress and brokerage.

The frozen development selector chose:

**Buy Call, premium <= 0.55% of spot**

Development result:
- n = 33
- mean = +64.89 points/trade
- profit factor = 3.218

The frozen rule then failed the validation gate:

- n = 70
- mean = **-1.68 points/trade**
- profit factor = **0.968**
- win rate = 37.1%
- block-bootstrap 95% CI = **-24.92 to +29.70**
- bootstrap P(mean <= 0) = **0.439**

Cross-rule multiple-testing diagnostic:
- 22 predeclared rules
- 480 pre-2025 decision dates
- block length 5
- 5,000 repetitions
- observed best mean per decision = +4.844
- Reality-Check-style p = **0.886**

This is a max-statistic diagnostic, not a full Hansen SPA.

The 2025-2026 period is already exposed by the parent research and is therefore descriptive only. For the selected rule it produced n=31, mean **-30.40** points/trade, PF **0.618**.

## What this means

The answer to the new research question, under this frozen protocol, is:

**No robust cheap-long-option edge was established.**

The development effect did not survive the first frozen validation test.

Buy Put had some positive post-hoc validation combinations in the full rule grid, but those combinations were not selected from development; their uncertainty intervals crossed zero, and the 22-rule search remained statistically unsupported. They therefore remain hypothesis-generating observations rather than candidates for promotion.

## Cost / time decay handling

The baseline historical cost was:
- 2.0 option points execution stress;
- ₹10 per order;
- two orders;
- lot size 65;
- total = 2.307692 points/trade.

Premium is part of the historical entry cashflow. Terminal intrinsic value is the expiry payoff. Therefore time decay is already embedded in realized P&L and was not double-counted.

## Data limitation

The parent options archive is an EOD close-price reconstruction rather than deployment-grade historical bid/ask replay. The result is a research reconstruction with explicit adverse cost stress, not an executable historical fill study.

## Final decision

**HOLD / NO PROMOTION.**

Next valid evidence requires genuinely new post-exposure observations, fixed rules, and deployment-grade quote history.
