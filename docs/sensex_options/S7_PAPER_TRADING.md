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
- Live executable proxy: BUY uses ask + 0.50 point slippage; SELL uses bid − 0.50 point slippage.
- Missing option premiums/bid-ask produce a DATA_LIMITED_CANDIDATE decision-time observation with execution_status=NOT_EXECUTABLE; no premium or LTP is invented.
- The live SENSEX quote must carry a parseable timestamp dated the current decision date; stale prior-session quotes remain a hard NO_TRADE/runtime failure and are logged.
- Costs: SENSEX-specific transaction-cost schedule from S2 is deducted.
- Paper only: no broker order is submitted.

## Data provenance

The live adapter uses BSE public index-history/live-quote endpoints and the BSE derivatives-chain surface. The scanner records retrieval timestamps and the exact raw-data schema observed in each run.

The decision-time scanner has two explicit information states: (1) EXECUTABLE_QUOTE_OBSERVATION when the current option bid/ask surface is available, and (2) DATA_LIMITED_CANDIDATE when underlying/past-only model inputs are available but option premiums/bid-ask are unavailable. DATA_LIMITED_CANDIDATE is not an executable trade and is excluded from realized-performance metrics.

## Today's 21-Sep-2026 observation

At the 09:30 IST decision boundary, the verified SENSEX spot used was 74,748.70. Option premiums/bid-ask were unavailable, so Batman and Adaptive were published as DATA_LIMITED_CANDIDATE decision-time observations. Adaptive's primary remained unselected because net MC-EV requires executable option prices. No trade was backfilled and no broker order was attempted.

## Scheduling

- Entry scanner: weekdays 09:30 IST (04:00 UTC), with a manual workflow_dispatch button. After state is pushed to the S7 branch, it requests an immediate combined Pages publication. The production workflow has no 09:40 backfill mode.
- Settlement/page refresh: weekdays 16:00 IST (10:30 UTC), with a manual workflow_dispatch button. This remains the scheduled publication backstop and settles matured paper trades.
- GitHub Pages publication remains a separate publication step; it never creates an additional entry signal.

## Scientific boundary

The first prospective executable observation must be generated prospectively and never backfilled. DATA_LIMITED_CANDIDATE records are decision-time audit observations, not retrospective trades. S7 results must not be mixed into the NIFTY MC-WFO manuscript or retroactively used to select the strategy. The SENSEX study remains a separate cross-index transfer study.
