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

### E006 — BSE EOD BhavCopy is not executable-quote data
Type: data-source limitation
Observation: BSE's published equity-derivatives Bhav Copy format contains open/high/low/close/WAP, volume and OI fields but not historical best bid/ask snapshots. That is insufficient by itself to reproduce a 09:30 executable entry.
Resolution: S1 will distinguish an executable intraday dataset from an EOD-only proxy dataset. The primary trading inference requires point-in-time executable quotes; an EOD-only run, if used, must be labelled a proxy analysis and cannot be presented as an executable backtest.
Prevention: quote_source and quote_quality are mandatory fields in the SENSEX research dataset.

### E007 — Current exchange web pages do not establish an archived 09:30 quote history
Type: data availability
Observation: BSE's live derivatives chain exposes bid/ask fields, but public EOD BhavCopy documentation does not contain a historical quote-book snapshot at the decision timestamp.
Resolution: require a point-in-time historical quote dataset for executable backtesting, and keep EOD-only analysis clearly separated as a proxy.
Prevention: block S5 execution-style inference until quote provenance passes S1 validation.

### E008 — Historical executable quote limitation retained as a proxy boundary
Type: execution-data limitation
Observation: the open SENSEX 1-minute dataset provides OHLCV/OI but not historical bid/ask.
Resolution: freeze 09:30-bar-open execution plus explicit adverse slippage as the backtest proxy. Do not label results as bid/ask-executable performance.
Prevention: every reported result must carry the quote-proxy label and slippage sensitivity.