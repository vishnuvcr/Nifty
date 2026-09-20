# Conversation and Audit Log

## 2026-09-21
User requested a BATMAN tuning study covering D0-D6 entry, prior-session signal to market-open execution, same-session 09:30 signal, fixed target, fixed stop, trailing target, and trailing stop.

The first scaffold was mistakenly created as a standalone local repository.

User corrected the architecture: use a separate branch in https://github.com/vishnuvcr/Nifty.

Correction applied: branch research/batman-tuning-v1 created in vishnuvcr/Nifty, with the promoted BATMAN preserved as the frozen control.

T0 protocol transferred to this branch. No tuning result has been claimed.

### T1 continuation — 2026-09-21
A repository and GitHub Actions audit searched historical BATMAN commits and the prior first-trade backfill. The persisted 2026-09-17 paper record uses NSE UDiFF close prices and explicitly says historical bid/ask were unavailable; backfill diagnostics were committed, but the corresponding workflow runs have no retained downloadable artifacts. This is insufficient for intraday target/stop/trailing analysis.

Engineering response: create an immutable-cache contract plus a fail-closed T1 validator. The study will not infer intraday behavior from settlement/close-only records and will not fabricate tuning results.
