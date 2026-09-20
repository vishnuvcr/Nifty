# Expiry-Day Exit Analysis V2 — Error Log

## Logging rule

Every workflow failure, data-source problem, schema mismatch, timing issue, or methodological correction is recorded here.

## 2026-09-20

### E001 — First-pass workflow was inefficient
Type: execution design
Observation: the first branch reran all three exit scenarios independently, rereading each option-expiry parquet file multiple times.
Resolution: V2 uses a single expiry pass for NIFTY and reuses the SENSEX validated backtest selector while pricing both early exits from the same frozen trade set.
Prevention: exit-sensitivity reruns must share the same entry evaluation and option file load whenever possible.

### E002 — Timestamp timezone normalization
Type: market-data alignment
Observation: stripping timezone information without conversion could shift 09:30 and 15:00/15:10 observations when source timestamps are timezone-aware.
Resolution: V2 converts timezone-aware timestamps to Asia/Kolkata before removing timezone metadata.
Prevention: all execution timestamps are normalized to IST before exact-minute filtering.

### E003 — SENSEX MC provenance
Type: methodology / reproducibility
Observation: the raw 1-minute SENSEX index archive is not the same MC/regime history used by validated S5/S6.
Resolution: V2 explicitly rebuilds and passes the S5 composite daily SENSEX history to the frozen SENSEX backtest engine.
Prevention: exit sensitivity must keep the validated entry-history data contract unchanged.
