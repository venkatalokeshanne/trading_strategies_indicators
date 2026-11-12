"""
Prior Day High/Low Breakout.

The most classic level-based day-trading strategy there is: a clean
close beyond yesterday's high or low is traded as a breakout in that
direction, on the read that the prior session's range has already
absorbed a full day of order flow, so breaking past its extremes
signals genuine new-session pressure rather than noise.

Entry: close crosses above the prior session's high (long); close
crosses below the prior session's low (short).
Exit: close crosses back through the OPPOSITE prior-session extreme --
i.e. the breakout fully round-tripped back through the whole prior
range and failed.

This file contains ONLY strategy logic -- the prior-day high/low
derivation is a trivial one-session shift, the same pattern already
used inline by app.indicators.camarilla_pivots / demark_pivots /
pivot_points, not a duplicated indicator.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.strategies.registry import strategy_registry


@strategy_registry.register("prior_day_hl_breakout")
class PriorDayHLBreakout(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="prior_day_hl_breakout",
            display_name="Prior Day High/Low Breakout",
            description="Trades a clean close beyond yesterday's high or low as a breakout in that direction.",
            category="breakout",
            indicators_used=[],
            default_params={"direction": "both"},
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        self.validate_params(params)
        out = df.copy()
        session_date = pd.Series(out.index.date, index=out.index)
        daily_high = out["high"].groupby(session_date).transform("max")
        daily_low = out["low"].groupby(session_date).transform("min")
        per_session_high = daily_high.groupby(session_date).first().shift(1)
        per_session_low = daily_low.groupby(session_date).first().shift(1)
        out["prior_day_high"] = session_date.map(per_session_high)
        out["prior_day_low"] = session_date.map(per_session_low)
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        prior_high, prior_low = df["prior_day_high"], df["prior_day_low"]
        close, prev_close = df["close"], df["close"].shift(1)

        long_mask = (close > prior_high) & (prev_close <= prior_high)
        short_mask = (close < prior_low) & (prev_close >= prior_low)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[long_mask] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[short_mask] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        self.validate_params(params)
        prior_high, prior_low = df["prior_day_high"], df["prior_day_low"]
        close, prev_close = df["close"], df["close"].shift(1)

        long_failed = (close < prior_low) & (prev_close >= prior_low)
        short_failed = (close > prior_high) & (prev_close <= prior_high)
        return long_failed | short_failed
