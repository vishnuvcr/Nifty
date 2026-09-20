# Long-Premium MC/WFO v1 — Error Log

### 2026-09-20 — LP implementation prototype parameter bug

Observation: the first local prototype accidentally created invalid Python assignments while converting command-line defaults.

Impact: prototype could not compile.

Resolution: replaced invalid global assignments with explicit argparse defaults and local parameters; reran py_compile and the full historical analysis successfully.

Prevention: no generated source replacement is accepted into the branch until syntax compilation and an end-to-end historical run pass.

### 2026-09-20 — Parent final period exposure

Observation: 2025-2026 observations already appeared in the parent NIFTY study.

Resolution: treated them as descriptive exposed-final data, not as a fresh holdout.

Prevention: fresh post-exposure data are required before promotion.
