"""
Doji Breakout.

A doji (body small relative to its total wick length) marks a bar of
indecision; the next bar's close breaking above that doji's own high
(or below its low) is read as a breakout resolving that indecision.

The source script hardcodes a fixed 3-minute anchor timeframe via
request.security regardless of the chart's own timeframe -- this
version runs entirely on whatever timeframe it's given instead
(making it usable at any interval, not just as a fixed-3min overlay);
the underlying entry logic (does close break the PRIOR bar's doji
high/low) is otherwise unchanged. The source's per-trade label/line
drawing is not ported (visual only).

Entry: the prior bar was a doji AND close breaks above its high
(long) / below its low (short).
Exit: the next opposite-direction doji-breakout signal.

This file contains ONLY strategy logic -- all math is plain OHLC,
nothing composed from app.indicators.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.strategies.registry import strategy_registry


@strategy_registry.register("doji_breakout")
class DojiBreakout(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="doji_breakout",
            display_name="Doji Breakout",
            description="Prior bar was a doji; entry fires when close breaks above (long) or below (short) that doji's own high/low.",
            category="price_action",
            indicators_used=[],
            default_params={"body_to_wick_ratio": 0.2, "direction": "both"},
            entry_conditions=[
                "Long: the prior bar was a doji AND close breaks above that doji's high",
                "Short: the prior bar was a doji AND close breaks below that doji's low",
            ],
            exit_conditions=["The next opposite-direction doji-breakout signal"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = df.copy()
        body = (out["close"] - out["open"]).abs()
        upper_wick = out["high"] - out[["open", "close"]].max(axis=1)
        lower_wick = out[["open", "close"]].min(axis=1) - out["low"]
        total_wicks = upper_wick + lower_wick
        out["doji_breakout_is_doji"] = (body < total_wicks * p["body_to_wick_ratio"]) & (total_wicks > 0)
        return out

    def _signals(self, df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        prev_is_doji = df["doji_breakout_is_doji"].shift(1).fillna(False).infer_objects(copy=False).astype(bool)
        prev_high, prev_low = df["high"].shift(1), df["low"].shift(1)
        buy_signal = prev_is_doji & (df["close"] > prev_high)
        sell_signal = prev_is_doji & (df["close"] < prev_low)
        return buy_signal, sell_signal

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        buy_signal, sell_signal = self._signals(df)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[buy_signal] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[sell_signal] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        buy_signal, sell_signal = self._signals(df)
        return buy_signal | sell_signal
