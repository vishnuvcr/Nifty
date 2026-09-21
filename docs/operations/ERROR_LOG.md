# Error Log — Paper Trading / Pages Operations

## 2026-09-21 — Controlled 09:40 backfill

### E2026-09-21-01 — NIFTY defined-risk persistence path
**Observed in workflow:** `35581947565`  
**Symptom:** persistence step failed with `fatal: pathspec 'paper_trading/prospective_defined_risk/nifty' did not match any files`.  
**Impact:** the backfill records were created, but the first NIFTY defined-risk workflow did not persist its audit/state successfully.  
**Root cause:** the workflow assumed a ledger directory that does not exist on the frozen defined-risk branch.  
**Correction:** removed the nonexistent ledger path from the `git add` command; retained the actual published `site/prospective-defined-risk/nifty` tree and audit JSON.  
**Verification:** retry workflow `35582069757` completed successfully.

### E2026-09-21-02 — Runtime audit interpolation
**Observed during first backfill attempt:** workflow audit JSON emitted literal `"${MODE}"`, `"${DECISION_DATE}"`, and `"${ENTRY_TIME_IST}"` instead of runtime values.  
**Impact:** audit metadata was not trustworthy for that first attempt.  
**Correction:** changed the shell heredoc fields to use runtime shell variables `$MODE`, `$DECISION_DATE`, and `$ENTRY_TIME_IST`.  
**Verification:** successful retry audits now contain `mode=backfill_0940`, `decision_date=2026-09-21`, and `entry_time_ist=09:40`.

### E2026-09-21-03 — Historical 09:40 executable snapshot unavailable
**Observed in all eight strategy backfill records.**  
**Impact:** an executable 09:40 strategy signal could not be reconstructed without introducing look-ahead or current-quote substitution.  
**Correction:** recorded `BACKFILL_0940_NO_TRADE` for each active strategy, with `historical_snapshot_available=false`, `quote_snapshot_used=false`, and `future_outcome_used=false`.  
**Scientific rationale:** current quotes cannot represent the historical 09:40 executable state.

## Final verification
- Common orchestrator retry: `35582059262` — success.
- NIFTY Batman + Adaptive: `35582069744` — success.
- SENSEX Batman + Adaptive: `35582069804` — success.
- NIFTY defined-risk: `35582069757` — success.
- SENSEX defined-risk: `35582069753` — success.
- Final combined Pages publication: `35582136269` — success.
