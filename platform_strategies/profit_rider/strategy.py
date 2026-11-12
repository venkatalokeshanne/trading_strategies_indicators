"""
Profit Rider (Ultra Conservative).

A long-only EMA breakout with a volume-surge confirmation filter --
requires close to cross above its own trend EMA on volume well above
its rolling average (1.5x by default), so only breakouts with real
participation behind them qualify.

Exit is deliberately NOT a bar-level signal condition -- the source
script's own exit ("close < trailing ATR stop that only ever ratchets
up while in the trade") is per-trade, entry-anchored, position-aware
state, which is exactly what this platform's execution engine's own
trailing_stop_atr_multiple already computes (see
app.strategies.execution.simulate_trades) -- same ATR-multiple ratchet
logic, just owned by the engine instead of duplicated here. Because of
that, generate_exits() always returns False: THIS STRATEGY REQUIRES
execution.trailing_stop_atr_multiple TO BE SET to exit trades on
anything other than force_close_at_session_end. The source script's
own default is 2.5x ATR(14) -- pass trailing_stop_atr_multiple=2.5 and
atr_period=14 to match it exactly. It also has no forced end-of-day
close (a swing-style hold), so set force_close_at_session_end=false
too for a faithful replay; leaving it True (this platform's default)
turns every trade into an intraday-only version of the same strategy.

Entry: close crosses above its EMA(period) AND volume exceeds
volume_multiple x its own rolling average, only while flat.
Exit: none defined here -- provide execution.trailing_stop_atr_multiple
(and optionally force_close_at_session_end=false) when running this
strategy, or trades will only ever close at forced session end.

This file contains ONLY entry logic -- EMA/volume-average math lives
in app.indicators and is reused as-is; the trailing stop lives in the
execution engine and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.ema import EMA
from app.indicators.volume_average import VolumeAverage
from app.strategies.registry import strategy_registry


@strategy_registry.register("profit_rider")
class ProfitRider(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="profit_rider",
            display_name="Profit Rider (Ultra Conservative)",
            description="Long-only EMA breakout confirmed by a volume surge (1.5x its rolling average); relies on execution.trailing_stop_atr_multiple to exit -- see Info tab.",
            category="trend_following",
            indicators_used=["ema", "volume_average"],
            default_params={
                "ema_period": 20,
                "volume_period": 20,
                "volume_multiple": 1.5,
            },
            entry_conditions=[
                "Close crosses above its EMA(ema_period)",
                "Volume exceeds volume_multiple x its own rolling volume_period average",
                "Only while flat (long-only, one position at a time -- matches the source script)",
            ],
            exit_conditions=[
                "NONE defined by this strategy -- set execution.trailing_stop_atr_multiple "
                "(source default: 2.5x ATR(14)) to replicate the source script's ratcheting "
                "trailing-stop exit; without it, trades only close at forced session end.",
            ],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = EMA().calculate(df, {"period": p["ema_period"], "source": "close"})
        out = VolumeAverage().calculate(out, {"period": p["volume_period"]})
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        ema = df[f"ema_{p['ema_period']}"]
        prev_close, prev_ema = df["close"].shift(1), ema.shift(1)

        cross_up = (df["close"] > ema) & (prev_close <= prev_ema)
        volume_confirmed = df["volume"] > (df[f"volume_avg_{p['volume_period']}"] * p["volume_multiple"])

        entries = pd.Series(None, index=df.index, dtype=object)
        entries[cross_up & volume_confirmed] = TradeDirection.LONG
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        self.validate_params(params)
        return pd.Series(False, index=df.index)
