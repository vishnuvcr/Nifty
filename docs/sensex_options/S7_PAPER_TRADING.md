# SENSEX S7 — Prospective Paper Trading

## Scope

S7 is a prospective paper-trading implementation of the frozen SENSEX Batman and Adaptive specifications from S0–S6. It is a new observation stream and does not reopen or modify the historical S5/S6 holdout.

## Frozen execution rules

- Decision time: 09:30 IST on BSE trading weekdays.
- Target expiry: exactly the third future weekday after the decision date, and only if that expiry is actually listed in the live BSE option-chain data.
- Monte Carlo: 5,000 bootstrap terminal paths from the last 756 completed daily log returns.
- Regime: past-only 20-day realized volatility ranked over the prior 252 observations.
- Batman: frozen P20/P35/P65/P80 strike mapping and net-MC-EV gate.
- Adaptive: frozen regime-conditioned candidate set; primary = highest net MC EV among eligible candidates.
- SENSEX transfer-edge sizing: exactly one lot when the frozen net-MC-EV gate passes. The previously tested ₹1 lakh / 2% affordability gate remains a separate research boundary and is not reintroduced silently.
- Live executable proxy: BUY uses ask + 0.50 point slippage; SELL uses bid − 0.50 point slippage. Missing bid/ask is a hard NO_TRADE.
- The live SENSEX quote must carry a parseable timestamp dated the current decision date; stale prior-session quotes are a hard NO_TRADE.
- Costs: SENSEX-specific transaction-cost schedule from S2 is deducted.
- Paper only: no broker order is submitted.

## Data provenance

The live adapter uses BSE public index-history/live-quote endpoints and the BSE derivatives-chain surface. BSE documentation exposes historical index OHLC through the ProduceCSVForDate endpoint and the live SENSEX endpoint; the derivatives page publishes bid/ask fields. The scanner records retrieval timestamps and the exact raw-data schema observed in each run. Any endpoint/schema change is a logged error and produces NO_TRADE rather than a fallback to unverified quotes.

## Scheduling

- Entry scanner: weekdays 09:30 IST (04:00 UTC), with a manual workflow_dispatch button. After state is pushed to the S7 branch, it requests an immediate combined Pages publication.
- Settlement/page refresh: weekdays 16:00 IST (10:30 UTC), with a manual workflow_dispatch button. This remains the scheduled publication backstop and settles matured paper trades.
- GitHub Pages publication remains a separate publication step; it never creates an additional entry signal.

## Scientific boundary

The first prospective observation must be generated prospectively and never backfilled. S7 results must not be mixed into the NIFTY MC-WFO manuscript or retroactively used to select the strategy. The SENSEX study remains a separate cross-index transfer study.
