# Adaptive Regime Paper Trading v1

This is a separate prospective paper-trading system from Batman.

## Research basis

The completed pre-2026 CPCV + block-bootstrap phase found that the regime-conditioned return effect was more reproducible than the exact strategy identity. The operational consequence is a **candidate-set router** rather than a permanently frozen one-strategy-per-regime mapping.

Candidate sets are frozen from the CPCV selection frequencies:

- **LOW volatility:** Risk Reversal, Long Synthetic Future, Buy Call
- **MEDIUM volatility:** Short Straddle, Put Ratio Spread, Short Strangle, Strip, Buy Put
- **HIGH volatility:** Sell Put, Risk Reversal, Long Synthetic Future, Batman

The producer evaluates every candidate available for the current regime using the same Monte Carlo terminal distribution and the same 2-point-per-contract stress cost. A candidate is eligible only when **net MC EV > 0** and the configured risk budget can fund at least one lot.

Among eligible candidates, the primary paper-trade candidate is the one with the highest net MC EV. This primary selection rule is explicitly marked **prospective and unvalidated**; it is not presented as a historical proof.

## Frozen operational rules

- Model data is frozen through the prior completed NIFTY 50 session.
- Entry processing is at 09:30 IST.
- Entry occurs only when the front expiry is exactly 3 future trading sessions away.
- MC uses 5,000 bootstrap paths from the previous 756 daily log returns.
- Risk sizing uses `max(ES95, ES99)` with a 2% paper-account risk budget.
- Stress transaction cost is 2 option points per contract.
- Missing/invalid data produces `NO_TRADE`; values are never imputed.
- The system is paper-only and does not place broker orders.
- Initial benchmark exit is expiry settlement; no discretionary early exit is used.

## Published artifacts

The Adaptive page publishes:

- latest signal JSON
- adaptive signal history CSV
- candidate-screen CSV for every candidate tested on each entry day
- paper-trading ledger CSV
- producer metadata
- the exact research/configuration used by the producer

Batman remains a separate page and uses separate state files and a separate page directory.
