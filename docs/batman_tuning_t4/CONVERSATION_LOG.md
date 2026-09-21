# T4 Audit Log

T3 corrected run 20 was accepted only after denominator/grid completeness validation.

T4 now performs chronological nested selection over the 2020-2024 development artifact. The final 2020-2024 selector output will be frozen before reading any 2025-2026 holdout outcome.

T4 workflow activated with two parallel tracks: nested development WFO and independent 2025-2026 holdout schema acquisition. The holdout outcome is not read by the nested selector.

The holdout audit confirmed Rahul's expiry field is encoded as expiry_code. Before using it for 2025-2026, the workflow now derives an expiry-code/date-range map from the full cached CSV so no expiry-date assumption is made without evidence.

The corrected T4 development selection is frozen before holdout. The holdout workflow now publishes the derived Rahul expiry_code mapping together with the source audit; no expiry-date assumption will be used.
