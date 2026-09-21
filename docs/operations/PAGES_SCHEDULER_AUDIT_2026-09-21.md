# Pages / 09:30 Signal Scheduler Audit — 2026-09-21

## Finding

The unified GitHub Pages site could be overwritten by an individual signal-producing workflow. In particular, the standalone NIFTY Batman producer had its own Pages deployment step and deployed from a partial research branch. That could replace the unified site with only the BATMAN dashboard.

The 09:30 IST schedule is intended for the NIFTY and SENSEX paper-signal systems. Before this audit, workflow execution time was not persisted in a structured file, so a historical run could not be distinguished reliably from an absent or failed run by the Pages site alone.

## Corrective controls

1. Signal-producing workflows no longer deploy GitHub Pages directly.
2. Each 09:30 producer persists a run-audit JSON record containing workflow, run ID, trigger, scheduled time, completion time and job status.
3. Each producer requests the combined publisher workflow after state persistence; the 16:00 IST publisher remains the scheduled backstop.
4. The combined publisher is the authoritative Pages deployer.
5. The publisher synchronizes the NIFTY, SENSEX and defined-risk dashboard trees and validates the complete required Pages manifest before deployment.
6. The root Pages selector displays the latest recorded run time for each published system using site/data/run_status.json.
7. Historical run times that were not previously persisted are explicitly shown as "Not recorded"; no timestamp is inferred from unrelated commits.

## Expected published dashboard tree

- NIFTY / BATMAN
- NIFTY / ADAPTIVE
- NIFTY / Jade Lizard
- NIFTY / Put Ratio Spread
- SENSEX / BATMAN
- SENSEX / ADAPTIVE
- SENSEX / Jade Lizard
- SENSEX / Put Ratio Spread

## Scientific / audit boundary

A missed 09:30 run is not backfilled as a 09:30 market observation using later quotes. The repair only fixes orchestration, observability and publication. A future successful scheduled run becomes the next prospective observation.
