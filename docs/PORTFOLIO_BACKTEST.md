# Multi-symbol historical replay (experimental)

`trading_claude.portfolio_backtest.replay` synchronizes completed one-minute bars across symbols. Pending signals execute at each symbol's **next available bar open**, with adverse slippage and commissions. Cash and exposure limits are shared across the portfolio. Symbols are processed alphabetically when timestamps tie; this is a deterministic but arbitrary tie-break.

```python
from trading_claude.portfolio_backtest import replay, compare_portfolios
from trading_claude.backtest import Costs
result = replay(historical_bars, costs=Costs(slippage_bps=5, commission_per_share=0.005))
print(result["metrics"])
comparison = compare_portfolios(historical_bars, approvals={})
```

`approvals` must be a timestamp-valid, pre-recorded mapping from signal IDs to boolean decisions. Empty approvals reject all signals; no Claude API calls occur during replay. A true walk-forward study needs strictly chronological training/test splits and time-stamped model versions and prompts, and is **not implemented** by this comparison alone.

Limitations: the module does not independently verify NYSE holidays or all minute gaps; supply the actual session closing times for early-close sessions. Intra-minute fills, market impact, partial fills and stop/target touch ordering are approximations. Risk of loss may exceed stop distance. No live orders are possible.
