# T4 Error Log

No T4 runtime error yet.

T3 denominator bias was corrected before entering T4 and the rejected run is not used.

E023
The T4 holdout probe acquired and cached the Rahul 2025-2026 archive and daily index successfully, but the probe runner lacked pandas. Correction: the probe job now installs pandas before reading the archive; no data source change is required.

E024
The first T4 selector produced impossible n_training_trades values because variant matching relied on mixed NaN/string comparisons and counted brokerage rows instead of unique decision dates. Correction: variants now use a normalized stable variant_id; selection requires positive unique-trade counts and reports unique trade dates.

E025
The first frozen-holdout execution failed because the independent NIFTY daily CSV stores the closing value in a Price column rather than Close. The Rahul option archive and frozen selection were valid. Correction: the holdout loader now accepts close, price, or last as the daily closing field.

E026
The first corrected holdout run completed with zero trades but did not persist stage-level eligibility diagnostics. Correction: the holdout engine now records expiry candidates, request dates, exact 09:30 spot availability, 756-return readiness, strike-grid availability, four-leg entry availability, gross-MC gate passes, positive-profit references and final exits, even when the result is empty. The artifact upload is always-run.

E027
The holdout diagnostics showed all 81 requests failed the 756-session history gate because comma-formatted prices in the independent NIFTY daily CSV were parsed as nonnumeric. Correction: the loader now removes thousands separators before numeric conversion and records daily-history coverage in the stage diagnostics.
