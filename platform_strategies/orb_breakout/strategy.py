"""
Opening Range Breakout.

The original day-trading play: the first N minutes of the session set
a range; a close beyond that range afterward is traded as a breakout
in the direction of the break, on the read that the opening auction
already absorbed the overnight order flow and a clean break signals
genuine one-way pressure for the rest of the session.

Entry: after the opening window has closed, close crosses above the
opening-range high (long) or below the opening-range low (short).
Exit: close crosses back through the OPPOSITE side of the opening
range (the breakout round-tripped and failed).

This file contains ONLY strategy logic -- opening-range math lives in
app.indicators.opening_range and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.opening_range import OpeningRange
from app.strategies.registry import strategy_registry
from app.utils.sessions import minutes_since_session_start


@strategy_registry.register("orb_breakout")
class ORBBreakout(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="orb_breakout",
            display_name="Opening Range Breakout",
            description="Trades a clean close beyond the first N minutes' high/low, once the opening range has finished forming.",
            category="breakout",
            indicators_used=["opening_range"],
            default_params={"minutes": 15, "direction": "both"},
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        return OpeningRange().calculate(df, {"minutes": p["minutes"]})

    def _cols(self, p: dict[str, Any]) -> tuple[str, str]:
        m = p["minutes"]
        return f"or_high_{m}", f"or_low_{m}"

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        high_col, low_col = self._cols(p)
        or_high, or_low = df[high_col], df[low_col]
        close, prev_close = df["close"], df["close"].shift(1)
        window_closed = minutes_since_session_start(df.index) >= p["minutes"]

        long_mask = window_closed & (close > or_high) & (prev_close <= or_high)
        short_mask = window_closed & (close < or_low) & (prev_close >= or_low)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[long_mask] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[short_mask] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        high_col, low_col = self._cols(p)
        or_high, or_low = df[high_col], df[low_col]
        close, prev_close = df["close"], df["close"].shift(1)

        # Crossing events (not raw state) so a live, favorably-running
        # trade isn't closed just because price still sits beyond the
        # range it broke out of -- only the round-trip FAILURE fires.
        long_failed = (close < or_low) & (prev_close >= or_low)
        short_failed = (close > or_high) & (prev_close <= or_high)
        return long_failed | short_failed
