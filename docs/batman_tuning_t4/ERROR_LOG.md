# T4 Error Log

No T4 runtime error yet.

T3 denominator bias was corrected before entering T4 and the rejected run is not used.

E023
The T4 holdout probe acquired and cached the Rahul 2025-2026 archive and daily index successfully, but the probe runner lacked pandas. Correction: the probe job now installs pandas before reading the archive; no data source change is required.

E024
The first T4 selector produced impossible n_training_trades values because variant matching relied on mixed NaN/string comparisons and counted brokerage rows instead of unique decision dates. Correction: variants now use a normalized stable variant_id; selection requires positive unique-trade counts and reports unique trade dates.
