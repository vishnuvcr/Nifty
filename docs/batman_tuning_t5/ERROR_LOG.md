# T5 Error Log

No T5 runtime error yet.

The accepted holdout run is run 10 / GitHub Actions 35605509219 after correction of E025-E029:
- daily-price parser;
- timezone-aware entry timestamps;
- missing synchronized-leg expiry fallback.

E030
The paired holdout expiry-control benchmark used a timezone-naive 09:30 cutoff against Rahul's UTC timestamps. Correction: the benchmark cutoff is now localized to Asia/Kolkata and converted to UTC before comparison. The frozen selected-exit result is unaffected.
