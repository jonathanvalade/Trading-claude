# Running the prototype

Requires Python 3.10+.

## Offline demo
```bash
python -m trading_claude.demo
python -m unittest discover -s tests -v
```

## Read-only market-data polling (experimental)
Set `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY` in your environment (not in Git), then:

```bash
python -m trading_claude.runner --once --symbols AAPL MSFT NVDA
python -m trading_claude.runner --symbols AAPL MSFT NVDA
```

The continuous command runs only while your machine/process stays on. It fetches Alpaca's IEX data by default; IEX is not the consolidated US market. No real broker trading API is called.

**Important limitations:** The runner is a prototype, not production-ready: no exchange holiday calendar, no daily P&L reset, no unrealized-loss daily kill switch, no end-of-day liquidation, no transactional per-symbol processing, and no slippage or commissions. Missing data or API failures may result in skipped bars. It should not yet be left unattended as a trustworthy simulation.

The upstream eleven Claude skills are not yet integrated.
