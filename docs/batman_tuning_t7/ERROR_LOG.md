# T7 Error Log

No T7 computation error yet.

Inherited rejected errors remain documented in T1-T6 logs.

E031
The first bounded smoke test chose the first three 2020 expiries and produced no eligible joint BATMAN rows, so the smoke gate failed before the full scan. This was a poor smoke sample choice, not evidence of data unavailability. Correction: smoke now samples the final three development expiries and always persists skip diagnostics on zero-row bounded runs.
