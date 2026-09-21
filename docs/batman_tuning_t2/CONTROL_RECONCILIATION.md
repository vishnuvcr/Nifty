# T2 Control Reconciliation

## Control hierarchy

The study contains two deliberately distinct controls.

### Parent historical benchmark

The promoted BATMAN historical implementation used daily NSE F&O bhavcopy snapshots. Its Monte Carlo gate was gross MC expected P&L greater than zero. Option entry prices were daily EOD snapshot values; the historical result was then stressed for a 2-point execution-cost assumption.

### Operational intraday timing control

The entry-timing study compares D0-D6 candidates against an operational 09:30 control:

- D3 relative to the target expiry session.
- Same-session 09:30 NIFTY spot signal.
- First positive-volume option observation strictly after 09:30 for execution.
- Frozen BATMAN structure.
- Gross MC-EV > 0 as the primary entry gate.

## Required reconciliation

1. Reconstruct the parent-style D3/EOD control from the 2020-2024 Ayush archive.
2. Compare its strike selection, MC-EV, gate rate and realized expiry P&L against the previously documented parent candidate.
3. Compare the same D3 opportunities under the intraday 09:30 execution layer.
4. Attribute differences to EOD versus 09:30 spot, EOD versus post-09:30 option execution, gate definition, source differences and strike availability.
5. Independently cross-check a stratified sample against official NSE bhavcopy data before calling the EOD reconstruction equivalent to the historical parent benchmark.

No D0-D6 candidate is promoted until this reconciliation is complete.
