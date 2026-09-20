# Expiry-Day Exit Analysis Error Log

## Logging rule

Every workflow failure, parser/schema mismatch, missing market observation, or methodological correction is recorded here with the correction and prevention control.

## 2026-09-20

### E001 — Local GitHub execution unavailable
Type: execution environment
Observation: the container could not resolve github.com, so a local checkout could not be used to run the historical dataset workflow.
Resolution: the analysis was moved to GitHub Actions on the repository branch, where the dataset and report artifacts are reproducible.
Prevention: use repository CI for data-heavy historical reruns when local network access is unavailable.

### E002 — Historical exit must not use future information
Type: methodology
Observation: using a 15:00 bar close would incorporate prices after the 15:00 decision instant.
Resolution: the analysis uses the exact 15:00 and 15:10 one-minute bar OPEN as the exit proxy.
Prevention: no exit scenario may use a bar close for the same timestamp when the intended execution is at the beginning of that minute.

### E003 — Analysis branch/dispatcher separation
Type: repository/CI architecture
Observation: the data-heavy analysis was initially treated as if a separate dispatcher were required for the branch.
Resolution: repository inspection confirmed that the research branch itself contains a push-triggered expiry-analysis workflow plus workflow_dispatch. The execution path is therefore kept on the research branch; no numerical result is claimed until it completes.
Prevention: verify trigger definitions on the actual target ref before documenting an execution architecture.

### E004 — Connected GitHub Actions dispatch unavailable
Type: execution infrastructure
Observation: the connected GitHub toolset does not expose a direct workflow_dispatch call. Earlier notes repeated the same limitation.
Resolution: no fabricated result was produced. The current run uses the verified branch push trigger instead.
Prevention: when workflow_dispatch is unavailable through the connector, use a push-triggered workflow that is already present in the research branch, provided its path filters and CI-side skip controls prevent recursion.

### E005 — Incorrect execution-path description in prior log
Type: repository-state verification
Observation: a prior continuation note said that the authoritative dispatcher lived on main. Repository inspection showed that the expiry-analysis workflow is present on research/expiry-auction-exit-analysis-v1 and its current trigger includes both push and workflow_dispatch; the main branch does not contain that workflow at the inspected path.
Resolution: corrected PHASE_STATUS, CONVERSATION_LOG, and this error log; execution is being initiated by a controlled branch push.
Prevention: always re-read the target branch and main branch workflow files before stating where an analysis dispatcher resides.


### E006 — CI import-path failure in v2 SENSEX path
Type: execution / packaging
Observation: the first full branch rerun reached the analysis stage and ran the NIFTY portion, then failed in `run_sensex()` with `ModuleNotFoundError: No module named 'scripts'` because the script was invoked as `python scripts/expiry_auction_exit_analysis_v2.py`, which places the scripts directory rather than the repository root first on `sys.path`.
Resolution: the v2 engine now explicitly inserts the repository root and `src` into `sys.path`, supporting both script-path and module execution.
Prevention: keep research runners importable under both supported invocation styles and test the SENSEX import path in CI before the long historical run.
