# Limited-Risk Option WFO — Error Log

## Logging rule

Every workflow failure, schema mismatch, methodological correction, data-quality issue, reproducibility issue, or repository-state mistake must be recorded here with:
- date/time;
- phase;
- observation;
- impact;
- resolution;
- prevention control.

No error is deleted; corrections are appended.

## 2026-09-20

### LRW001 — Manual risk labels are not sufficient as the authoritative classifier
Phase: L0

Observation: The parent branch contains a manually maintained DEFINED_RISK set in scripts/run_candidate_screen.py.

Impact: A manually curated list can become stale if a strategy definition changes, and it does not itself prove finite maximum loss for a particular strike/premium configuration.

Resolution: This branch requires a mechanical payoff/tail risk-audit engine in L3. The manual list is treated only as a starting universe.

Prevention: Never promote a strategy to the limited-risk universe without a mechanical maximum-loss audit.

### LRW002 — Non-deterministic bootstrap seed construction exists in inherited candidate screen
Phase: L0

Observation: The parent run_candidate_screen.py constructs one bootstrap seed using Python's process-randomized hash(strategy).

Impact: Identical code can produce different bootstrap random streams across Python processes.

Resolution: This branch requires deterministic seeds derived from a stable encoding, for example CRC32 or SHA-derived integers, for every statistical resampling task.

Prevention: Add a unit test asserting identical seeds and identical bootstrap outputs across repeated runs.

### LRW003 — Prior 2026 holdout is already exposed
Phase: L0

Observation: Existing NIFTY MC-WFO results have already reported performance on 2026 observations.

Impact: Those observations cannot serve as a clean final test set for a newly designed limited-risk strategy.

Resolution: L8 is defined around a fresh post-exposure holdout only. If no clean data exist, the phase status must remain HOLD rather than recycling the exposed period.

Prevention: Maintain an explicit exposure map and frozen data boundary.

### LRW004 — Broker margin cannot be inferred from historical P&L
Phase: L0

Observation: Prior research correctly distinguished historical risk estimates from current Paytm Money basket margin.

Impact: Using historical P&L as broker margin would misstate required capital.

Resolution: L9 requires a current broker/exchange margin snapshot for any deployment-oriented capital statement.

Prevention: Archive the broker margin and charges source alongside the final paper-trading specification.

### LRW005 — Existing strategy catalog mixes finite-risk and unbounded-risk structures
Phase: L0

Observation: src/nifty_mc/strategy_catalog.py contains both defined-risk candidates and structures with unbounded adverse tails.

Impact: An all-strategy aggregate can create misleading comparisons if risk classes are not separated.

Resolution: Keep the existing catalog intact, but build a separate mechanical eligibility layer in L3.

Prevention: All outputs must include risk_class and risk_audit_status.

### LRW006 — Multi-expiry calendars cannot be evaluated with a single-expiry terminal payoff
Phase: L0

Observation: The catalog includes Long Calendar strategies using front and next expiries.

Impact: A one-price-at-expiry payoff calculation is insufficient to represent early-exit/calendar value.

Resolution: Treat calendars as a separate path-/expiry-dependent sub-study in L3/L4. They cannot be mixed into single-expiry terminal-payoff statistics without an explicit valuation model.

Prevention: Require an expiry-count/data-contract check before a calendar strategy can enter the core comparison.

## LRW007 — Workflow planning failure
Phase: L2-L7 CI
Observation: first limited-risk workflow run 35496468303 completed with failure and zero jobs.
Resolution: workflow simplified to a single static job with read-only permissions and without in-job repository mutation/status commits.
Prevention: keep research workflows execution-only; update phase logs in separate commits after successful results.

## LRW008 — Initial strategy taxonomy was incomplete
Phase: L3
Observation: The initial written taxonomy omitted Double Plateau and treated Put Ratio Back Spread as an unlimited-profit family without stating the non-negative underlying-domain convention.
Impact: The written plan could have excluded an eligible finite-loss strategy and mischaracterized the profit bound of a put-only ratio backspread.
Resolution: The mechanical auditor is authoritative. The written taxonomy now classifies Put Ratio Back Spread and Double Plateau as R2 for the S >= 0 single-expiry core.
Prevention: Risk-classification tables must be generated from the executable auditor rather than manually maintained lists.

## LRW009 — Overlapping historical CI runs
Phase: L2-L7 CI
Observation: successive protocol/data corrections triggered multiple concurrent limited-risk workflow runs.
Resolution: added workflow concurrency with cancel-in-progress so only the newest research revision can execute the historical analysis.
Prevention: all long historical research workflows use a single branch-level concurrency group.

## LRW010 — Finite-risk definition corrected for index-domain mathematics
Phase: L3
Observation: Initial documentation treated several put-containing structures as unbounded-loss because of common trading-language shorthand.
Impact: This would have wrongly excluded structures whose terminal loss is finite on the admissible NIFTY domain S >= 0.
Resolution: The executable audit now classifies risk from the exact call-tail slope and non-negative underlying domain. Net short-call structures retain the unbounded-loss flag; short puts do not.
Prevention: All risk taxonomy decisions are generated from the mathematical payoff audit and its domain assumptions, not from colloquial strategy labels.

## LRW011 — Moving parent workflow lookup failed
Phase: L2
Observation: CI tests passed, but gh run list did not resolve the already verified parent strategy-regime-lab-v2 artifact from the branch context.
Resolution: pinned verified parent run 35425922439, whose strategy-regime-lab-v2-results artifact is known to contain the research trade population.
Prevention: historical analyses use immutable acquisition/run identifiers once the source artifact is frozen.

## LRW013 — Pinned-parent fix was not applied cleanly on first attempt
Phase: L2
Observation: the workflow still contained the obsolete gh run list lookup and escaped GitHub expressions after the first patch.
Resolution: replaced the full workflow with an explicit immutable PARENT_RUN_ID and native GitHub Actions expressions.
Prevention: inspect the exact committed workflow text after every CI-control correction.

## LRW014 — Optional tabulate dependency caused report-stage CI failure
Phase: L5-L7
Observation: The historical computation completed through risk/WFO analysis but failed while rendering pandas to_markdown because tabulate was not installed.
Resolution: Result rendering now uses pandas to_string and requires no extra reporting package.
Prevention: Avoid optional formatting dependencies inside the numerical research engine.

## LRW015 — Clean limited-risk WFO completion
Phase: L2-L7
Observation: Successful end-to-end workflow run 35496685719 completed tests, pinned parent-artifact download, limited-risk WFO, result publication, and artifact upload.
Resolution: Published structured results under reports/limited_risk_wfo/.
Prevention: Treat 35496685719 and parent source run 35425922439 as the immutable provenance for this phase.

## LRW016 — Fresh holdout not available
Phase: L8
Observation: The currently available 2025-2026 NIFTY period was already exposed by the parent research.
Resolution: L8 is HOLD; no exposed-period statistic is treated as fresh confirmation.
Prevention: Use only post-exposure observations for any future confirmation run.
