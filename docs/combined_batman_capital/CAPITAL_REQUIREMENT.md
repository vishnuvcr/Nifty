# Combined NIFTY + SENSEX Batman Capital Requirement

## Status
**Completed — provisional research capital-sizing result.**

This branch evaluates one NIFTY Batman strategy-lot and one SENSEX Batman strategy-lot held simultaneously. This is a capital-risk reserve analysis, not a Paytm Money live-margin quote.

## Inputs

### NIFTY Batman
The frozen repository ledger contains a reconstructed 2026-09-17 Batman observation:
- risk points: **780.6186**
- stored lot size: **65**
- stored estimated risk: **₹50,740.21**

The signal producer defines the sizing proxy as max(ES95, ES99) × lot size.

The stored 65-unit lot is obsolete for current NIFTY contract sizing. Normalizing the same risk points to the current 75-unit lot gives:

**780.6186 × 75 = ₹58,546.40 per NIFTY Batman strategy-lot.**

This is one frozen risk snapshot, not a historical maximum.

### SENSEX Batman
From the complete frozen S5 development + validation + holdout population:
- maximum estimated MC-risk proxy: **₹66,970.95 per lot**
- 20% operational buffer: **₹80,365.14 per lot**

## Combined reserve

| Component | MC-risk proxy | +20% buffer |
|---|---:|---:|
| NIFTY Batman | ₹58,546.40 | ₹70,255.68 |
| SENSEX Batman | ₹66,970.95 | ₹80,365.14 |
| **Combined** | **₹125,517.35** | **₹150,620.82** |

For **1 NIFTY Batman lot + 1 SENSEX Batman lot simultaneously**, the current repository-backed research reserve is therefore approximately **₹1.51 lakh**.

For operational simplicity, round this to **₹1.55 lakh minimum research working capital**, before an additional discretionary cash cushion.

## Interpretation and limitations

1. Paytm Money's exact margin is dynamic and must be checked for the exact live baskets.
2. The NIFTY estimate is based on one retained risk observation, not a multi-trade historical maximum.
3. No synchronized NIFTY/SENSEX dependence simulation has yet been run; the combined number is additive.
4. Batman has theoretically unbounded tail loss; MC expected shortfall is a sizing proxy, not a maximum-loss guarantee.
5. Brokerage, statutory charges, slippage and temporary margin expansion require a separate operating buffer.

## Deployment rule

Use:

**required account equity = max(live Paytm Money margin for both baskets, ₹150,621 research reserve) + separate operating cash buffer.**

Capture the live Paytm Money basket-margin snapshot with the signal before deployment.

## Required upgrade before final capital specification

- reconstruct a multi-trade NIFTY Batman risk population;
- normalize lot size by contract date;
- run synchronized cross-index Monte-Carlo/bootstrap with an explicit dependence model;
- capture live Paytm Money basket-margin snapshots;
- stress slippage and transaction costs.
