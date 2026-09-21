# T3 Error Log

## 2026-09-21

No T3 workflow runtime error yet.

### E017
The initial T3 implementation used the fixed-stop parameter as the trailing retracement in the combined trailing-target + fixed-stop family. Correction: combined rules now use the dedicated retracement parameter while retaining the fixed-stop parameter independently.

E018
Adverse premium slippage could theoretically drive a very low premium below zero. Correction: sell-side execution premiums are floored at zero after adverse slippage for both entries and exits; a unit test will enforce this.

Any subsequent T3 computation error will be logged before rerun.

E019
The first T3 cost routine charged entry brokerage but omitted the four exit orders from net P&L. The unit test exposed the omission before the exit grid ran. Correction: net P&L now includes 4 entry brokerage orders + 4 exit brokerage orders + STT + slippage.

E020
The T3 unit-test suite passed, but the full script failed in GitHub Actions because the repository's scripts directory is not a Python package and the module import could not resolve. Correction: the T3 script now inserts the repository root into sys.path before importing shared T2 functions.

E021
The T3 cache-stabilization edit introduced malformed YAML: duplicate run keys under one step and a stale cache-step ID. GitHub created a run with no jobs. Correction: duplicate key removed and the obsolete cache-save step removed entirely because T1 is the authoritative cached source.
