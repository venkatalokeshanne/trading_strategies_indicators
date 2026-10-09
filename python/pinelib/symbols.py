"""Symbol properties a backtest needs: tick size, point value, quantity step, session."""

from __future__ import annotations

import math
from dataclasses import dataclass

# Sessions are exchange-local "HHMM-HHMM". A session ending at or before its start wraps
# midnight (CME futures 1700-1600 Chicago). "0000-0000" = 24 hours.
DEFAULTS = {
    "stock":   dict(mintick=0.01, pointvalue=1.0, qty_step=1.0, timezone="America/New_York",
                    session="0930-1600", ext_session="0400-2000"),
    "crypto":  dict(mintick=0.01, pointvalue=1.0, qty_step=1e-6, timezone="Etc/UTC",
                    session="0000-0000", ext_session="0000-0000"),
    "forex":   dict(mintick=0.00001, pointvalue=1.0, qty_step=1.0, timezone="America/New_York",
                    session="1700-1700", ext_session="1700-1700"),
    "futures": dict(mintick=0.25, pointvalue=1.0, qty_step=1.0, timezone="America/Chicago",
                    session="1700-1600", ext_session="1700-1600"),
    "index":   dict(mintick=0.01, pointvalue=1.0, qty_step=1.0, timezone="America/New_York",
                    session="0930-1600", ext_session="0930-1600"),
}

# Futures contract specs used most often by published strategies.
FUTURES = {
    "ES": (0.25, 50.0), "MES": (0.25, 5.0), "NQ": (0.25, 20.0), "MNQ": (0.25, 2.0),
    "YM": (1.0, 5.0), "MYM": (1.0, 0.5), "RTY": (0.1, 50.0), "M2K": (0.1, 5.0),
    "CL": (0.01, 1000.0), "MCL": (0.01, 100.0), "GC": (0.1, 100.0), "MGC": (0.1, 10.0),
    "SI": (0.005, 5000.0), "NG": (0.001, 10000.0), "ZB": (1 / 32, 1000.0), "ZN": (1 / 64, 1000.0),
}


@dataclass
class SymbolInfo:
    tickerid: str = "NASDAQ:AAPL"
    type: str = "stock"
    mintick: float = 0.01
    pointvalue: float = 1.0
    qty_step: float = 1.0          # [VERIFY] TradingView's quantity rounding per market
    timezone: str = "America/New_York"
    session: str = "0930-1600"
    ext_session: str = "0400-2000"
    extended_hours: bool = False   # data includes pre/post market bars
    currency: str = "USD"
    basecurrency: str = ""
    description: str = ""

    @property
    def ticker(self) -> str:
        return self.tickerid.split(":")[-1]

    @property
    def prefix(self) -> str:
        return self.tickerid.split(":")[0] if ":" in self.tickerid else ""

    @property
    def root(self) -> str:
        return "".join(ch for ch in self.ticker if ch.isalpha())

    def round_qty(self, q: float) -> float:
        if q != q or q <= 0:
            return 0.0
        step = self.qty_step
        return math.floor(q / step + 1e-9) * step

    @property
    def session_start_minutes(self) -> int:
        s = self.ext_session if self.extended_hours else self.session
        hhmm = s.split("-")[0]
        return int(hhmm[:2]) * 60 + int(hhmm[2:4])

    @classmethod
    def make(cls, tickerid: str, type: str, **kw) -> "SymbolInfo":
        base = dict(DEFAULTS.get(type, DEFAULTS["stock"]))
        if type == "futures":
            root = "".join(ch for ch in tickerid.split(":")[-1] if ch.isalpha())
            for r in (root, root.rstrip("!")):
                if r in FUTURES:
                    base["mintick"], base["pointvalue"] = FUTURES[r]
                    break
        base.update(kw)
        return cls(tickerid=tickerid, type=type, **base)
