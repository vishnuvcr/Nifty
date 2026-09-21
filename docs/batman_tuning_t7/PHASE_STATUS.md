# T7 Phase Status

| Phase | Status |
|---|---|
| T0 | COMPLETE |
| T1 | COMPLETE |
| T2 | COMPLETE |
| T3 | COMPLETE |
| T4 | COMPLETE |
| T5 | COMPLETE |
| T6 | COMPLETE |
| T7 Joint development grid + nested WFO | COMPLETE |
| T7 development freeze | COMPLETE |
| T7 untouched 2025–2026 holdout | IN PROGRESS |

## Frozen development selection

The joint selector has already produced and frozen:

- D4 entry day.
- Same-session 09:30 execution.
- Trailing target: activate at 30% of maximum-profit reference.
- Retracement: 30% of maximum-profit reference.
- Development selection uses the frozen T7 brokerage-stress selector.
- 2025–2026 holdout remains untouched by selection.

## Current gate

The holdout engine is separate from the development engine. It uses the accepted 2025–2026 option archive convention and evaluates the frozen T7 candidate against:

1. Original BATMAN operational control: D3 / 09:30 / expiry.
2. Prior T6 candidate: D3 / 09:30 / trailing 20% activation / 10% retracement.
3. T7 frozen candidate: D4 / 09:30 / trailing 30% activation / 30% retracement.

Primary case: 2-point adverse slippage per option leg and ₹20 brokerage per executed F&O order.

A 4-point slippage stress is also reported descriptively and is not used for selection.

No holdout observation is used to alter or re-select the T7 configuration.
