# SENSEX Options Research Conversation Log

## 2026-09-20

### User instruction
Start a separate branch to test the final derived Batman strategy and the Adaptive strategy in SENSEX options trading.

### Recorded research decision
- Dedicated branch: research/sensex-batman-adaptive-v1.
- Keep this study separate from the NIFTY MC-WFO manuscript.
- Treat the NIFTY Phase-10 Batman and Adaptive specifications as frozen parent protocols.
- Validate SENSEX-specific data, contract rules, expiry calendar, quote quality and transaction costs before running performance tests.
- Do not tune the SENSEX study using its final holdout.

### Audit note
This repository log records user-visible instructions and research decisions. It does not store private chain-of-thought or hidden reasoning.