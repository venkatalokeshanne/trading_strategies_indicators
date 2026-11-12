"""
EMA Cross Volume RSI Band.

A fast/slow EMA cross gated by volume confirmation (above its own
short recent average) AND RSI sitting inside a single shared band
(e.g. 50-70) for EITHER direction -- an unusual, deliberately
asymmetric gate versus the more common "overbought caps longs /
oversold caps shorts" split (see ema_cross_rsi_filtered): the SAME
"healthy-bullish-momentum" RSI zone must hold whichever way the EMAs
just crossed, which also biases the whole system toward being pickier
about shorts (a bearish cross needs RSI still sitting in a
bullish-momentum band, a narrower window to catch).

Entry: fast EMA crosses above slow EMA (long) or below it (short), at
the moment volume confirms and RSI is inside [rsi_band_low,
rsi_band_high].
Exit: the opposite-direction cross+confluence event.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.ema import EMA
from app.indicators.rsi import RSI
from app.strategies.registry import strategy_registry


@strategy_registry.register("ema_cross_volume_rsi_band")
class EMACrossVolumeRSIBand(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="ema_cross_volume_rsi_band",
            display_name="EMA Cross Volume RSI Band",
            description="An EMA cross, gated by a volume confirmation and a single shared RSI band that must hold for either direction.",
            category="trend_following",
            indicators_used=["ema", "rsi"],
            default_params={
                "fast_period": 9,
                "slow_period": 26,
                "rsi_period": 14,
                "rsi_band_low": 50.0,
                "rsi_band_high": 70.0,
                "volume_lookback_bars": 3,
                "volume_multiplier": 1.0,
            },
            entry_conditions=[
                "Long: fast EMA crosses above slow EMA",
                "Short: fast EMA crosses below slow EMA",
                "Either: RSI(rsi_period) within [rsi_band_low, rsi_band_high] AND volume > volume_multiplier * average volume of the prior volume_lookback_bars",
            ],
            exit_conditions=["The opposite-direction cross+confluence event"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = EMA().calculate(df, {"period": p["fast_period"], "source": "close"})
        out = EMA().calculate(out, {"period": p["slow_period"], "source": "close"})
        out = RSI().calculate(out, {"period": p["rsi_period"], "source": "close"})

        fast, slow = out[f"ema_{p['fast_period']}"], out[f"ema_{p['slow_period']}"]
        prev_fast, prev_slow = fast.shift(1), slow.shift(1)
        cross_up = (fast > slow) & (prev_fast <= prev_slow)
        cross_down = (fast < slow) & (prev_fast >= prev_slow)

        rsi = out[f"rsi_{p['rsi_period']}"]
        rsi_ok = (rsi > p["rsi_band_low"]) & (rsi < p["rsi_band_high"])
        avg_vol = out["volume"].shift(1).rolling(window=p["volume_lookback_bars"], min_periods=p["volume_lookback_bars"]).mean()
        high_vol = out["volume"] >= avg_vol * p["volume_multiplier"]

        out["ema_cross_vol_long"] = cross_up & rsi_ok & high_vol
        out["ema_cross_vol_short"] = cross_down & rsi_ok & high_vol
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        self.validate_params(params)
        entries = pd.Series(None, index=df.index, dtype=object)
        entries[df["ema_cross_vol_long"]] = TradeDirection.LONG
        entries[df["ema_cross_vol_short"]] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        self.validate_params(params)
        return df["ema_cross_vol_long"] | df["ema_cross_vol_short"]
