"""
RVOL Breakout.

A short-lookback price-range breakout, confirmed by a genuine burst of
relative volume rather than a trend-strength indicator like ADX --
day traders watch for volume precisely because a break on 3x normal
volume is far more likely to be real (institutional participation)
than the same break on a quiet, thin tape.

Entry: close breaks above the trailing N-bar high (long) or below the
trailing N-bar low (short), with relative volume above a threshold on
that same bar.
Exit: close crosses back through the midpoint of that same range.

This file contains ONLY strategy logic -- range/volume math lives in
app.indicators.rvol and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.rvol import RelativeVolume
from app.strategies.registry import strategy_registry


@strategy_registry.register("rvol_breakout")
class RVOLBreakout(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="rvol_breakout",
            display_name="RVOL Breakout",
            description="A short-lookback range breakout, taken only when relative volume confirms genuine participation behind the break.",
            category="breakout",
            indicators_used=["rvol"],
            default_params={"range_period": 12, "rvol_period": 20, "rvol_threshold": 1.5, "direction": "both"},
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = RelativeVolume().calculate(df, {"period": p["rvol_period"]})
        n = p["range_period"]
        out[f"range_high_{n}"] = out["high"].rolling(window=n, min_periods=n).max()
        out[f"range_low_{n}"] = out["low"].rolling(window=n, min_periods=n).min()
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        n = p["range_period"]
        range_high, range_low = df[f"range_high_{n}"], df[f"range_low_{n}"]
        rvol = df[f"rvol_{p['rvol_period']}"]
        close, prev_close = df["close"], df["close"].shift(1)
        volume_confirmed = rvol > p["rvol_threshold"]

        long_mask = volume_confirmed & (close > range_high.shift(1)) & (prev_close <= range_high.shift(2))
        short_mask = volume_confirmed & (close < range_low.shift(1)) & (prev_close >= range_low.shift(2))

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[long_mask] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[short_mask] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        n = p["range_period"]
        mid = (df[f"range_high_{n}"] + df[f"range_low_{n}"]) / 2
        close, prev_close = df["close"], df["close"].shift(1)
        prev_mid = mid.shift(1)
        return ((close > mid) != (prev_close > prev_mid)) & prev_mid.notna()
