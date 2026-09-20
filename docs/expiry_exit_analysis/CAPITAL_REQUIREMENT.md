# Initial Capital Requirement — Expiry Exit Strategies

## Status
Completed as a **research capital-sizing estimate**. This is not a broker quote.

## Broker facts
Paytm Money states that overnight F&O positions require the prescribed exchange margin and that its Margin Calculator/order window gives the current required margin. Hedged positions receive margin benefits. Therefore a historical backtest cannot by itself establish the exact live broker margin for every future option chain.

## Research sizing model
For the frozen SENSEX S5 trade population, the existing research engine defines `estimated_risk_inr_per_lot` as the larger of the 95% and 99% Monte-Carlo expected-shortfall estimates multiplied by the one-lot size. This is a conservative capital-risk proxy, not the broker's SPAN/exposure margin.

### SENSEX
Across the complete frozen S5 development + validation + holdout populations:
- Batman maximum estimated risk per lot: **₹66,970.95**
- Batman 95th-percentile estimated risk: **₹59,578.50**
- Adaptive maximum estimated risk per lot: **₹89,576.67**
- Adaptive 95th-percentile estimated risk: **₹85,047.81**

Because the router can select either strategy, a single-account capital reserve should be based on the larger selected-strategy requirement rather than adding both strategies.

### Practical reserve
Using a 20% operational buffer above the historical maximum MC risk proxy:
- SENSEX Batman: **₹80,365 per lot**
- SENSEX Adaptive: **₹107,492 per lot**
- If one account can trade either strategy: **₹107,500 per active lot-equivalent** is the research reserve.

A further cash buffer for brokerage, statutory charges, slippage and temporary margin expansion is recommended; it is not included in the ₹107,500 figure.

## Important limitation
This is **not yet the exact Paytm Money initial margin**. Paytm Money states that overnight F&O margin is higher than intraday margin and that the required amount varies with the script/position; its calculator should be checked for the actual live basket. The final live-capital implementation therefore needs a broker-margin snapshot for the exact four legs immediately before deployment.

## NIFTY
The expiry-exit branch does not contain the frozen NIFTY risk-sizing CSV with the `estimated_risk_inr_per_lot` field. It would be scientifically incorrect to manufacture a NIFTY capital number from the P&L drawdown. NIFTY capital must be calculated from its frozen trade/MC risk population using the same procedure before live deployment.

## Decision rule
Until the NIFTY margin/risk file is restored and the live Paytm Money basket is checked:
1. Do not size from historical P&L drawdown.
2. Do not treat the broker's minimum margin as a safe account balance.
3. Use the larger of broker basket margin and the research MC-risk reserve, plus an operational cash buffer.
4. Recheck margin after each lot-size or exchange-margin change.
