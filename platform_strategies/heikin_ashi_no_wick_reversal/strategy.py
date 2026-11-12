"""
Heikin Ashi No-Wick Reversal.

After a Heikin Ashi color flip (bearish to bullish, or vice versa),
waits for the FIRST subsequent candle in the new direction that also
has no wick on the "wrong" side (a bullish candle with no bottom wick,
or a bearish candle with no top wick) -- read as strong, uncontested
momentum confirming the reversal, rather than trading the flip itself
which can whipsaw.

The source script runs this on a fixed signal timeframe via
request.security regardless of the chart's own timeframe -- this
version computes Heikin Ashi directly from whatever timeframe it's
given instead, so it works at any interval.

Entry: Long on the first no-bottom-wick bullish HA candle after a
bearish-to-bullish flip. Short is the mirror image.
Exit: the next opposite-direction no-wick reversal signal.

This file contains ONLY strategy logic -- Heikin Ashi math lives in
app.indicators.heikinashicandles and is reused as-is.
"""

from typing import Any

import numpy as np
import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.heikinashicandles import HeikinAshiCandles
from app.strategies.registry import strategy_registry


@strategy_registry.register("heikin_ashi_no_wick_reversal")
class HeikinAshiNoWickReversal(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="heikin_ashi_no_wick_reversal",
            display_name="Heikin Ashi No-Wick Reversal",
            description="After a Heikin Ashi color flip, waits for the first no-wick candle in the new direction as a strong-momentum confirmation.",
            category="price_action",
            indicators_used=["heikinashicandles"],
            default_params={"direction": "both"},
            entry_conditions=[
                "Long: first no-bottom-wick bullish HA candle after a bearish-to-bullish flip",
                "Short: first no-top-wick bearish HA candle after a bullish-to-bearish flip",
            ],
            exit_conditions=["The next opposite-direction no-wick reversal signal"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        self.validate_params(params)
        out = HeikinAshiCandles().calculate(df, {})

        ha_open, ha_high = out["ha_open"].to_numpy(), out["ha_high"].to_numpy()
        ha_low, ha_close = out["ha_low"].to_numpy(), out["ha_close"].to_numpy()
        length = len(out)

        long_signal = np.zeros(length, dtype=bool)
        short_signal = np.zeros(length, dtype=bool)
        waiting_bull = False
        waiting_bear = False
        prev_bull = None
        prev_bear = None
        for i in range(length):
            if np.isnan(ha_open[i]):
                continue
            bull = ha_close[i] > ha_open[i]
            bear = ha_close[i] < ha_open[i]

            if prev_bull is not None:
                if bull and prev_bear:
                    waiting_bull, waiting_bear = True, False
                elif bear and prev_bull:
                    waiting_bear, waiting_bull = True, False

            no_bottom_wick = ha_low[i] == ha_open[i]
            no_top_wick = ha_high[i] == ha_open[i]

            if waiting_bull and bull and no_bottom_wick:
                long_signal[i] = True
                waiting_bull = False
            if waiting_bear and bear and no_top_wick:
                short_signal[i] = True
                waiting_bear = False

            prev_bull, prev_bear = bull, bear

        out["ha_no_wick_long"] = long_signal
        out["ha_no_wick_short"] = short_signal
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[df["ha_no_wick_long"]] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[df["ha_no_wick_short"]] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        return df["ha_no_wick_long"] | df["ha_no_wick_short"]
