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

### E009 — GitHub Actions execution not exposed through connected runtime
Type: execution environment
Observation: the S5 dispatcher and workflow definitions are present, but neither push-triggered nor pull_request-triggered runs are exposed through the connected GitHub Actions endpoints in this session; no RUN_STARTED checkpoint or report artifacts appeared on the S5 branch.
Resolution: do not report numerical backtest results. Preserve the frozen engine, workflow, split definitions and cost model so the run can be executed from GitHub Actions without methodological changes.
Prevention: treat a missing CI run as an infrastructure failure, never as a zero-trade or zero-performance backtest result.


### E010 — ₹100k risk gate produced zero deployable lots despite valid strategy observations
Type: methodology interpretation / reporting
Observation: with a ₹100,000 account and 2% risk budget, the frozen risk-sizing gate returned zero lots for the evaluated SENSEX structures because one-lot ES95/ES99 risk often exceeded ₹2,000.
Resolution: retain the frozen gate for Adaptive execution results, but separately report forced one-lot realized expiry P&L for every successfully priced candidate. This prevents conflating “not deployable at the chosen account size” with “strategy has no historical outcome.” The realized column is strictly post-entry evaluation and cannot affect selection.


### E010 — Yahoo Finance HTTP 429 in S5 CI
Type: external data acquisition
Observation: S5 run 35472613682 failed at the independent Yahoo daily SENSEX-history fetch with HTTP 429 before the option backtest began.
Resolution: removed the runtime Yahoo dependency from the S5 workflow. The frozen engine now requires the cached/primary SENSEX index dataset already used by the option dataset.
Prevention: no live third-party API is allowed in the historical backtest path; data must be cached/pinned before execution.


### E011 — Stale Yahoo MC argument remained after E010
Type: workflow/code integration
Observation: the first E010 retry removed the Yahoo download step but the branch workflow still passed `--mc-index-path data/external/sensex_daily_yahoo.parquet`, causing FileNotFoundError after the SENSEX option dataset downloaded successfully.
Resolution: removed the stale argument; the engine falls back to the cached primary SENSEX index series for the past-only MC return history.
Prevention: after removing an external dependency, search both workflow and code for all references before rerun.


### E012 — Git LFS public clone acquisition failed in S5
Type: external dataset acquisition
Observation: after E010/E011, the branch workflow failed during the Git/LFS sparse acquisition of the public SENSEX dataset before the backtest began (exit 128).
Resolution: replaced Git/LFS acquisition with the Hugging Face Hub `snapshot_download` client and explicit file existence validation.
Prevention: prefer the dataset provider's supported download API over an unauthenticated Git/LFS clone in CI.


### E013 — SENSEX engine imported package from wrong module path
Type: Python package integration
Observation: CI successfully downloaded all 149 SENSEX files, then development failed with `ModuleNotFoundError: nifty_mc` because the strategy catalog is under `src/nifty_mc` and the workflow intentionally did not install the project editable.
Resolution: changed the engine import to `src.nifty_mc.strategy_catalog`, matching the repository layout.
Prevention: run the exact CI command in the repository environment before workflow execution and validate package imports.


### E014 — `src` is not a Python package namespace in CI
Type: Python path integration
Observation: changing the import to `src.nifty_mc` still failed because `src` is a source-layout directory, not an import package.
Resolution: prepend repository `src/` to `sys.path` and import `nifty_mc.strategy_catalog` directly.
Prevention: validate source-layout imports using the exact non-editable CI environment.


### E011 — Result extraction filtered standalone Batman incorrectly
Type: backtest reporting bug
Observation: standalone Batman rows were recorded as STANDALONE_EVALUATED, while the realized-trade extractor accepted only EVALUATED, producing zero standalone Batman trades in the headline result even though the underlying candidate evaluation completed.
Resolution: extractor now accepts both EVALUATED and STANDALONE_EVALUATED statuses; the workflow prints candidate/status counts before publication.
Prevention: add regression coverage for standalone strategy extraction and require consistency between evaluated candidate rows and realized summaries.

### E012 — S5 publication branch race
Type: CI publication
Observation: the backtest job successfully produced all three split outputs, but the final git push was rejected because the run-start checkpoint had advanced the remote branch.
Resolution: publication now fetches and rebases onto the current remote phase branch before pushing results.
Prevention: all workflow jobs that self-commit state must rebase against the remote branch before publication.


### E013 — SENSEX affordability gate suppresses all trades at the copied NIFTY paper-capital scale
Type: transferability / risk sizing
Observation: with ₹100,000 paper capital and a 2% risk budget, every evaluated SENSEX candidate required more than ₹2,000 estimated ES risk per lot, so the original operational affordability gate yielded zero trades despite positive MC-EV observations.
Resolution: run a separate pre-registered one-lot transfer-edge analysis using the unchanged MC-EV gate, while retaining the original affordability result as a separate operational diagnostic. One-lot P&L is capital-independent and therefore avoids arbitrary account-size selection.
Prevention: never conflate instrument-transfer edge evidence with a particular account-capital sizing constraint.


### E015 — S6 workflow adds explicit one-lot edge sensitivity
Type: methodology extension
Observation: the ₹1 lakh account-level gate produced zero actual trades because estimated ES risk per SENSEX lot often exceeded the ₹2,000 risk budget. That is a capital-sizing result, not evidence that the strategy has zero per-lot edge.
Resolution: S6 evaluates the frozen strategy rules on exactly one lot when net MC EV > 0, across 0.25/0.50/1.00/2.00 slippage. These results are reported separately from account-sized trading and are not used to alter the frozen strategy selection rules.
Prevention: distinguish strategy edge from account-affordability in all SENSEX conclusions.
\n\n### E016 — Initial S6 robustness workflow was incomplete
Type: robustness/statistical inference
Observation: the first S6 workflow only varied slippage, re-downloaded the same historical dataset on each run, and did not quantify Monte Carlo seed instability or dependence-aware uncertainty.
Resolution: S6 workflow now uses persistent GitHub Actions caching for the source dataset, runs a predeclared five-seed OOS sensitivity at fixed base slippage, and calculates a circular moving-block bootstrap over validation + holdout closed trades.
Prevention: every robustness phase must include execution-cost sensitivity, model/random-seed sensitivity where stochastic components exist, and dependence-aware uncertainty before a performance conclusion is finalized.


### E016 — Available SENSEX dataset does not support the full planned chronological sample
Type: data coverage
Observation: the frozen 756-session lookback makes 2024 development observations unavailable; usable validation begins 2025-10-09 and the available holdout ends 2026-05-21.
Resolution: do not impute missing history or relabel no-data periods as strategy losses. Report the observed windows explicitly and keep the phase complete only for the available sample.
Prevention: future replication must acquire a longer exchange-verified SENSEX history before interpreting multi-year walk-forward stability.
\n\n### E017 — S6 dataset-fetch heredoc indentation error
Type: CI execution
Observation: the first corrected S6 workflow failed before downloading data because the shell heredoc terminator was indented, producing a bash syntax error.
Resolution: rewrote the embedded Python block with a column-zero heredoc terminator in the rendered shell script.
Prevention: validate YAML block scalar rendering for embedded heredocs before triggering a long workflow.
\n\n### E018 — First S6 heredoc correction did not alter rendered workflow
Type: CI execution / correction control
Observation: the first attempted heredoc correction did not change the rendered YAML because the content replacement failed to match; the next run repeated E017.
Resolution: removed the embedded heredoc entirely and replaced it with a single-line Python invocation.
Prevention: after each CI syntax correction, re-fetch the committed workflow text and verify the exact rendered shell block before relying on the rerun.
\n\n### E019 — S6 robustness summary rejected valid zero-trade CSV
Type: statistical reporting / data-shape handling
Observation: some Monte Carlo seed scenarios legitimately produced no closed trades for a strategy, and the backtest wrote an empty CSV. The S6 summary parser treated that as a malformed file and stopped the robustness phase.
Resolution: empty trade CSVs are now treated as valid zero-trade outputs and skipped in concatenation; the scenario-level JSON summary remains the authoritative zero-trade record.
Prevention: reporting code must distinguish valid empty result sets from corrupt files, with zero-trade cases explicitly represented in scenario summaries.
\n\n### E020 — S6 used a different MC history input than the completed S5 baseline
Type: methodology / provenance
Observation: the initial S6 implementation passed the raw 1-minute SENSEX index parquet directly as the Monte Carlo/regime history. The completed S5 transfer run used an independently constructed daily history combining cached pre-2024 SENSEX warmup data with the daily closes from the primary SENSEX index parquet.
Resolution: S6 now reproduces the S5 composite daily MC history exactly, passes it through --mc-index-path for every slippage and seed scenario, and adds an explicit S5 baseline reproduction gate before sensitivity results are interpreted.
Prevention: robustness phases must reuse the exact validated baseline data-engine contract and include an automated reproducibility checksum before alternative scenarios are accepted.
\n\n### E021 — S6 report publication failed on add/add rebase conflicts
Type: CI publication
Observation: numerical S6 analysis completed, but publication failed because generated report files existed on the remote branch and the workflow attempted to rebase a new report commit onto them, creating add/add conflicts.
Resolution: publication now snapshots the current run's reports outside the repository, hard-resets to the current remote branch tip, restores only the current run's S6 reports, commits, and pushes.
Prevention: generated-report publication must be conflict-safe and must treat the current successful run's reports as authoritative only after all numerical gates pass.


### E022 — S7 scanner source-layout import
Type: Python package integration
Observation: the first S7 scanner draft imported src.nifty_mc directly even though src is a source-layout directory rather than a Python package namespace in CI.
Resolution: S7 now prepends the repository src/ directory to sys.path and imports nifty_mc.strategy_catalog, matching the validated S5/S6 pattern.
Prevention: reuse the repository's proven source-layout import convention in all new workflows.

### E023 — S7 expiry shortcut needed trading-session semantics
Type: methodology / calendar handling
Observation: the initial prospective scanner used a generic future-weekday helper without documenting that the frozen protocol means exactly three future SENSEX trading sessions before the target expiry.
Resolution: target expiry is now derived from future weekday positions and must still be confirmed by the actual BSE option-chain response for that date; missing listed expiry produces NO_TRADE.
Prevention: never synthesize an expiry contract solely from a calendar rule; require listed-contract confirmation before signal generation.

### E024 — S7 workflow authoring template collision
Type: CI authoring
Observation: an intermediate workflow-generation attempt collided with GitHub Actions expression syntax inside the authoring template before any repository write occurred.
Resolution: escaped the Actions expression syntax and re-created the workflows; no malformed workflow was committed.
Prevention: validate generated YAML strings before calling repository write operations.

### E025 — SENSEX Pages parent selector missing from initial S7 state
Type: Pages publication
Observation: the S7 refresh script creates the SENSEX parent selector dynamically, while the first static mirror did not contain site/sensex/index.html.
Resolution: added an explicit SENSEX selector file to the S7 branch and mirrored it to the NIFTY Pages source branch.
Prevention: all published navigation parents must exist as committed static state as well as being reproducible by refresh scripts.
