"""
EMA Hammer Rejection.

A wick-rejection continuation pattern, gated by an EMA trend filter:
a prior candle with a long wick against the trend (a red candle with
a long upper wick while price is above the EMA, or a green candle
with a long lower wick while below it) followed by a same-direction
confirmation candle that closes decisively through the prior candle's
extreme -- read as a rejected pullback resuming the trend, not a
reversal. An alternate looser trigger fires on a smaller "coverage"
close (reclaiming most, not all, of the prior candle's range) instead
of a full close-beyond-the-extreme.

Entry: prior candle is a rejection wick against the trend AND both
candles sit on the EMA's trend side AND the confirmation candle
closes beyond the prior extreme (or the coverage threshold).
Exit: the opposite-direction signal.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.strategies.registry import strategy_registry


@strategy_registry.register("ema_hammer_rejection")
class EMAHammerRejection(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="ema_hammer_rejection",
            display_name="EMA Hammer Rejection",
            description="A wick-rejection continuation pattern gated by an EMA trend filter: a rejection wick against the trend, then a confirmation candle closing through the prior extreme.",
            category="price_action",
            indicators_used=[],
            default_params={
                "ema_period": 21,
                "wick_multiplier": 1.5,
                "coverage_pct": 60.0,
                "direction": "both",
            },
            entry_conditions=[
                "Long: prior red candle's upper wick >= wick_multiplier * its body, both candles above the EMA, and close > prior high (or >= coverage_pct of the way through the prior red candle's range)",
                "Short: prior green candle's lower wick >= wick_multiplier * its body, both candles below the EMA, and close < prior low (or through the mirrored coverage threshold)",
            ],
            exit_conditions=["The opposite-direction signal"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = df.copy()

        ema = out["close"].ewm(span=p["ema_period"], adjust=False, min_periods=p["ema_period"]).mean()
        prev_close, prev_open = out["close"].shift(1), out["open"].shift(1)
        prev_high, prev_low = out["high"].shift(1), out["low"].shift(1)
        prev_body = (prev_close - prev_open).abs()
        prev_upper_wick = prev_high - prev_close.combine(prev_open, max)
        prev_lower_wick = prev_close.combine(prev_open, min) - prev_low

        red_inverted_hammer = (prev_close < prev_open) & (prev_body > 0) & (prev_upper_wick >= prev_body * p["wick_multiplier"])
        green_hammer = (prev_close > prev_open) & (prev_body > 0) & (prev_lower_wick >= prev_body * p["wick_multiplier"])

        prev_ema = ema.shift(1)
        buy_trend = (prev_close > prev_ema) & (out["close"] > ema)
        sell_trend = (prev_close < prev_ema) & (out["close"] < ema)

        green_confirm = out["close"] > out["open"]
        red_confirm = out["close"] < out["open"]

        main_buy = red_inverted_hammer & green_confirm & buy_trend & (out["close"] > prev_high)
        main_sell = green_hammer & red_confirm & sell_trend & (out["close"] < prev_low)

        prev_range = prev_high - prev_low
        coverage = p["coverage_pct"] / 100.0
        buy_coverage_level = prev_low + prev_range * coverage
        sell_coverage_level = prev_high - prev_range * coverage

        coverage_buy = red_inverted_hammer & green_confirm & buy_trend & (prev_range > 0) & (out["close"] >= buy_coverage_level)
        coverage_sell = green_hammer & red_confirm & sell_trend & (prev_range > 0) & (out["close"] <= sell_coverage_level)

        out["ehr_buy_signal"] = main_buy | coverage_buy
        out["ehr_sell_signal"] = main_sell | coverage_sell
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[df["ehr_buy_signal"]] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[df["ehr_sell_signal"]] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        return df["ehr_buy_signal"] | df["ehr_sell_signal"]
