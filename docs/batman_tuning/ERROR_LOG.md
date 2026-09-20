# Error Log

## 2026-09-21

E001: Initial scaffold was prepared as a standalone repository. Correction: the research architecture is now a dedicated branch inside vishnuvcr/Nifty.

E002: First remote bulk-transfer attempt hit a local quoting error before any GitHub write. Correction: transfer is being rebuilt using smaller auditable batches; no branch data were corrupted.

E003: Historical BATMAN backfill artifacts were expected to provide a reusable option dataset. Repository/Actions audit found the backfill runs but no downloadable workflow artifacts; the persisted paper record explicitly lacks historical bid/ask quotes. Correction: do not treat the reconstructed close-price record as executable historical data; add a fail-closed cache contract and validator.

E004: T1 workflow originally only printed a blocker message and did not mechanically validate prerequisites. Correction: workflow now runs scripts/batman_tuning_t1_data_check.py and fails closed when the cache is absent or incomplete.
