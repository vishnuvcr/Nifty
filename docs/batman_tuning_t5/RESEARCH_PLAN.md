# T5 Robustness and Inference

## Objective
Stress-test the frozen 2025-2026 holdout result without changing the rule.

## Analyses
1. Exact small-sample uncertainty for the mean net P&L and win rate.
2. Bootstrap sensitivity, explicitly treated as exploratory because only seven trades exist.
3. Brokerage sensitivity at ₹10/₹20/₹30 per executed F&O order.
4. Additional adverse-slippage stress.
5. Calendar/year stability.
6. Leave-one-trade-out concentration analysis.
7. Document all data-availability and execution skips.

## No re-selection
The T4 frozen rule remains unchanged:
D3, same-session 09:30, gross MC-EV > 0, trailing target activated at 20% of maximum-profit reference with 10% retracement.

T5 can reject robustness; it cannot modify the frozen rule.
