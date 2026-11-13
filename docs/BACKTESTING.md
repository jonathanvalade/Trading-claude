# Historical backtesting (experimental)

The `trading_claude.backtest` module provides a deterministic, single-symbol, long-only ORB replay. It accepts completed, timezone-aware `Bar` objects sorted by end time. It never calls a brokerage or Claude API.

- The strategy generates a signal from a completed candle; a fill is simulated at the **next candle open** with configurable adverse slippage.
- Entry/exit commissions are charged per share (with configurable minimum). Stops are conservatively prioritized when stop and target are both touched.
- A trade is flattened at/after 15:55 New York time, provided there is a bar. Missing closing bars with an open position cause an explicit error.
- Reports: total return, max drawdown, daily Sharpe (only meaningful with multiple daily samples), trade count, win rate, profit factor, ending equity, event journal and daily equity.
- `compare(bars, approvals)` runs rules-only and AI-gated strategies on the **same bars and cost model**. AI approvals are supplied as an offline `signal_id -> bool` map. Missing approvals reject entries. **No historical Claude inference is performed**, preventing accidental hindsight claims. Approval records must be generated only with information available at each signal time.
- Inputs are validated for malformed OHLC, nonpositive prices and duplicate bars.

## Example

```python
from trading_claude.backtest import run_backtest, Costs, compare
from trading_claude.core import Bar
# Load your own historical completed Bar objects, including the end-of-session bars.
result = run_backtest(bars, costs=Costs(slippage_bps=5, commission_per_share=0.005))
print(result["metrics"])
both = compare(bars, approvals={})
```

## Limitations and research integrity

This is not yet a production-grade backtester. No portfolio-level multi-symbol execution, bid/ask order book, partial fills, exchange halts, corporate-action adjustments, market impact, borrow costs, calibrated AI confidence, walk-forward validation or Monte Carlo are implemented. A one-minute candle cannot determine the true sequence of stop/target touches. The replay assumes a fill at the next bar open and may be optimistic on illiquid securities. Historical AI comparisons require a timestamped decision archive; otherwise a fair comparison cannot be claimed. Do not infer profitability from these synthetic or in-sample tests.
