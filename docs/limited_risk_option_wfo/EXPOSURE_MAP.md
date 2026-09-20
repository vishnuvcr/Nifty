# NIFTY MC-WFO Exposure Map

## Purpose

This file prevents previously inspected observations from being reused as a fresh final holdout in the limited-risk strategy study.

## Known prior exposure from repository records

| Data period | Prior use | Status for this branch |
|---|---|---|
| 2020–2022 | Development / strategy discovery | Exposed |
| 2023–2024 | Validation / strategy selection | Exposed |
| 2025–2026 through the recorded dataset end | Final/holdout reporting in prior NIFTY MC-WFO work | Exposed |
| 2026-03-30 | Recorded historical-data end in the Batman paper-trading candidate | Current provisional exposure boundary |

## Fresh-holdout rule

The provisional fresh boundary is **after 2026-03-30**.

This boundary is not final until L2 performs a data-lineage audit and proves:
1. observations after the boundary were not used in previous strategy design;
2. they are not present in any prior reported holdout artifact;
3. they are not used to tune the limited-risk branch before L8;
4. their option-chain coverage is sufficient for the declared execution model.

If those conditions are not met, L8 remains HOLD and no fresh-holdout inference is made.

## Audit requirement

At L2, create a machine-readable exposure table with:
- date;
- source dataset;
- previous workflow/run ID;
- previous purpose;
- whether strategy selection saw the observation;
- whether public reports used the observation;
- eligible as fresh holdout: yes/no;
- reason.

