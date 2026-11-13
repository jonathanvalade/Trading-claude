# Local paper-trading dashboard

Start the trading runner in one terminal and the dashboard in another, using the same database file:

```bash
python -m pip install -r requirements.txt
python -m trading_claude.runner --symbols AAPL MSFT NVDA --database paper.db --ai-gate
python -m trading_claude.dashboard --database paper.db
```

Open http://127.0.0.1:8765. The dashboard reads persisted SQLite paper state and refreshes every 10 seconds. It shows equity, cash, realized/unrealized P&L, open positions, simulated events and the entry-halt state.

**Security:** The dashboard binds to localhost by default and refuses remote bind addresses because it has no authentication. Do not expose it through a public proxy. It has no endpoints that place trades or change state. Price marks can be stale; the view does not guarantee data freshness.

**Scope:** This is a paper portfolio monitor, not a full historical analytics dashboard. AI decision audit logs and historical equity charts remain future work. No real-money broker connectivity exists.
