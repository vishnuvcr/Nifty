# T4 Error Log

No T4 runtime error yet.

T3 denominator bias was corrected before entering T4 and the rejected run is not used.

E023
The T4 holdout probe acquired and cached the Rahul 2025-2026 archive and daily index successfully, but the probe runner lacked pandas. Correction: the probe job now installs pandas before reading the archive; no data source change is required.
