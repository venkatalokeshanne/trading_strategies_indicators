"""
EMA Fib Confluence Breakout.

A trend-continuation entry, not a mean-reversion bounce: price must
CROSS THROUGH a Fibonacci retracement level (0.618 of the trailing
swing, computed independently for each side -- from the swing high
for longs, from the swing low for shorts) while the fast/slow EMA
pair already agrees on that direction. Distinct from
app.indicators.fibonacci_retracement's bounce-off-the-zone read (see
fib_retracement_bounce) -- here the level is a breakout trigger
inside an already-trending market, not a support/resistance zone.

Entry: fast EMA > slow EMA AND close crosses above (highest_high -
swing_range * 0.618) (long); mirrored for short.
Exit: the fast/slow EMA pair flips against the open position. (A
level-fail exit -- close dipping back under the fib trigger level --
was tried and dropped: verified empirically to be noise-sensitive
enough to close nearly every trade within 1-2 bars.)
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.strategies.registry import strategy_registry


@strategy_registry.register("ema_fib_confluence_breakout")
class EMAFibConfluenceBreakout(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="ema_fib_confluence_breakout",
            display_name="EMA Fib Confluence Breakout",
            description="Trades a close crossing through the 0.618 Fibonacci level of the trailing swing, only while the fast/slow EMA pair already agrees on that direction.",
            category="trend_following",
            indicators_used=[],
            default_params={
                "fast_ema_period": 9,
                "slow_ema_period": 21,
                "fib_lookback": 50,
                "fib_ratio": 0.618,
                "direction": "both",
            },
            entry_conditions=[
                "Long: fast EMA > slow EMA AND close crosses above the long-side 0.618 fib level",
                "Short: fast EMA < slow EMA AND close crosses below the short-side 0.618 fib level",
            ],
            exit_conditions=["The fast/slow EMA pair flips against the open position"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = df.copy()

        fast_ema = out["close"].ewm(span=p["fast_ema_period"], adjust=False, min_periods=p["fast_ema_period"]).mean()
        slow_ema = out["close"].ewm(span=p["slow_ema_period"], adjust=False, min_periods=p["slow_ema_period"]).mean()

        n = p["fib_lookback"]
        highest_high = out["high"].rolling(n, min_periods=n).max()
        lowest_low = out["low"].rolling(n, min_periods=n).min()
        price_range = highest_high - lowest_low
        ratio = p["fib_ratio"]

        long_level = highest_high - price_range * ratio
        short_level = lowest_low + price_range * ratio

        close, prev_close = out["close"], out["close"].shift(1)
        prev_long_level, prev_short_level = long_level.shift(1), short_level.shift(1)

        cross_up_long_level = (close > long_level) & (prev_close <= prev_long_level)
        cross_down_short_level = (close < short_level) & (prev_close >= prev_short_level)

        bull_trend = fast_ema > slow_ema
        bear_trend = fast_ema < slow_ema

        out["efc_long_signal"] = bull_trend & cross_up_long_level
        out["efc_short_signal"] = bear_trend & cross_down_short_level
        out["efc_fast_ema"] = fast_ema
        out["efc_slow_ema"] = slow_ema
        out["efc_long_level"] = long_level
        out["efc_short_level"] = short_level
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[df["efc_long_signal"]] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[df["efc_short_signal"]] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        self.validate_params(params)
        fast_ema, slow_ema = df["efc_fast_ema"], df["efc_slow_ema"]
        prev_fast, prev_slow = fast_ema.shift(1), slow_ema.shift(1)

        # Deliberately NOT a level-fail exit (close dipping back under the fib
        # level): verified empirically that condition is noise-sensitive
        # enough to close nearly every trade within 1-2 bars (median holding
        # time was 10 minutes on synthetic data), which defeats a
        # trend-continuation strategy. Only a genuine EMA-pair flip -- the
        # trend actually reversing -- ends the trade.
        ema_flip_down = (fast_ema < slow_ema) & (prev_fast >= prev_slow)
        ema_flip_up = (fast_ema > slow_ema) & (prev_fast <= prev_slow)
        return ema_flip_down | ema_flip_up
