# Trading Claude

Autonomous **paper-only** US equities trading research prototype. Polls a market-data provider every 60 seconds during regular NYSE hours, generates deterministic opening-range breakout signals, enforces cash/risk limits and records simulated fills.

**No live brokerage connectivity, no real orders, no profitability claims.** Starting balance $1,000 USD; 1% max planned risk per trade; 5% daily drawdown limit; 10 maximum open positions; 3% aggregate planned open risk; 100% cash exposure cap.

## Quick start (offline demo)

```bash
python -m trading_claude.demo
python -m unittest discover -s tests -v
```

The demo uses deterministic synthetic candles. No external data subscription is included. To monitor real markets, implement a licensed `MarketDataProvider` and deploy the scheduler on an always-on host. No order execution against real brokers is implemented.

## Upstream inspiration

Inspired by [Jakeschincariol/day-trader-skill](https://github.com/Jakeschincariol/day-trader-skill) (MIT). The upstream 11 Claude skills are **not yet copied or integrated**; see `docs/ROADMAP.md`. This project implements a separate testable core first.
