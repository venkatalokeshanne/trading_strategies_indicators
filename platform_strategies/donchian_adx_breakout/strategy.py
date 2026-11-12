"""
Donchian ADX Breakout.

A classic turtle-style channel breakout, gated by ADX so it only fires
when the market is actually capable of trending -- the single biggest
failure mode of plain breakout systems on intraday bars is getting
chopped up inside a range that never had real directional strength
behind it.

Entry: close breaks above the trailing Donchian high (long) or below
the trailing Donchian low (short), with ADX above a minimum threshold.
Exit: close crosses back through the Donchian midline.

This file contains ONLY strategy logic -- Donchian/ADX math lives in
app.indicators.donchian / app.indicators.adx and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.adx import ADX
from app.indicators.donchian import Donchian
from app.strategies.registry import strategy_registry


@strategy_registry.register("donchian_adx_breakout")
class DonchianADXBreakout(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="donchian_adx_breakout",
            display_name="Donchian ADX Breakout",
            description="Donchian channel breakout, only taken when ADX confirms the market has genuine trend strength behind it.",
            category="breakout",
            indicators_used=["donchian", "adx"],
            default_params={"donchian_period": 20, "adx_period": 14, "adx_threshold": 25.0, "direction": "both"},
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = Donchian().calculate(df, {"period": p["donchian_period"]})
        out = ADX().calculate(out, {"period": p["adx_period"]})
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        n = p["donchian_period"]
        # Donchian's own upper/lower are rolling windows INCLUDING the
        # current bar, so a raw close-vs-upper compare can never fire
        # (upper >= today's own high >= close). Shift by 1 to compare
        # against the trailing channel as of the PRIOR bar instead.
        prior_upper = df[f"donchian_upper_{n}"].shift(1)
        prior_lower = df[f"donchian_lower_{n}"].shift(1)
        adx = df[f"adx_{p['adx_period']}"]
        close, prev_close = df["close"], df["close"].shift(1)
        strong_trend = adx > p["adx_threshold"]

        long_mask = strong_trend & (close > prior_upper) & (prev_close <= prior_upper.shift(1))
        short_mask = strong_trend & (close < prior_lower) & (prev_close >= prior_lower.shift(1))

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[long_mask] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[short_mask] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        n = p["donchian_period"]
        mid = df[f"donchian_mid_{n}"]
        close, prev_close = df["close"], df["close"].shift(1)
        prev_mid = mid.shift(1)
        return ((close > mid) != (prev_close > prev_mid)) & prev_mid.notna()
