"""Offline demonstration with synthetic candles; never accesses a broker."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from .core import Bar, Portfolio, orb_signal

def main():
    tz = ZoneInfo("America/New_York")
    start = datetime(2026, 11, 12, 9, 30, tzinfo=tz)
    bars = []
    for minute in range(1, 17):
        close = 10.5 if minute == 16 else 10.0
        bars.append(Bar("DEMO", start + timedelta(minutes=minute), 10, 10.2 if minute < 16 else 10.6, 9.8 if minute < 16 else 10, close, 1000))
    signal = orb_signal(bars)
    portfolio = Portfolio()
    if signal:
        result = portfolio.enter(signal["symbol"], signal["entry"], signal["stop"], signal["target"], signal["signal_id"], {"DEMO": signal["entry"]})
        print(result, portfolio.events)
    else:
        print("No signal")

if __name__ == "__main__":
    main()
