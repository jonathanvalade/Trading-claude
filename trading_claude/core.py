"""Deterministic, offline-capable paper-trading core. No brokerage APIs."""
from dataclasses import dataclass, field
from datetime import datetime, time
from zoneinfo import ZoneInfo
from math import floor

NY = ZoneInfo("America/New_York")

@dataclass(frozen=True)
class Config:
    initial_capital_usd: float = 1000
    max_risk_per_trade_pct: float = 1
    max_daily_loss_pct: float = 5
    max_open_positions: int = 10
    max_total_open_risk_pct: float = 3
    max_gross_exposure_pct: float = 100
    poll_interval_seconds: int = 60

@dataclass(frozen=True)
class Bar:
    symbol: str
    timestamp: datetime  # end of completed minute, timezone aware
    open: float
    high: float
    low: float
    close: float
    volume: int

    def validate(self):
        if self.timestamp.tzinfo is None:
            raise ValueError("Timezone-aware bar timestamp required")
        if min(self.open, self.high, self.low, self.close) <= 0:
            raise ValueError("Prices must be positive")
        if self.low > min(self.open, self.close) or self.high < max(self.open, self.close):
            raise ValueError("Invalid OHLC")
        if self.volume < 0:
            raise ValueError("Negative volume")

@dataclass
class Position:
    symbol: str
    quantity: int
    entry: float
    stop: float
    target: float

@dataclass
class Portfolio:
    config: Config = field(default_factory=Config)
    cash: float = 1000
    positions: dict = field(default_factory=dict)
    realized_pnl_today: float = 0
    events: list = field(default_factory=list)
    seen_signals: set = field(default_factory=set)
    halted: bool = False

    def __post_init__(self):
        self.cash = self.config.initial_capital_usd

    def equity(self, prices: dict) -> float:
        return self.cash + sum(p.quantity * prices.get(s, p.entry) for s, p in self.positions.items())

    def open_risk(self) -> float:
        return sum(p.quantity * max(0, p.entry - p.stop) for p in self.positions.values())

    def enter(self, symbol: str, price: float, stop: float, target: float, signal_id: str, prices: dict):
        if signal_id in self.seen_signals:
            return "BLOCK_DUPLICATE"
        if self.halted or self.realized_pnl_today <= -self.config.initial_capital_usd * self.config.max_daily_loss_pct / 100:
            return "BLOCK_DAILY_LOSS"
        if symbol in self.positions or len(self.positions) >= self.config.max_open_positions:
            return "BLOCK_POSITIONS"
        if not (0 < stop < price < target):
            return "BLOCK_LEVELS"
        equity = self.equity(prices)
        if equity <= 0:
            return "BLOCK_EQUITY"
        # Stop distance is planned risk, not guaranteed realized loss (gaps/slippage).
        per_share = price - stop
        risk_budget = equity * self.config.max_risk_per_trade_pct / 100
        remaining_risk = max(0, equity * self.config.max_total_open_risk_pct / 100 - self.open_risk())
        gross = sum(p.quantity * prices.get(s, p.entry) for s, p in self.positions.items())
        exposure_budget = max(0, equity * self.config.max_gross_exposure_pct / 100 - gross)
        qty = min(floor(risk_budget / per_share), floor(remaining_risk / per_share),
                  floor(self.cash / price), floor(exposure_budget / price))
        if qty < 1:
            return "BLOCK_CAPITAL_OR_RISK"
        self.cash -= qty * price
        self.positions[symbol] = Position(symbol, qty, price, stop, target)
        self.seen_signals.add(signal_id)
        self.events.append({"type": "BUY_SIMULATED", "symbol": symbol, "qty": qty, "price": price, "signal_id": signal_id})
        return "FILLED_PAPER"

    def exit(self, symbol: str, price: float, reason: str):
        p = self.positions.pop(symbol)
        self.cash += p.quantity * price
        pnl = p.quantity * (price - p.entry)
        self.realized_pnl_today += pnl
        self.events.append({"type": "SELL_SIMULATED", "symbol": symbol, "qty": p.quantity, "price": price, "pnl": pnl, "reason": reason})
        if self.realized_pnl_today <= -self.config.initial_capital_usd * self.config.max_daily_loss_pct / 100:
            self.halted = True
        return pnl

    def process_bar(self, bar: Bar):
        bar.validate()
        p = self.positions.get(bar.symbol)
        if p:
            # Conservative assumption: stop wins if both touched in one candle.
            if bar.low <= p.stop:
                self.exit(bar.symbol, min(bar.open, p.stop), "STOP")
            elif bar.high >= p.target:
                self.exit(bar.symbol, p.target, "TARGET")

def orb_signal(bars: list[Bar]):
    """15-minute opening range; signals only on completed bars, long-only."""
    if not bars:
        return None
    bars = sorted(bars, key=lambda b: b.timestamp)
    for b in bars:
        b.validate()
    symbol = bars[0].symbol
    if any(b.symbol != symbol for b in bars):
        raise ValueError("Mixed symbols")
    local = [(b, b.timestamp.astimezone(NY)) for b in bars]
    day = local[-1][1].date()
    today = [(b, dt) for b, dt in local if dt.date() == day]
    opening = [b for b, dt in today if time(9, 30) < dt.time() <= time(9, 45)]
    if len(opening) != 15:
        return None
    latest, latest_dt = today[-1]
    if not (time(9, 45) < latest_dt.time() <= time(15, 30)):
        return None
    upper = max(b.high for b in opening)
    lower = min(b.low for b in opening)
    if latest.close <= upper:
        return None
    # Only signal first crossing, not every bar above the range.
    previous = today[-2][0] if len(today) >= 2 else None
    if previous and previous.close > upper:
        return None
    stop = (upper + lower) / 2
    if stop >= latest.close:
        return None
    return {"symbol": symbol, "entry": latest.close, "stop": stop,
            "target": latest.close + (latest.close - stop),
            "signal_id": f"{symbol}:{latest.timestamp.isoformat()}:ORB"}
