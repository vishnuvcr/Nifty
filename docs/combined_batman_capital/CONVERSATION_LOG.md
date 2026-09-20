# Combined Batman Capital Analysis — Conversation Log

## 2026-09-20

### User request
Assess the capital requirement if NIFTY Batman and SENSEX Batman are traded simultaneously.

### Actions
- Audited the prior expiry-exit capital-sizing work and repository phase/error records.
- Inspected the NIFTY Batman signal producer and frozen paper-trading ledger.
- Recovered one NIFTY risk observation containing ES-based sizing fields.
- Validated that its stored 65-unit lot is obsolete for current NIFTY contract sizing and normalized the risk points to 75 units.
- Reused the frozen SENSEX S5 Batman maximum risk proxy.

### Result
- NIFTY Batman: ₹58,546.40 provisional risk proxy per strategy-lot.
- SENSEX Batman: ₹66,970.95 maximum frozen risk proxy per lot.
- Combined: ₹125,517.35.
- With 20% operating buffer: ₹150,620.82.
- Rounded research working minimum: ~₹1.55 lakh.

### Qualification
The NIFTY figure is not a historical maximum because only one suitable frozen risk observation was available. The combined result is additive and does not replace synchronized cross-index Monte-Carlo/dependence analysis or a live Paytm Money basket-margin check.
