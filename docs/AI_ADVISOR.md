# Optional Claude approval gate (experimental)

The Python scanner produces an ORB signal from completed minute bars. Claude receives that signal and up to 25 completed candles and can only return APPROVE or REJECT. The deterministic risk engine remains authoritative. **No brokerage orders can be sent.**

By default Claude is disabled; Python paper simulation runs without AI.

To enable AI review, configure environment variables securely (do not commit secrets):

```bash
export APCA_API_KEY_ID="your_read_only_data_key"
export APCA_API_SECRET_KEY="your_data_secret"
export ANTHROPIC_API_KEY="your_anthropic_key"
export ANTHROPIC_MODEL="your_available_model_id"
python -m trading_claude.runner --symbols AAPL MSFT NVDA --ai-gate
```

Claude is called only when an ORB signal exists, not every 60 seconds for every stock. Calls incur API charges. Errors, timeouts, malformed JSON and REJECT decisions block new entries. The AI cannot alter position sizing, stops, risk settings or order execution.

**Not yet production-ready:** no news feed, no calibrated model confidence, no A/B evaluation, no consolidated SIP feed guarantee, no holiday calendar, no unrealized drawdown gate, no daily reset, no end-of-day flattening. The 11 upstream skills remain to be audited/integrated. Do not run this as an unattended financial decision system.
