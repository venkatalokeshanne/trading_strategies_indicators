"""
VWAP Reversion.

Session VWAP is the volume-weighted "fair value" for the day; most
intraday participants (especially institutions working large orders)
trade around it. When price stretches an unusually large distance from
VWAP (measured in ATRs, so it scales with each ticker's own
volatility), that stretch tends to snap back toward the anchor.

Entry: close is more than N ATRs above VWAP (short, fade the
overextension) or below VWAP (long).
Exit: close crosses back through VWAP (reversion complete).

This file contains ONLY strategy logic -- VWAP/ATR math lives in
app.indicators.vwap / app.indicators.atr and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.atr import ATR
from app.indicators.vwap import VWAP
from app.strategies.registry import strategy_registry


@strategy_registry.register("vwap_reversion")
class VWAPReversion(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="vwap_reversion",
            display_name="VWAP Reversion",
            description="Fades overextensions away from session VWAP, measured in ATRs, back toward the day's volume-weighted fair value.",
            category="mean_reversion",
            indicators_used=["vwap", "atr"],
            default_params={"atr_period": 14, "stretch_atr_multiple": 2.0, "direction": "both"},
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = VWAP().calculate(df, {})
        out = ATR().calculate(out, {"period": p["atr_period"]})
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        vwap, atr = df["vwap"], df[f"atr_{p['atr_period']}"]
        close = df["close"]
        stretch = p["stretch_atr_multiple"] * atr

        long_mask = close < (vwap - stretch)
        short_mask = close > (vwap + stretch)

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
