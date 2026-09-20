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

 — Connected GitHub Actions dispatch unavailable
Type: execution infrastructure
Observation: the connected GitHub toolset exposes workflow inspection/rerun operations but does not expose workflow_dispatch. Commits created through the connector did not start the analysis workflow, and the PR path was blocked by the repository's Codex code-review quota.
Resolution: retain the complete analysis branch and a manual dispatcher workflow on main; do not fabricate numerical results without a completed CI run.
Prevention: future data-heavy reruns should invoke the dispatcher manually from the GitHub Actions UI when the connected session lacks workflow_dispatch capability.

### E003 — Analysis branch/dispatcher separation
Type: repository/CI architecture
Observation: the data-heavy analysis branch cannot reliably self-trigger a workflow when workflow execution permissions are unavailable through the connected GitHub toolset.
Resolution: the execution path is separated from the research branch: the dispatcher workflow lives on main, while the analysis engine, protocol and eventual reports remain isolated on research/expiry-auction-exit-analysis-v1.
Prevention: keep execution dispatchers on main and keep research outputs on dedicated analysis branches; never treat an unexecuted workflow as a completed numerical result.

### E004 — Connected GitHub Actions dispatch unavailable
Type: execution infrastructure
Observation: the connected GitHub toolset exposes workflow inspection/rerun operations but does not expose workflow_dispatch. Commits created through the connector did not start the analysis workflow, and the PR path was blocked by the repository's Codex code-review quota.
Resolution: retain the complete analysis branch and a manual dispatcher workflow on main; do not fabricate numerical results without a completed CI run.
Prevention: future data-heavy reruns should invoke the dispatcher manually from the GitHub Actions UI when the connected session lacks workflow_dispatch capability.


### E003 — Analysis branch/dispatcher separation
Type: repository/CI architecture
Observation: the data-heavy analysis branch cannot reliably self-trigger a workflow when workflow execution permissions are unavailable through the connected GitHub toolset.
Resolution: execution dispatch is separated from the research branch; the dispatcher is kept on main while the analysis engine and reports remain isolated on the dedicated analysis branch.
Prevention: never treat an unexecuted workflow as a completed numerical result.
