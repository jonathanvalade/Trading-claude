# Paper-trading safety implementation

The XNYS calendar comes from exchange_calendars and handles US market holidays and scheduled early closes. Entries are allowed from 16 minutes after open until 30 minutes before close; positions are flattened starting 5 minutes before close when fresh prices exist.

Risk is tracked using portfolio mark-to-market equity against the session-start equity. A 5% drawdown halts **new entries**; protective exits remain active. Halt status, last known marks and processed candle IDs survive restarts through SQLite. Duplicate candles do not retrigger exits.

## Known gaps — do not run unattended
- If a price feed fails near close, a position cannot be flattened; the system logs an error and retains it. There is no guaranteed exit.
- Missing prices may make mark-to-market equity stale; no complete-portfolio freshness gate is implemented yet.
- Daily session baseline uses last saved marks, not independently verified exchange opening marks.
- Entry fills use the signal candle close (lookahead/execution optimism); slippage, spread, fees and partial fills are not modeled.
- SQLite is not protected against two runner processes writing simultaneously.
- Paper only, no real broker endpoints. Tests must pass in CI before relying on any behavior.
