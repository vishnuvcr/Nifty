# Error Log

## 2026-09-21

E001: Initial scaffold was prepared as a standalone repository. Correction: the research architecture is now a dedicated branch inside vishnuvcr/Nifty.

E002: First remote bulk-transfer attempt hit a local quoting error before any GitHub write. Correction: transfer is being rebuilt using smaller auditable batches; no branch data were corrupted.

E003: Historical BATMAN backfill artifacts were expected to provide a reusable option dataset. Repository/Actions audit found the backfill runs but no downloadable workflow artifacts; the persisted paper record explicitly lacks historical bid/ask quotes. Correction: do not treat the reconstructed close-price record as executable historical data; add a fail-closed cache contract and validator.

E004: T1 workflow originally only printed a blocker message and did not mechanically validate prerequisites. Correction: workflow now runs scripts/batman_tuning_t1_data_check.py and fails closed when the cache is absent or incomplete.

E005: A code-generation transfer attempt used an unescaped template delimiter while embedding the T1 acquisition workflow. The error occurred before any repository write. Correction: the workflow and documentation were resent using safe string serialization.

E006: Initial T1 acquisition workflow separated cache restore and cache save with the same fixed key. Correction: use actions/cache in combined restore/save mode so the first successful acquisition can populate the cache and later runs can reuse it without a duplicate-save path.
