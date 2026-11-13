"""Causal, next-bar-open paper backtest. No broker connections or AI API calls."""
from dataclasses import dataclass
from datetime import time
from math import sqrt
from statistics import mean, stdev
from .core import Config, Portfolio, NY, orb_signal

@dataclass(frozen=True)
class Costs:
    slippage_bps: float = 5
    commission_per_share: float = 0.005
    minimum_commission: float = 0.0
    def __post_init__(self):
        if min(self.slippage_bps, self.commission_per_share, self.minimum_commission) < 0:
            raise ValueError("Negative trading cost")
    def fee(self, qty):
        return max(self.minimum_commission, qty * self.commission_per_share)

def validate_history(bars):
    ordered = sorted(bars, key=lambda b: b.timestamp)
    seen = set()
    for bar in ordered:
        bar.validate()
        if (bar.symbol, bar.timestamp) in seen:
            raise ValueError("Duplicate historical candle")
        seen.add((bar.symbol, bar.timestamp))
    return ordered

def statistics(equity_curve, trades, starting_equity):
    if not equity_curve:
        return {"total_return_pct": 0.0, "max_drawdown_pct": 0.0, "sharpe_daily": None,
                "trade_count": 0, "win_rate_pct": None, "profit_factor": None,
                "ending_equity": starting_equity}
    peak = starting_equity
    max_dd = 0.0
    daily = []
    previous = starting_equity
    for _, value in equity_curve:
        peak = max(peak, value)
        if peak > 0:
            max_dd = max(max_dd, (peak - value) / peak * 100)
        if previous > 0:
            daily.append(value / previous - 1)
        previous = value
    wins = [x for x in trades if x > 0]
    gains = sum(wins)
    losses = -sum(x for x in trades if x < 0)
    sharpe = (mean(daily) / stdev(daily) * sqrt(252)) if len(daily) > 1 and stdev(daily) > 0 else None
    return {"total_return_pct": (equity_curve[-1][1] / starting_equity - 1) * 100,
            "max_drawdown_pct": max_dd, "sharpe_daily": sharpe,
            "trade_count": len(trades), "win_rate_pct": len(wins) / len(trades) * 100 if trades else None,
            "profit_factor": gains / losses if losses else (None if not gains else float("inf")),
            "ending_equity": equity_curve[-1][1]}

def run_backtest(bars, config=None, costs=None, approvals=None):
    """Single-symbol long-only ORB replay.

    approvals: offline mapping signal_id -> bool. Missing decisions REJECT (fail closed).
    None means deterministic strategy without AI. Compare on identical historical bars.
    """
    config = config or Config()
    costs = costs or Costs()
    ordered = validate_history(bars)
    if len({b.symbol for b in ordered}) > 1:
        raise ValueError("Single-symbol backtest; portfolio multi-symbol replay not supported")
    p = Portfolio(config=config)
    pending = None
    history = []
    equity_curve = []
    trades = []
    entry_fees = {}
    active_day = None
    for index, bar in enumerate(ordered):
        dt = bar.timestamp.astimezone(NY)
        day = dt.date().isoformat()
        if active_day != day:
            if p.positions:
                raise ValueError("Previous session not flattened: missing closing data")
            active_day = day
            pending = None
            p.begin_session(day)
            history = []
        # Fill only at NEXT completed bar's opening price, never the signal close.
        if pending is not None:
            signal = pending
            pending = None
            entry = bar.open * (1 + costs.slippage_bps / 10000)
            distance = signal["entry"] - signal["stop"]
            if distance > 0 and entry > signal["stop"]:
                target = entry + distance
                outcome = p.enter(bar.symbol, entry, signal["stop"], target,
                                  signal["signal_id"], {bar.symbol: entry})
                if outcome == "FILLED_PAPER":
                    pos = p.positions[bar.symbol]
                    fee = costs.fee(pos.quantity)
                    p.cash -= fee
                    entry_fees[bar.symbol] = fee
                    p.events.append({"type": "COMMISSION", "amount": fee})
        # Existing positions: conservative stop-first if both levels touched.
        if bar.symbol in p.positions:
            pos = p.positions[bar.symbol]
            exit_price = None
            reason = None
            if bar.low <= pos.stop:
                exit_price = min(bar.open, pos.stop) * (1 - costs.slippage_bps / 10000)
                reason = "STOP"
            elif bar.high >= pos.target:
                exit_price = pos.target * (1 - costs.slippage_bps / 10000)
                reason = "TARGET"
            elif dt.time() >= time(15, 55):
                exit_price = bar.close * (1 - costs.slippage_bps / 10000)
                reason = "EOD"
            if exit_price is not None:
                fee = costs.fee(pos.quantity)
                pnl = p.exit(bar.symbol, exit_price, reason) - fee
                p.cash -= fee
                trades.append(pnl - entry_fees.pop(bar.symbol, 0))
        p.last_prices[bar.symbol] = bar.close
        p.check_drawdown()
        history.append(bar)
        # Do not use bar close as an entry price; defer to next bar.
        if not p.positions and not p.halted and time(9, 46) <= dt.time() < time(15, 29):
            signal = orb_signal(history)
            if signal and (approvals is None or approvals.get(signal["signal_id"], False)):
                pending = signal
        # End-of-day marks are after the close. No artificial flat if bars end early.
        if dt.time() >= time(15, 55):
            daily_equity = (day, p.equity(p.last_prices))
            if equity_curve and equity_curve[-1][0] == day:
                equity_curve[-1] = daily_equity
            else:
                equity_curve.append(daily_equity)
    if p.positions:
        raise ValueError("History ends with open position: missing EOD candles")
    if not equity_curve and ordered:
        equity_curve.append((active_day, p.equity(p.last_prices)))
    return {"metrics": statistics(equity_curve, trades, config.initial_capital_usd),
            "trades": trades, "equity_curve": equity_curve, "events": p.events}

def compare(bars, approvals, config=None, costs=None):
    """Same historical sample/costs; approvals must be precomputed without future bars."""
    return {"rules_only": run_backtest(bars, config, costs),
            "ai_gated": run_backtest(bars, config, costs, approvals)}
