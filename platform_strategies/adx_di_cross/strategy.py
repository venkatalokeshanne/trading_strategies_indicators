"""
ADX/DMI Cross.

Wilder's own directional system used as its designer intended: +DI
crossing above -DI (or vice versa) marks a directional shift, and
requiring ADX itself above a threshold at that moment filters out the
crosses that happen during dead, directionless chop.

Entry: +DI crosses above -DI with ADX above threshold (long); -DI
crosses above +DI with ADX above threshold (short).
Exit: the opposite DI cross.

This file contains ONLY strategy logic -- ADX/+DI/-DI math lives in
app.indicators.adx / plus_di / minus_di and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.adx import ADX
from app.indicators.minus_di import MinusDI
from app.indicators.plus_di import PlusDI
from app.strategies.registry import strategy_registry


@strategy_registry.register("adx_di_cross")
class ADXDICross(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="adx_di_cross",
            display_name="ADX/DMI Cross",
            description="+DI/-DI crossovers, taken only when ADX confirms the trend has real strength behind it.",
            category="trend_following",
            indicators_used=["adx", "plus_di", "minus_di"],
            default_params={"period": 14, "adx_threshold": 20.0, "direction": "both"},
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = ADX().calculate(df, {"period": p["period"]})
        out = PlusDI().calculate(out, {"period": p["period"]})
        out = MinusDI().calculate(out, {"period": p["period"]})
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        n = p["period"]
        plus_di, minus_di, adx = df[f"plus_di_{n}"], df[f"minus_di_{n}"], df[f"adx_{n}"]
        prev_plus, prev_minus = plus_di.shift(1), minus_di.shift(1)
        strong_trend = adx > p["adx_threshold"]

        cross_up = strong_trend & (plus_di > minus_di) & (prev_plus <= prev_minus)
        cross_down = strong_trend & (plus_di < minus_di) & (prev_plus >= prev_minus)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[cross_up] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[cross_down] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        n = p["period"]
        plus_di, minus_di = df[f"plus_di_{n}"], df[f"minus_di_{n}"]
        prev_plus, prev_minus = plus_di.shift(1), minus_di.shift(1)
        return ((plus_di > minus_di) != (prev_plus > prev_minus)) & prev_plus.notna() & prev_minus.notna()
