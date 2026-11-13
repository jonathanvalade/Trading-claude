"""Read-only market polling and simulated paper execution; no broker orders."""
import argparse
import logging
import time
from datetime import datetime, timezone
from .core import NY, orb_signal
from .calendar import session, can_enter, should_flatten
from .market_data import AlpacaData
from .storage import Store
from .ai_advisor import ClaudeAdvisor

LOG = logging.getLogger(__name__)

def market_window(now):
    return can_enter(now)

def cycle(data, store, symbols, now=None, advisor=None):
    now = now or datetime.now(timezone.utc)
    portfolio = store.load()
    schedule = session(now)
    if schedule is None:
        return {"status": "MARKET_CLOSED", "cash": portfolio.cash}
    opened, closed = schedule
    if now < opened or now >= closed:
        return {"status": "OUTSIDE_SESSION", "cash": portfolio.cash}
    portfolio.begin_session(now.astimezone(NY).date().isoformat())
    entering = can_enter(now)
    flattening = should_flatten(now)
    # Include held positions even if no longer in the watchlist.
    watched = list(dict.fromkeys(list(portfolio.positions) + list(symbols)))
    fetched = {}
    for symbol in watched:
        try:
            bars = data.bars(symbol, now=now)
            if not bars:
                LOG.warning("Missing bars for %s", symbol)
                continue
            latest = bars[-1]
            age = (now - latest.timestamp).total_seconds()
            if age < 0 or age > 120:
                LOG.warning("Stale data for %s: %.1f seconds", symbol, age)
                continue
            fetched[symbol] = bars
            portfolio.last_prices[symbol] = latest.close
        except Exception:
            LOG.exception("Market-data failure for %s", symbol)
    portfolio.check_drawdown()
    # Exits always have priority. Never act on stale bars.
    for symbol, bars in fetched.items():
        try:
            portfolio.process_bar(bars[-1])
        except Exception:
            LOG.exception("Exit evaluation failure for %s", symbol)
    if flattening:
        for symbol in list(portfolio.positions):
            if symbol in fetched:
                portfolio.exit(symbol, fetched[symbol][-1].close, "END_OF_SESSION")
            else:
                LOG.error("CANNOT FLATTEN %s: missing fresh price", symbol)
    elif entering and not portfolio.halted:
        for symbol in symbols:
            if symbol not in fetched:
                continue
            try:
                bars = fetched[symbol]
                signal = orb_signal(bars)
                if not signal:
                    continue
                if advisor is not None:
                    try:
                        advice = advisor.evaluate(signal, bars)
                        LOG.info("AI review %s: %s (%s)", symbol, advice.decision, advice.reason)
                        if advice.decision != "APPROVE":
                            continue
                    except Exception:
                        LOG.exception("AI unavailable; blocking entry for %s", symbol)
                        continue
                result = portfolio.enter(symbol, signal["entry"], signal["stop"],
                                         signal["target"], signal["signal_id"], portfolio.last_prices)
                LOG.info("%s: %s", symbol, result)
            except Exception:
                LOG.exception("Entry evaluation failure for %s", symbol)
    store.save(portfolio)
    return {"status": "OK", "cash": portfolio.cash, "halted": portfolio.halted,
            "equity": portfolio.equity(portfolio.last_prices),
            "positions": list(portfolio.positions), "events": len(portfolio.events)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", default=["AAPL", "MSFT", "NVDA"])
    parser.add_argument("--database", default="paper.db")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--ai-gate", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    data, store = AlpacaData(), Store(args.database)
    advisor = ClaudeAdvisor() if args.ai_gate else None
    while True:
        now = datetime.now(timezone.utc)
        LOG.info("cycle %s", cycle(data, store, args.symbols, now, advisor=advisor))
        if args.once:
            break
        time.sleep(max(1, 60 - time.time() % 60 + 3))

if __name__ == "__main__":
    main()
