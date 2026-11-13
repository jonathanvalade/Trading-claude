"""Minute-aligned paper monitor. Read-only data endpoint; no real order APIs.

EXPERIMENTAL: regular-session weekdays only; exchange holiday calendar and
unrealized daily loss checks are NOT implemented. Do not run unattended.
"""
import argparse
import logging
import time
from datetime import datetime, timezone, time as clocktime
from .core import NY, orb_signal
from .market_data import AlpacaData
from .storage import Store
from .ai_advisor import ClaudeAdvisor

LOG = logging.getLogger(__name__)

def market_window(now):
    local = now.astimezone(NY)
    return local.weekday() < 5 and clocktime(9, 46) <= local.time() < clocktime(15, 30)

def cycle(data, store, symbols, now=None, advisor=None):
    now = now or datetime.now(timezone.utc)
    portfolio = store.load()
    if not market_window(now):
        return {"status": "OUTSIDE_WINDOW", "equity": portfolio.cash}
    prices = {}
    for symbol in symbols:
        try:
            bars = data.bars(symbol, now=now)
            if not bars:
                LOG.warning("No bars for %s", symbol)
                continue
            latest = bars[-1]
            age = (now - latest.timestamp).total_seconds()
            if age < 0 or age > 120:
                LOG.warning("Stale bars for %s (%.1f seconds)", symbol, age)
                continue
            prices[symbol] = latest.close
            # Check exits before looking for new entries.
            portfolio.process_bar(latest)
            signal = orb_signal(bars)
            if signal:
                if advisor is not None:
                    try:
                        advice = advisor.evaluate(signal, bars)
                        LOG.info("AI review %s: %s (%s)", symbol, advice.decision, advice.reason)
                        if advice.decision != "APPROVE":
                            continue
                    except Exception:
                        LOG.exception("AI unavailable/invalid; blocking new entry for %s", symbol)
                        continue
                result = portfolio.enter(symbol, signal["entry"], signal["stop"],
                                         signal["target"], signal["signal_id"], prices)
                LOG.info("%s: %s", symbol, result)
        except Exception:
            LOG.exception("Cycle failed for %s", symbol)
    store.save(portfolio)
    return {"status": "OK", "cash": portfolio.cash,
            "positions": list(portfolio.positions), "events": len(portfolio.events)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", default=["AAPL", "MSFT", "NVDA"])
    parser.add_argument("--database", default="paper.db")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--ai-gate", action="store_true", help="Require Claude approval for every new paper entry")
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
