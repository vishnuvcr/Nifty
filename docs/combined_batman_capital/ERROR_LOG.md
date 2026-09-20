# Combined Batman Capital Analysis — Error Log

## 2026-09-20

### E012 — Historical NIFTY Batman signal retained an obsolete lot size
Type: contract specification / capital sizing

Observation: the frozen NIFTY Batman paper signal records a 65-unit lot.

Resolution: preserve the risk points but normalize INR risk to 75 units for current NIFTY contract sizing: 780.6185953876956 × 75 = ₹58,546.39.

Prevention: validate the exchange contract multiplier for the relevant deployment date before converting points to INR.

### E013 — NIFTY Batman risk population is incomplete
Type: methodology / evidence coverage

Observation: only one frozen NIFTY Batman observation with the required ES sizing fields was available in the inspected repository branch.

Resolution: label the NIFTY result provisional and do not call it a historical maximum.

Prevention: reconstruct and freeze a multi-trade NIFTY Batman risk population across development/validation/holdout periods before final capital specification.
