"""Read-only Alpaca historical market-data adapter. No order endpoints."""
import json
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from .core import Bar

class AlpacaData:
    def __init__(self, key=None, secret=None, feed="iex"):
        self.key = key or os.getenv("APCA_API_KEY_ID")
        self.secret = secret or os.getenv("APCA_API_SECRET_KEY")
        if not self.key or not self.secret:
            raise RuntimeError("Missing APCA_API_KEY_ID / APCA_API_SECRET_KEY")
        if feed not in ("iex", "sip"):
            raise ValueError("Unsupported feed")
        self.feed = feed

    def bars(self, symbol, now=None, limit=120):
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            raise ValueError("now must be timezone aware")
        # Request enough history for ORB, then reject incomplete candles.
        params = urlencode({"timeframe": "1Min", "start": (now - timedelta(hours=8)).isoformat(),
                            "end": now.isoformat(), "limit": min(limit, 10000), "feed": self.feed,
                            "adjustment": "raw"})
        url = "https://data.alpaca.markets/v2/stocks/" + symbol + "/bars?" + params
        request = Request(url, headers={"APCA-API-KEY-ID": self.key,
                                        "APCA-API-SECRET-KEY": self.secret})
        with urlopen(request, timeout=12) as response:
            payload = json.load(response)
        result = []
        for raw in payload.get("bars", []):
            # Alpaca timestamps mark bar START; our engine requires bar END.
            start = datetime.fromisoformat(raw["t"].replace("Z", "+00:00"))
            end = start + timedelta(minutes=1)
            if end > now - timedelta(seconds=3):
                continue
            bar = Bar(symbol, end, float(raw["o"]), float(raw["h"]), float(raw["l"]),
                      float(raw["c"]), int(raw["v"]))
            bar.validate()
            result.append(bar)
        return sorted(result, key=lambda b: b.timestamp)
