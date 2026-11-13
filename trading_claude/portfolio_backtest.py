"""Multi-symbol, bar-by-bar portfolio replay with causal fills and explicit costs."""
from collections import defaultdict
from datetime import time
from .backtest import Costs, statistics, validate_history
from .core import Config, Portfolio, NY, orb_signal

def replay(bars, config=None, costs=None, approvals=None, session_closes=None):
    """Replay a portfolio on synchronized completed bars.

    session_closes maps ISO session dates to local close times; defaults 16:00 ET.
    For early-close days, provide the actual exchange close. Missing last-bar
    data for held positions raises instead of fabricating fills.
    """
    config, costs = config or Config(), costs or Costs()
    ordered = validate_history(bars)
    by_time = defaultdict(list)
    for bar in ordered:
        by_time[bar.timestamp].append(bar)
    portfolio = Portfolio(config=config)
    history = defaultdict(list)
    pending = {}
    trades, curve = [], []
    current_day = None
    session_closes = session_closes or {}
    for stamp, batch in sorted(by_time.items()):
        dt = stamp.astimezone(NY)
        day = dt.date().isoformat()
        if current_day != day:
            if portfolio.positions:
                raise ValueError("Incomplete previous session: positions remain open")
            current_day = day
            history.clear()
            pending.clear()
            portfolio.begin_session(day)
        close_at = session_closes.get(day, time(16, 0))
        flatten_at = (dt.hour * 60 + dt.minute >= close_at.hour * 60 + close_at.minute - 5)
        batch = sorted(batch, key=lambda b: b.symbol)
        fresh = {bar.symbol: bar for bar in batch}
        # Pending orders are filled at the next bar for THAT symbol only.
        for symbol in sorted(list(pending)):
            if symbol not in fresh:
                continue
            signal = pending.pop(symbol)
            bar = fresh[symbol]
            if bar.timestamp.astimezone(NY).date().isoformat() != signal["day"]:
                continue
            if flatten_at:
                continue
            entry = bar.open * (1 + costs.slippage_bps / 10000)
            if entry <= signal["stop"]:
                continue
            distance = signal["entry"] - signal["stop"]
            if distance <= 0:
                continue
            # Reserve commission from cash before sizing to prevent overdraft.
            available = portfolio.cash
            portfolio.cash -= costs.minimum_commission
            outcome = portfolio.enter(symbol, entry, signal["stop"], entry + distance,
                                      signal["signal_id"], {symbol: entry})
            portfolio.cash += costs.minimum_commission
            if outcome == "FILLED_PAPER":
                qty = portfolio.positions[symbol].quantity
                fee = costs.fee(qty)
                if portfolio.cash < fee:
                    # Undo fill rather than letting a fee produce negative cash.
                    portfolio.cash += qty * entry
                    del portfolio.positions[symbol]
                    portfolio.seen_signals.discard(signal["signal_id"])
                    portfolio.events.pop()
                    continue
                portfolio.cash -= fee
                portfolio.events.append({"type": "COMMISSION", "symbol": symbol, "amount": fee})
        # Evaluate exits on fresh bars; conservative stop-first ordering.
        for bar in batch:
            pos = portfolio.positions.get(bar.symbol)
            if pos:
                reason, exit_price = None, None
                if bar.low <= pos.stop:
                    reason, exit_price = "STOP", min(bar.open, pos.stop)
                elif bar.high >= pos.target:
                    reason, exit_price = "TARGET", pos.target
                elif flatten_at:
                    reason, exit_price = "EOD", bar.close
                if exit_price is not None:
                    fee = costs.fee(pos.quantity)
                    pnl = portfolio.exit(bar.symbol, exit_price * (1 - costs.slippage_bps / 10000), reason)
                    portfolio.cash -= fee
                    trades.append(pnl - fee)
            portfolio.last_prices[bar.symbol] = bar.close
            history[bar.symbol].append(bar)
        portfolio.check_drawdown()
        if not flatten_at and not portfolio.halted and time(9, 46) <= dt.time() < time(15, 29):
            for bar in batch:
                if bar.symbol in portfolio.positions or bar.symbol in pending:
                    continue
                signal = orb_signal(history[bar.symbol])
                if signal and (approvals is None or approvals.get(signal["signal_id"], False)):
                    pending[bar.symbol] = dict(signal, day=day)
        if flatten_at and dt.time() <= close_at:
            if portfolio.positions and any(symbol not in fresh for symbol in portfolio.positions):
                # Missing a quote at this timestamp is not automatically fatal:
                # require flat at session boundary or end of dataset.
                pass
            # One daily mark, updated as final bars arrive.
            equity = portfolio.equity(portfolio.last_prices)
            if curve and curve[-1][0] == day:
                curve[-1] = (day, equity)
            else:
                curve.append((day, equity))
    if portfolio.positions:
        raise ValueError("Incomplete final session: positions remain open")
    if not curve and ordered:
        curve.append((current_day, portfolio.equity(portfolio.last_prices)))
    return {"metrics": statistics(curve, trades, config.initial_capital_usd),
            "equity_curve": curve, "trades": trades, "events": portfolio.events}

def compare_portfolios(bars, approvals, config=None, costs=None, session_closes=None):
    return {"rules_only": replay(bars, config, costs, None, session_closes),
            "ai_gated": replay(bars, config, costs, approvals, session_closes)}
