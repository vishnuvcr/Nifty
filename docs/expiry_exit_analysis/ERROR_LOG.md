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


### E007 — Superseded CI runs competing for the same analysis branch
Type: CI orchestration
Observation: rapid corrective commits created multiple queued/overlapping branch analysis runs while the first long historical run was still executing.
Resolution: branch workflow concurrency was changed to cancel superseded runs so only the newest corrected research revision can proceed.
Prevention: use `cancel-in-progress: true` for deterministic single-run historical analyses on a dedicated branch.


### E008 — SENSEX MC history path mismatch in full v2 runner
Type: execution / data-path
Observation: the workflow correctly created `data/expiry_exit/sensex_mc_daily.parquet`, but the v2 runner passed `data_root/"sensex_mc_daily.parquet"` (inside the HF data tree) into the frozen SENSEX backtest. The resulting run failed after approximately 20 minutes with FileNotFoundError.
Resolution: the runner now reads the prepared composite MC history from the authoritative `ROOT/data/expiry_exit/sensex_mc_daily.parquet` path.
Prevention: use one explicit prepared-data contract between workflow and analysis engine; add a preflight file-existence assertion before entering the long SENSEX backtest.


### E009 — SENSEX NO_TRADE rows reached exit JSON parsing
Type: execution / schema handling
Observation: frozen S5 trade CSVs deliberately contain NO_TRADE rows with blank `legs_json`; pandas represented those blanks as NaN, and the early-exit runner attempted `json.loads()` on the NaN value.
Resolution: the runner now skips rows without a string `legs_json` and skips non-CLOSED rows before parsing; malformed JSON is also skipped rather than interpreted as a trade.
Prevention: treat NO_TRADE/status fields as part of the frozen trade schema and validate them before any leg-level repricing.


### E010 — SENSEX early-exit pricer received the raw CSV row instead of decoded legs
Type: execution / function contract
Observation: the runner decoded `legs_json` successfully, but then passed the original pandas Series into `sensex_exit_pnl()`. That function expects an entry object containing a decoded `legs` collection, so every SENSEX early-exit attempt raised a KeyError and was silently skipped. This caused the verification stage to report all four SENSEX 15:00/15:10 scenarios missing even though expiry-settlement results were produced.
Resolution: the decoded legs and entry cashflow are now passed explicitly as the pricer entry object.
Prevention: align caller/callee data contracts and add a test that requires at least one SENSEX early-exit row before allowing the verification stage to pass.
