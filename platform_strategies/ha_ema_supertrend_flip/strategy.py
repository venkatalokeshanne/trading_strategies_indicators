"""
HA-EMA SuperTrend Flip.

A double-confirmation trend flip: EMA-smoothed Heikin-Ashi bars must
agree with SuperTrend's own direction before a flip counts as a
signal, filtering out flips where the two regimes momentarily
disagree. Distinct from this platform's other SuperTrend/HA
strategies (supertrend_flip has no HA confirmation at all;
heikin_ashi_no_wick_reversal uses raw HA wick shape, not an
EMA-smoothed HA trend regime).

Entry: EMA-smoothed HA trend turns bullish AND SuperTrend direction is
already bullish, on the first bar this combined regime activates
(long); mirrored for short.
Exit: the opposite-direction flip.
"""

from typing import Any

import numpy as np
import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.supertrend import SuperTrend
from app.strategies.registry import strategy_registry


@strategy_registry.register("ha_ema_supertrend_flip")
class HAEMASuperTrendFlip(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="ha_ema_supertrend_flip",
            display_name="HA-EMA SuperTrend Flip",
            description="Trades a trend flip only when an EMA-smoothed Heikin-Ashi trend regime and SuperTrend's own direction agree.",
            category="trend_following",
            indicators_used=["supertrend"],
            default_params={
                "ha_ema_period": 14,
                "ha_smooth_period": 2,
                "supertrend_period": 2,
                "supertrend_multiple": 2.0,
                "direction": "both",
            },
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = SuperTrend().calculate(df, {"period": p["supertrend_period"], "multiple": p["supertrend_multiple"]})

        hk_open = out["open"].ewm(span=p["ha_ema_period"], adjust=False, min_periods=p["ha_ema_period"]).mean()
        hk_close = out["close"].ewm(span=p["ha_ema_period"], adjust=False, min_periods=p["ha_ema_period"]).mean()
        hk_high = out["high"].ewm(span=p["ha_ema_period"], adjust=False, min_periods=p["ha_ema_period"]).mean()
        hk_low = out["low"].ewm(span=p["ha_ema_period"], adjust=False, min_periods=p["ha_ema_period"]).mean()
        hk_typical = (hk_open + hk_high + hk_low + hk_close) / 4

        n = len(out)
        hk_prev = np.full(n, np.nan)
        typical_arr = hk_typical.to_numpy()
        open_arr = hk_open.to_numpy()
        close_arr = hk_close.to_numpy()
        for i in range(n):
            if np.isnan(typical_arr[i]):
                continue
            if np.isnan(hk_prev[i - 1]) if i > 0 else True:
                hk_prev[i] = (open_arr[i] + close_arr[i]) / 2
            else:
                hk_prev[i] = (hk_prev[i - 1] + typical_arr[i - 1]) / 2

        hk_prev_s = pd.Series(hk_prev, index=out.index).ewm(
            span=p["ha_smooth_period"], adjust=False, min_periods=p["ha_smooth_period"]
        ).mean()
        hk_typical_smooth = hk_typical.ewm(span=p["ha_smooth_period"], adjust=False, min_periods=p["ha_smooth_period"]).mean()

        ha_bull = hk_prev_s < hk_typical_smooth
        ha_bear = hk_prev_s > hk_typical_smooth

        st_col = f"supertrend_direction_{p['supertrend_period']}_{p['supertrend_multiple']}"
        st_bull = out[st_col] == 1
        st_bear = out[st_col] == -1

        go_long = ha_bull & st_bull
        go_short = ha_bear & st_bear

        raw_state = pd.Series(np.nan, index=out.index)
        raw_state[go_long] = 1
        raw_state[go_short] = -1
        state = raw_state.ffill()
        prev_state = state.shift(1)

        out["ha_ema_st_long"] = (state == 1) & (prev_state != 1)
        out["ha_ema_st_short"] = (state == -1) & (prev_state != -1)
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[df["ha_ema_st_long"]] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[df["ha_ema_st_short"]] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        return df["ha_ema_st_long"] | df["ha_ema_st_short"]
