# T7 Audit Log

## 2026-09-21 — holdout execution phase

The T7 development configuration was already frozen before this holdout step:

- D4
- same-session 09:30
- trailing target
- 30% activation / 30% retracement

A branch audit found that the development engine correctly stops at 2020–2024 but did not itself contain the 2025–2026 holdout implementation.

The correction is deliberately isolated from the frozen selector:
- no development parameters changed;
- no holdout result is used to re-select the candidate;
- a separate holdout workflow uses the accepted 2025–2026 option source convention;
- the holdout comparison includes the original D3/09:30/expiry control, the prior D3/09:30 trailing 20%/10% candidate, and the frozen T7 D4/09:30 trailing 30%/30% candidate;
- 2-point slippage per option leg is primary, with 4-point slippage as a descriptive stress;
- all costs include historical lot size, option-sale STT, and eight brokerage charges per round trip.

No final superiority claim is made until the untouched holdout outputs pass verification.
