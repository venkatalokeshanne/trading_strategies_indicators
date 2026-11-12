"""
Market Structure BOS.

Trades Break of Structure continuations: the indicator already
distinguishes a BOS (trend-continuation break) from a CHoCH (trend-
reversal break), so entries trade BOS in whichever direction price
just broke to, and CHoCH is the natural exit -- it means the market's
character just flipped against whatever position that break direction
implied.

Entry: a BOS fires and the break was to a new local high (long) or new
local low (short) over a trailing confirmation window.
Exit: a CHoCH fires (trend character changed).

This file contains ONLY strategy logic -- BOS/CHoCH detection lives in
app.indicators.market_structure and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.market_structure import MarketStructure
from app.strategies.registry import strategy_registry


@strategy_registry.register("market_structure_bos")
class MarketStructureBOS(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="market_structure_bos",
            display_name="Market Structure BOS",
            description="Trades Break of Structure continuations in whichever direction price just broke; exits on Change of Character.",
            category="price_action",
            indicators_used=["market_structure"],
            default_params={"swing_range": 5, "direction_lookback": 10, "direction": "both"},
            live_caution=(
                "A swing point isn't confirmed until swing_range bars after it forms, so a BOS entry "
                "is structurally several bars behind the actual turn -- real fills will typically land "
                "later and worse than the backtest, which assumes instant action the moment it confirms."
            ),
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        return MarketStructure().calculate(df, {"swing_range": p["swing_range"]})

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        bos = df["market_structure_bos"]
        close = df["close"]
        lookback = p["direction_lookback"]

        prior_max = close.shift(1).rolling(window=lookback, min_periods=lookback).max()
        prior_min = close.shift(1).rolling(window=lookback, min_periods=lookback).min()

        long_mask = bos & (close > prior_max)
        short_mask = bos & (close < prior_min)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[long_mask] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[short_mask] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        self.validate_params(params)
        return df["market_structure_choch"]
