"""
VWAP Trend Pullback.

The trend-following complement to VWAP Reversion: when VWAP itself is
sloping in one direction (a genuine intraday trend, not just noise
around a flat anchor), a dip down to touch VWAP and reclaim it is
traded as a continuation entry -- buying the pullback in an uptrend,
selling the pullback in a downtrend -- rather than a reversal.

Entry: VWAP is higher than N bars ago (uptrend) and the bar's low
touches/dips below VWAP but closes back above it (long); mirrored for
a downtrend (short).
Exit: close crosses to the other side of VWAP (the pullback failed to
hold).

This file contains ONLY strategy logic -- VWAP math lives in
app.indicators.vwap and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.vwap import VWAP
from app.strategies.registry import strategy_registry


@strategy_registry.register("vwap_trend_pullback")
class VWAPTrendPullback(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="vwap_trend_pullback",
            display_name="VWAP Trend Pullback",
            description="Buys/sells a dip-and-reclaim of VWAP in the direction VWAP itself is already sloping.",
            category="trend_following",
            indicators_used=["vwap"],
            default_params={"slope_lookback": 10, "direction": "both"},
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        self.validate_params(params)
        return VWAP().calculate(df, {})

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        vwap = df["vwap"]
        high, low, close = df["high"], df["low"], df["close"]
        prior_vwap = vwap.shift(p["slope_lookback"])

        uptrend = vwap > prior_vwap
        downtrend = vwap < prior_vwap

        long_mask = uptrend & (low <= vwap) & (close > vwap)
        short_mask = downtrend & (high >= vwap) & (close < vwap)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[long_mask] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[short_mask] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        self.validate_params(params)
        vwap, close = df["vwap"], df["close"]
        prev_close, prev_vwap = close.shift(1), vwap.shift(1)
        return ((close > vwap) != (prev_close > prev_vwap)) & prev_vwap.notna()
