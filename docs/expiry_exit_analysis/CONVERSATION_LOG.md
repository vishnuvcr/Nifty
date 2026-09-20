# Expiry-Day Exit Analysis Conversation Log

## 2026-09-20

### User instruction
Re-run the Batman and Adaptive strategy numbers for both NIFTY and SENSEX using expiry-day exits at approximately 3:00–3:10 pm instead of holding to expiry settlement.

### Research decisions
- Dedicated branch: research/expiry-auction-exit-analysis-v1.
- Frozen entry logic is not changed by the exit study.
- Three exit scenarios are compared: expiry settlement, 15:00 IST and 15:10 IST.
- Exact 1-minute bar OPEN is used for 15:00/15:10 to avoid same-minute look-ahead.
- The analysis uses the cached/public 1-minute options dataset for direct intraday exit marks and a pinned NIFTY daily-history warmup source.
- One-lot/one-strategy-unit edge realization is used to isolate the effect of the exit rule from account-sizing constraints.
- Results are not interpreted until the workflow publishes verified trade-level outputs.

### Corrections recorded
- The first analysis engine draft loaded only SENSEX entry-day rows, preventing expiry-day exit marks; this was corrected to load the full expiry file for 15:00/15:10 re-pricing.
- The first CI draft lacked a reliable source-layout import path; the engine and workflow were corrected to install/use the repository package.


### 2026-09-20 — Expiry-day early-exit rerun
User requested a separate-branch rerun of frozen NIFTY and SENSEX Batman and Adaptive results using expiry-day exits at 15:00 IST and 15:10 IST, retaining expiry settlement as the baseline. The research branch, protocol, analysis engine and CI path are created. Numerical results are not yet claimed because the connected GitHub session cannot invoke workflow_dispatch and the initial PR execution path was blocked. The phase tracker records this execution block explicitly.
