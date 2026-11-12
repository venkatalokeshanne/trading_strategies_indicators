"""
ADX Compression Flash Breakout.

Waits for ADX to drop below a low threshold (a "flash" -- trend
strength has compressed, the market has gone quiet) and then fires a
directional signal the bar AFTER ADX re-expands back above either
directional line (+DI or -DI), taking direction from whichever DI is
on top at that moment. Reads compression-then-expansion as the setup,
rather than trading the compression itself.

Entry: one bar after ADX crosses back above +DI or -DI following a
flash (ADX crossing below adx_threshold) -- long if +DI > -DI at that
moment, short if -DI > +DI.
Exit: the opposite-direction signal.
"""

from typing import Any

import numpy as np
import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators._shared import directional_movement, wilders_smooth
from app.strategies.registry import strategy_registry


@strategy_registry.register("adx_compression_flash_breakout")
class ADXCompressionFlashBreakout(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="adx_compression_flash_breakout",
            display_name="ADX Compression Flash Breakout",
            description="Waits for ADX to compress below a low threshold, then fires a directional signal one bar after it expands back through +DI or -DI.",
            category="momentum",
            indicators_used=[],
            default_params={"adx_period": 14, "adx_threshold": 13.0, "direction": "both"},
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = df.copy()
        n = p["adx_period"]

        dm = directional_movement(out, n)
        plus_di, minus_di = dm["plus_di"], dm["minus_di"]
        di_sum = (plus_di + minus_di).replace(0, np.nan)
        dx = 100 * (plus_di - minus_di).abs() / di_sum
        adx = wilders_smooth(dx, n)

        adx_arr = adx.to_numpy()
        plus_arr = plus_di.to_numpy()
        minus_arr = minus_di.to_numpy()
        length = len(out)

        long_signal = np.zeros(length, dtype=bool)
        short_signal = np.zeros(length, dtype=bool)
        flash_active = False
        flash_ended_prev = False

        for i in range(length):
            if np.isnan(adx_arr[i]) or np.isnan(plus_arr[i]) or np.isnan(minus_arr[i]):
                continue

            if flash_ended_prev:
                if plus_arr[i] > minus_arr[i]:
                    long_signal[i] = True
                else:
                    short_signal[i] = True
                flash_ended_prev = False

            cross_below = i > 0 and adx_arr[i] < p["adx_threshold"] <= adx_arr[i - 1]
            if cross_below:
                flash_active = True

            flash_ended = False
            if flash_active and i > 0:
                cross_above_plus = adx_arr[i] > plus_arr[i] and adx_arr[i - 1] <= plus_arr[i - 1]
                cross_above_minus = adx_arr[i] > minus_arr[i] and adx_arr[i - 1] <= minus_arr[i - 1]
                if cross_above_plus or cross_above_minus:
                    flash_ended = True

            if flash_ended:
                flash_active = False
                flash_ended_prev = True

        out["adx_flash_long"] = long_signal
        out["adx_flash_short"] = short_signal
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[df["adx_flash_long"]] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[df["adx_flash_short"]] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        return df["adx_flash_long"] | df["adx_flash_short"]
