# T7 Error Log

No T7 computation error yet.

Inherited rejected errors remain documented in T1-T6 logs.

E031
The first bounded smoke test chose the first three 2020 expiries and produced no eligible joint BATMAN rows, so the smoke gate failed before the full scan. This was a poor smoke sample choice, not evidence of data unavailability. Correction: smoke now samples the final three development expiries and always persists skip diagnostics on zero-row bounded runs.

E032
The representative T7 smoke test reached the trailing-stop exit branch and exposed a parameter-slot bug: trailing-stop variants store the trail fraction in the second parameter slot, but the evaluator read the first slot. Correction: trailing-stop evaluation now uses p2, with a direct unit test covering the mapping.
