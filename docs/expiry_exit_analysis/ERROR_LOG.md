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
