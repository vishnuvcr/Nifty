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

### E004 — Expiry-calendar source conflict
Type: contract calendar / data integrity
Observation: current SENSEX listings show Thursday expiries, while historical BSE methodology documents record multiple changes in expiry conventions across years. A single weekday rule would be unsafe for a long backtest.
Resolution: S1 will use date-specific contract metadata / actual listed expiry records and treat generalized weekday rules only as a diagnostic cross-check.
Prevention: every option observation must pass an expiry-consistency audit before entering a walk-forward sample.

### E005 — Current brokerage source conflict
Type: transaction-cost modelling
Observation: Paytm Money currently publishes an F&O FAQ with Rs.10 per unique executed order, while older official Paytm Money communications describe Rs.20 for newer accounts and different legacy rates.
Resolution: S2 will use account/effective-date-aware cost scenarios and clearly label the selected base case; no single brokerage number will be assumed for all historical observations.
Prevention: version the cost schedule by effective date and source.