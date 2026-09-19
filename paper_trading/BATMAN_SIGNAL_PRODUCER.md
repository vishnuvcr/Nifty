# Batman Signal Producer

This is the separate prospective signal-publication workflow for the frozen Batman research candidate.

## Frozen protocol

- Entry timing: exactly 3 future NSE trading sessions before the selected expiry.
- Monte Carlo: 5,000 bootstrap paths by default.
- Return lookback: 756 daily NIFTY 50 closes.
- Terminal quantiles: P20, P35, P65, P80.
- Strategy:
  - Buy 1 x PE(P35)
  - Sell 2 x PE(P20)
  - Buy 1 x CE(P65)
  - Sell 2 x CE(P80)
- Signal gate: net MC expected P&L > 0 and at least one risk-sized strategy lot fits configured paper capital.
- Risk sizing: max(ES95, ES99) as a sizing proxy.
- Stress execution cost: 2.0 option points per contract by default, applied before the EV gate.
- Missing/invalid data: no imputation; the producer publishes NO_TRADE / NOT_ENTRY_DAY.

## Schedule

Workflow:
.github/workflows/batman-signal-producer.yml

It supports manual workflow_dispatch and a weekday schedule at 10:10 UTC (15:40 IST).

Manual runs are live/current-day runs, not historical replays.

## GitHub Pages

The workflow creates and deploys a static Pages site containing:

- latest Batman signal
- MC terminal quantiles
- selected strikes
- gross and net MC EV
- MC probability of profit
- ES95 / ES99
- capital/risk sizing
- recent signal history
- paper-trade ledger
- JSON and CSV downloads

One-time repository setup: enable GitHub Pages with GitHub Actions as the Pages source in repository Settings -> Pages.

## Telegram

Add these repository Actions secrets:

- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID

On entry dates the workflow sends the signal and MC results. When an open paper trade reaches expiry, it also sends the realized paper P&L.

Without the secrets, the producer still publishes to Pages and logs TELEGRAM_NOT_CONFIGURED.

## Persistent paper-trading state

- paper_trading/batman_signals.csv stores every producer run, including non-entry days.
- paper_trading/batman_ledger.csv stores frozen entry-day paper positions and eventual expiry outcomes.
- The ledger stores the lot size used at entry, so realized P&L is not hard-coded to 65.

## Data source and execution

The producer uses NSE public endpoints for NIFTY 50 historical closes, trading holidays and the live NIFTY option chain. For option execution assumptions it uses ask for buys and bid for sells when available, falling back to last price only when bid/ask is unavailable.

It does not place broker orders. This is a research and paper-trading publication system.
