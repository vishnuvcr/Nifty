# Combined Batman Capital Analysis — Research Plan

## Research question
What account-equity reserve is required to carry one NIFTY Batman strategy-lot and one SENSEX Batman strategy-lot simultaneously, after accounting for model-based tail-risk proxies, operational buffer, contract-size changes, execution costs and broker-margin uncertainty?

## Planned phases

1. **Repository audit**
   - Read the prior expiry-exit capital-sizing result and error log.
   - Identify frozen NIFTY and SENSEX Batman risk fields.
2. **Risk-population recovery**
   - Recover the most complete available NIFTY Batman risk population.
   - Use the complete frozen SENSEX S5 population.
3. **Contract normalization**
   - Validate NIFTY/SENSEX contract multipliers for the relevant trade dates.
   - Never multiply historical risk by an obsolete current lot size.
4. **Marginal capital calculation**
   - Calculate ES-based research risk per strategy-lot.
   - Apply the established 20% operational buffer.
5. **Simultaneous portfolio calculation**
   - Combine the two marginal reserves.
   - Explicitly distinguish additive reserve from a joint dependence simulation.
6. **Broker/execution layer**
   - Define the Paytm Money live-margin capture requirement.
   - Include slippage, brokerage and statutory charges as separate operating-buffer items.
7. **Finalization**
   - Replace provisional NIFTY sizing with a frozen multi-trade distribution.
   - Run synchronized cross-index stress testing.
   - Publish the final capital specification and limitations.

## Stopping rule
Do not claim a final live-account capital requirement until the finalization gate is satisfied. The current branch stops at a clearly labelled provisional research reserve.
