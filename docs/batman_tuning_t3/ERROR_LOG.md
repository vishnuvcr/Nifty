# T3 Error Log

## 2026-09-21

No T3 runtime error yet.

### E017
The initial T3 implementation used the fixed-stop parameter as the trailing retracement in the combined trailing-target + fixed-stop family. Correction: combined rules now use the dedicated retracement parameter while retaining the fixed-stop parameter independently.

Any subsequent T3 computation error will be logged before rerun.
