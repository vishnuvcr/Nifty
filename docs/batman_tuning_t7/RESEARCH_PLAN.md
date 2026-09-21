# BATMAN Tuning T7 — Joint Entry × Timing × Exit WFO

## Research question
Can BATMAN performance be improved when entry day, entry timing and exit family are tuned jointly rather than sequentially?

## Candidate universe

### Entry day
D0 through D6:
- D0 = expiry session.
- D1 = one prior trading session.
- ...
- D6 = six prior trading sessions.

### Entry timing
A. Previous-session evening signal -> next-session market-open execution.
B. Same-session 09:30 signal -> first executable observation strictly after 09:30.

### Exit families
1. Expiry control.
2. Fixed target: 10%, 20%, 30%, 40%, 50%, 60%, 75% of maximum-profit reference.
3. Fixed stop: 10%, 20%, 30%, 40%, 50%, 75%, 100% of MC ES95 loss reference.
4. Trailing target: activation 20/30/40/50% × retracement 10/20/30%.
5. Trailing stop: 10/20/30/40/50% of maximum-profit reference.

Total exit variants = 32.
Total joint configurations = 14 × 32 = 448.

## Frozen BATMAN entry mechanics

- 756 completed NIFTY daily log-return lookback.
- 5,000 Monte Carlo paths.
- Bootstrap-with-replacement daily returns.
- P20/P35/P65/P80 terminal quantiles.
- +1 P35 PE, -2 P20 PE, +1 C65 CE, -2 C80 CE.
- Primary gate: gross MC-EV > 0.
- Two option-premium points adverse slippage per execution leg.
- Four entry orders and four exit orders.
- Historical NIFTY lot size and option-sale STT by execution date.

## Exit mechanics

Maximum-profit reference is the maximum finite strategy payoff over 0 and all selected strike breakpoints.

Initial-risk reference is MC ES95 loss:
negative mean of the worst 5% of simulated MC basket P&L, floored at zero.

Every non-triggered fixed/trailing rule falls back to the expiry control. No trade disappears from the denominator.

Trailing target:
- activate after basket marked P&L reaches activation × maximum-profit reference;
- thereafter exit after the declared retracement from the running peak.

Trailing stop:
- trail the running favorable basket P&L by the declared trailing fraction of maximum-profit reference.

## Joint WFO

Outer test years: 2022, 2023, 2024.

For each outer fold:
1. Use only earlier development years for selection.
2. Candidate must have at least 25 unique training trades.
3. Primary selection score = worst-brokerage mean net P&L per unique trade across ₹10/₹20/₹30 brokerage scenarios.
4. Secondary = worst-brokerage total net P&L.
5. Tertiary = worst-brokerage maximum drawdown, preferring the least-negative value.
6. Quaternary = lower rule complexity.
7. Evaluate the selected full joint configuration on the untouched outer test year.
8. Compare against frozen control: D3 + 09:30 + expiry exit.

After the outer folds, apply the identical selector to all 2020-2024 development data and freeze exactly one joint configuration.

## Holdout
The 2025-2026 holdout is untouched until the final joint configuration is frozen.

## Anti-leakage
No future quote, strike availability, trigger, exit or P&L may enter selection.

## Interpretation
T7 directly answers the original objective. A joint configuration can only be promoted to prospective research if it survives the nested WFO and untouched holdout comparison.

No candidate is selected by looking at the holdout.
