# T2 Error Log

## 2026-09-21

No T2 engine execution error has been observed yet.

### Inherited T1 engineering corrections
The T1 phase resolved acquisition, cache persistence, nested archive probing, source selection, and missing-test-environment failures. The full T1 error history remains in docs/batman_tuning/ERROR_LOG.md.

Any T2 computation failure will be logged here before correction and rerun.

E011: The first T2 engine used a net-cost-adjusted MC-EV gate. The promoted parent BATMAN rule uses gross MC-EV > 0. Correction: gross MC-EV > 0 is the primary gate; net-cost gating is sensitivity only.

E012: The first T2 report treated the D3/09:30 operational control as identical to the promoted historical control. Repository inspection showed the parent acquisition pipeline uses daily NSE F&O bhavcopy snapshots, while T2 uses minute-level Ayush option/spot data. Correction: report a parent-style EOD benchmark and an operational intraday control separately.
