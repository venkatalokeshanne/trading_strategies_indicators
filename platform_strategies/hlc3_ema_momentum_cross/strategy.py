"""
HLC3 EMA Momentum Cross.

A fast EMA cross variant that trades hlc3 (the typical price, less
noisy than a raw close) against its own EMA, confirmed by short-term
price momentum: only buy the bullish cross while price has actually
been rising over the last few bars, only sell the bearish cross while
it's been falling. Distinct from this platform's other EMA cross
strategies (ema_cross reverses on either close/EMA cross with no
momentum confirmation; ema_cross_rsi_filtered filters by RSI level,
not price momentum; sma_cross uses SMA and a fixed pairing).

Entry: hlc3 crosses above its EMA AND hlc3 has risen over the
momentum lookback window (long); mirrored for short.
Exit: the opposite-direction cross+momentum signal.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.strategies.registry import strategy_registry


@strategy_registry.register("hlc3_ema_momentum_cross")
class HLC3EMAMomentumCross(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="hlc3_ema_momentum_cross",
            display_name="HLC3 EMA Momentum Cross",
            description="Trades hlc3 crossing its own EMA, confirmed by short-term price momentum in the same direction.",
            category="trend_following",
            indicators_used=[],
            default_params={"ema_period": 9, "momentum_lookback": 5, "direction": "both"},
            entry_conditions=[
                "Long: hlc3 crosses above its EMA AND hlc3 rose over the momentum lookback",
                "Short: hlc3 crosses below its EMA AND hlc3 fell over the momentum lookback",
            ],
            exit_conditions=["The opposite-direction cross+momentum signal"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = df.copy()
        hlc3 = (out["high"] + out["low"] + out["close"]) / 3
        ema = hlc3.ewm(span=p["ema_period"], adjust=False, min_periods=p["ema_period"]).mean()
        momentum = hlc3.diff(p["momentum_lookback"])

        prev_hlc3, prev_ema = hlc3.shift(1), ema.shift(1)
        cross_up = (hlc3 > ema) & (prev_hlc3 <= prev_ema)
        cross_down = (hlc3 < ema) & (prev_hlc3 >= prev_ema)

        out["hlc3_ema_mom_long"] = cross_up & (momentum > 0)
        out["hlc3_ema_mom_short"] = cross_down & (momentum < 0)
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[df["hlc3_ema_mom_long"]] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[df["hlc3_ema_mom_short"]] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        return df["hlc3_ema_mom_long"] | df["hlc3_ema_mom_short"]
