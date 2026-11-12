"""
Turtle Donchian System.

The classic Turtle Trading dual-channel breakout: a WIDER Donchian
channel triggers entries, a NARROWER one triggers exits -- the two
different lengths mean a trade gets more room to run before the
system gives it back than it needed to get in, unlike a single-channel
system where entry and exit sensitivity are forced to match. An
optional long-period EMA trend filter only allows longs above it and
shorts below it. Distinct from donchian_adx_breakout (single channel,
ADX-gated, midline exit).

Entry: close breaks above the trailing entry-channel high (long) or
below the trailing entry-channel low (short), with price on the
trend-filter's matching side if enabled.
Exit: close breaks back through the trailing (narrower) exit channel.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.donchian import Donchian
from app.indicators.ema import EMA
from app.strategies.registry import strategy_registry


@strategy_registry.register("turtle_donchian_system")
class TurtleDonchianSystem(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="turtle_donchian_system",
            display_name="Turtle Donchian System",
            description="Classic Turtle Trading dual-channel breakout -- a wider channel triggers entries, a narrower one triggers exits, optionally trend-filtered by a long EMA.",
            category="breakout",
            indicators_used=["donchian", "ema"],
            default_params={
                "entry_period": 20,
                "exit_period": 10,
                "use_trend_filter": True,
                "trend_ema_period": 200,
                "direction": "both",
            },
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = Donchian().calculate(df, {"period": p["entry_period"]})
        out = Donchian().calculate(out, {"period": p["exit_period"]})
        if p["use_trend_filter"]:
            out = EMA().calculate(out, {"period": p["trend_ema_period"], "source": "close"})
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        entry_upper = df[f"donchian_upper_{p['entry_period']}"].shift(1)
        entry_lower = df[f"donchian_lower_{p['entry_period']}"].shift(1)
        close, prev_close = df["close"], df["close"].shift(1)

        long_mask = (close > entry_upper) & (prev_close <= entry_upper.shift(1))
        short_mask = (close < entry_lower) & (prev_close >= entry_lower.shift(1))

        if p["use_trend_filter"]:
            trend = df[f"ema_{p['trend_ema_period']}"]
            long_mask = long_mask & (close > trend)
            short_mask = short_mask & (close < trend)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[long_mask] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[short_mask] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        exit_upper = df[f"donchian_upper_{p['exit_period']}"].shift(1)
        exit_lower = df[f"donchian_lower_{p['exit_period']}"].shift(1)
        close, prev_close = df["close"], df["close"].shift(1)

        long_exit = (close < exit_lower) & (prev_close >= exit_lower.shift(1))
        short_exit = (close > exit_upper) & (prev_close <= exit_upper.shift(1))
        return long_exit | short_exit
