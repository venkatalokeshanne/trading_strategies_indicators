"""
FVG BOS Confirmation.

Trades a Fair Value Gap only when it's structurally confirmed: a
bullish FVG is only tradeable if it formed within `fvg_expiry_bars`
bars AFTER a confirmed bullish Break of Structure (mirrored for
bearish) -- the BOS proves genuine directional intent already
happened before trusting the gap as a real supply/demand imbalance,
rather than trading any 3-bar gap in isolation. Distinct from
fvg_fill_continuation (trades any fresh FVG, no structural
precondition) and from confluence_order_block/order_block_retest
(order-block zones, not FVGs).

Entry: price retraces into a BOS-confirmed FVG zone and closes back
through its far edge, in the BOS's own direction.
Exit: price closes back through the OPPOSITE edge of that same gap
(the continuation failed).

This file contains ONLY strategy logic -- BOS/CHoCH detection lives in
app.indicators.market_structure and FVG detection in
app.indicators.fair_value_gap, both reused as-is.
"""

from typing import Any

import numpy as np
import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.fair_value_gap import FairValueGap
from app.indicators.market_structure import MarketStructure
from app.strategies.registry import strategy_registry


@strategy_registry.register("fvg_bos_confirmation")
class FVGBOSConfirmation(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="fvg_bos_confirmation",
            display_name="FVG BOS Confirmation",
            description="Trades a Fair Value Gap only when it formed shortly after a confirmed Break of Structure in the same direction, using the BOS as structural proof before trusting the gap.",
            category="price_action",
            indicators_used=["market_structure", "fair_value_gap"],
            default_params={"swing_range": 10, "fvg_expiry_bars": 20, "direction": "both"},
            live_caution=(
                "Trading a retrace into the gap needs a fill at a specific, often narrow price zone -- "
                "a backtest assumes a clean fill the instant price crosses it, but that's a real "
                "slippage/no-fill risk live that the backtested numbers don't account for."
            ),
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = MarketStructure().calculate(df, {"swing_range": p["swing_range"]})
        out = FairValueGap().calculate(out, {})

        bos = out["market_structure_bos"].to_numpy()
        close = out["close"].to_numpy()
        bull_top = out["fvg_bullish_top"].to_numpy()
        bull_bottom = out["fvg_bullish_bottom"].to_numpy()
        bear_top = out["fvg_bearish_top"].to_numpy()
        bear_bottom = out["fvg_bearish_bottom"].to_numpy()
        n = len(out)
        expiry = p["fvg_expiry_bars"]

        confirmed_bull_top = np.full(n, np.nan)
        confirmed_bull_bottom = np.full(n, np.nan)
        confirmed_bear_top = np.full(n, np.nan)
        confirmed_bear_bottom = np.full(n, np.nan)

        last_bull_bos_bar = -10**9
        last_bear_bos_bar = -10**9
        active_bull_top = active_bull_bottom = np.nan
        active_bull_expiry = -1
        active_bear_top = active_bear_bottom = np.nan
        active_bear_expiry = -1

        for i in range(n):
            if bos[i]:
                if close[i] > close[i - 1] if i > 0 else False:
                    last_bull_bos_bar = i
                else:
                    last_bear_bos_bar = i

            if not np.isnan(bull_top[i]) and (i - last_bull_bos_bar) <= expiry:
                active_bull_top, active_bull_bottom = bull_top[i], bull_bottom[i]
                active_bull_expiry = i + expiry
            if not np.isnan(bear_top[i]) and (i - last_bear_bos_bar) <= expiry:
                active_bear_top, active_bear_bottom = bear_top[i], bear_bottom[i]
                active_bear_expiry = i + expiry

            if i <= active_bull_expiry:
                confirmed_bull_top[i], confirmed_bull_bottom[i] = active_bull_top, active_bull_bottom
            if i <= active_bear_expiry:
                confirmed_bear_top[i], confirmed_bear_bottom[i] = active_bear_top, active_bear_bottom

        out["fvg_bos_bull_top"] = confirmed_bull_top
        out["fvg_bos_bull_bottom"] = confirmed_bull_bottom
        out["fvg_bos_bear_top"] = confirmed_bear_top
        out["fvg_bos_bear_bottom"] = confirmed_bear_bottom
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        bull_top, bull_bottom = df["fvg_bos_bull_top"], df["fvg_bos_bull_bottom"]
        bear_top, bear_bottom = df["fvg_bos_bear_top"], df["fvg_bos_bear_bottom"]
        low, high, close = df["low"], df["high"], df["close"]

        long_mask = (low <= bull_top) & (low >= bull_bottom) & (close > bull_top)
        short_mask = (high >= bear_bottom) & (high <= bear_top) & (close < bear_bottom)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[long_mask] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[short_mask] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        self.validate_params(params)
        bull_bottom, bear_top = df["fvg_bos_bull_bottom"], df["fvg_bos_bear_top"]
        close = df["close"]
        long_invalidated = close < bull_bottom
        short_invalidated = close > bear_top
        return long_invalidated | short_invalidated
