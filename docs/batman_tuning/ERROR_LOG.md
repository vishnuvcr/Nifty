# Error Log

## 2026-09-21

E001: Initial scaffold was prepared as a standalone repository. Correction: the research architecture is now a dedicated branch inside vishnuvcr/Nifty.

E002: First remote bulk-transfer attempt hit a local quoting error before any GitHub write. Correction: transfer is being rebuilt using smaller auditable batches; no branch data were corrupted.

E003: Historical BATMAN backfill artifacts were expected to provide a reusable option dataset. Repository/Actions audit found the backfill runs but no downloadable workflow artifacts; the persisted paper record explicitly lacks historical bid/ask quotes. Correction: do not treat the reconstructed close-price record as executable historical data; add a fail-closed cache contract and validator.

E004: T1 workflow originally only printed a blocker message and did not mechanically validate prerequisites. Correction: workflow now runs scripts/batman_tuning_t1_data_check.py and fails closed when the cache is absent or incomplete.

E005: A code-generation transfer attempt used an unescaped template delimiter while embedding the T1 acquisition workflow. The error occurred before any repository write. Correction: the workflow and documentation were resent using safe string serialization.

E006: Initial T1 acquisition workflow separated cache restore and cache save with the same fixed key. Correction: use a persistent raw-source cache and an explicit cache-save step before validation so source acquisition survives downstream test failures.

E007: T1 acquisition run 35537467726 successfully downloaded all four raw archives and generated their SHA-256 manifest, but the validation step failed because pytest was not installed. The cache-save and manifest-upload steps were also skipped by the failure. Correction: install pytest and save the raw cache before validation; publish the manifest even when validation fails.

E008: Run 35537505911 repeated the same missing-pytest defect because the correction had not yet been committed. Correction: installed pytest and added explicit cache persistence in run 35537798592.

E009: The first transfer of the raw-source schema-audit script failed in the connector before repository write because one sequential lookup returned no object. Correction: repository state was checked and the audit script was then created separately; no partial source-audit file was left behind.

E010: Deep raw-data probe run 35538086620 failed because the Zenodo option archive nests ZIPs across multiple levels; the probe attempted to parse a nested ZIP as CSV. Correction: the probe now recursively descends ZIP layers until a CSV member is found. Raw archives remain intact.
