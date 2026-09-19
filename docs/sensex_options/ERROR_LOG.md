# SENSEX Options Research Error Log

## 2026-09-20

### E001 — Parent-branch ambiguity
Type: repository/branching
Observation: the default main branch is a lightweight scaffold and does not contain the Phase-10 strategy implementation.
Resolution: the Sensex branch was moved to the Phase-10 Adaptive research branch tip before adding study files.
Prevention: always inspect the branch containing the frozen research implementation before creating transfer experiments.

### E002 — NIFTY strategy code uses NIFTY-specific data contracts
Type: implementation risk
Observation: the current Batman and Adaptive producer code contains NIFTY-specific endpoints, symbols, calendar logic and lot-size defaults.
Resolution: do not simply change a symbol string; create a SENSEX data/contract adapter and test it independently.
Prevention: require an S1 data-contract audit before S3/S4 implementation.

### E003 — Brokerage information can be time/version dependent
Type: market-cost modelling
Observation: Paytm Money public pages contain different historical brokerage figures depending on account vintage/date.
Resolution: store the exact effective-date rule and source used for the study; do not assume one current brokerage number applies to all historical observations.
Prevention: version the execution-cost configuration and log source URLs/dates in DATA_MANIFEST.md.

## Logging rule
Every failed workflow, data-source exception, schema mismatch, unit-test failure, or methodological correction must be appended here with timestamp, phase, symptom, root cause, corrective action, and prevention/control added. Never delete prior entries.