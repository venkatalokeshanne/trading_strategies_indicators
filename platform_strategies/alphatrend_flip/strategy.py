"""
AlphaTrend Flip.

Trades AlphaTrend's own trend flips directly -- the same buySignalk /
sellSignalk crossover(AlphaTrend, AlphaTrend[2]) / crossunder(...) the
original Pine script plots as BUY/SELL labels. Comparing the line
against its own value 2 bars back (rather than 1) is deliberate in the
source indicator -- it keeps a single-bar wiggle in the ratchet from
firing a flip on its own.

Entry: AlphaTrend crosses above (long) / below (short) its own value
2 bars back, filtered by a longer-period SMA so only flips that agree
with the prevailing trend get traded (on by default -- see
trend_filter_period below).
Exit: the next crossover in the opposite direction.

Why the trend filter: backtesting this signal on IONQ showed its
losers ran much longer and larger than its winners (no stop-loss to
cut a bad entry short) AND that whichever side (long or short) matched
the prevailing multi-week trend was consistently the profitable one --
the counter-trend side lost money in every window tested, including
two windows with opposite trends. A FIXED direction_filter would just
curve-fit to whichever trend was active in the window it was tuned on;
this filter instead re-evaluates the prevailing trend every bar (price
vs. its own trailing SMA) so it adapts as the trend changes, rather
than hard-coding a side.

This file contains ONLY strategy logic -- AlphaTrend/SMA math lives in
app.indicators and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.alphatrend import AlphaTrend
from app.indicators.sma import SMA
from app.strategies.registry import strategy_registry


@strategy_registry.register("alphatrend_flip")
class AlphaTrendFlip(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="alphatrend_flip",
            display_name="AlphaTrend Flip",
            description="Trades AlphaTrend's own crossover/crossunder against its value 2 bars back, filtered to trade only with the prevailing trend.",
            category="trend_following",
            indicators_used=["alphatrend", "sma"],
            default_params={
                "period": 14,
                "multiplier": 1.0,
                "source": "close",
                "no_volume_data": False,
                "direction": "both",
                "trend_filter_period": 100,
            },
            entry_conditions=[
                "Long: AlphaTrend crosses above its own value 2 bars back, AND close is above its trend_filter_period SMA",
                "Short: AlphaTrend crosses below its own value 2 bars back, AND close is below its trend_filter_period SMA",
                "(set trend_filter_period to 0/None to trade every flip unfiltered, matching the raw Pine signal)",
            ],
            exit_conditions=["The next AlphaTrend crossover in the opposite direction"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = AlphaTrend().calculate(
            df,
            {
                "period": p["period"],
                "multiplier": p["multiplier"],
                "source": p["source"],
                "no_volume_data": p["no_volume_data"],
            },
        )
        if p["trend_filter_period"]:
            out = SMA().calculate(out, {"period": p["trend_filter_period"], "source": "close"})
        return out

    def _col(self, p: dict[str, Any]) -> str:
        return f"alphatrend_{p['period']}_{p['multiplier']}"

    def _state(self, df: pd.DataFrame, params: dict[str, Any]) -> tuple[pd.Series, pd.Series]:
        """(is_above, was_above) -- whether AlphaTrend sits above its own
        value 2 bars back, this bar and the bar before. A NaN on either
        side of `>` compares as False in pandas, so warmup bars never
        register as a cross either way."""
        p = self.validate_params(params)
        line = df[self._col(p)]
        lagged = line.shift(2)
        is_above = line > lagged
        was_above = is_above.shift(1).fillna(False).infer_objects(copy=False).astype(bool)
        return is_above, was_above

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        is_above, was_above = self._state(df, p)
        cross_up = is_above & ~was_above
        cross_down = ~is_above & was_above

        if p["trend_filter_period"]:
            trend_sma = df[f"sma_{p['trend_filter_period']}"]
            has_trend = trend_sma.notna()
            uptrend = (df["close"] > trend_sma) & has_trend
            downtrend = (df["close"] < trend_sma) & has_trend
            cross_up = cross_up & uptrend
            cross_down = cross_down & downtrend

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[cross_up] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[cross_down] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        is_above, was_above = self._state(df, params)
        return is_above != was_above
