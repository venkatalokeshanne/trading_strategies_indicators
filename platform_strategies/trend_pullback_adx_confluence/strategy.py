"""
Trend Pullback ADX Confluence.

A multi-filter long-only confluence: trades a pullback bounce off a
medium EMA, but only when three independent conditions all agree --
(1) price is in an established macro uptrend (above a long SMA),
(2) that trend has real strength, not flat chop (ADX above threshold),
(3) momentum hasn't already run into overbought/oversold extremes
(RSI within a band). Distinct from this platform's other EMA-pullback
strategies (ema_cross_rsi_filtered has no SMA/ADX regime gate;
vwap_trend_pullback pulls back to VWAP, not an EMA).

The source script's ATR stop-loss/take-profit is NOT ported here --
risk management lives in this engine's own ExecutionConfig, not
hardcoded into strategies; pass execution.stop_loss_atr_multiple /
execution.take_profit_atr_multiple for a comparable overlay.

Entry: close > SMA(200) AND ADX > threshold AND close crosses above
EMA(21) (or is freshly above it) AND RSI within [oversold, overbought].
Exit: close drops back below EMA(21), or the macro trend filter breaks
(close < SMA(200)).
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.adx import ADX
from app.indicators.ema import EMA
from app.indicators.rsi import RSI
from app.indicators.sma import SMA
from app.strategies.registry import strategy_registry


@strategy_registry.register("trend_pullback_adx_confluence")
class TrendPullbackADXConfluence(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="trend_pullback_adx_confluence",
            display_name="Trend Pullback ADX Confluence",
            description="Long-only EMA pullback bounce, gated by a macro SMA trend filter, ADX trend-strength filter, and an RSI band.",
            category="trend_following",
            indicators_used=["sma", "ema", "adx", "rsi"],
            default_params={
                "macro_sma_period": 200,
                "pullback_ema_period": 21,
                "adx_period": 14,
                "adx_threshold": 20.0,
                "rsi_period": 14,
                "rsi_low": 45.0,
                "rsi_high": 70.0,
            },
            entry_conditions=[
                "close > SMA(macro_sma_period)",
                "ADX(adx_period) > adx_threshold",
                "close crosses above EMA(pullback_ema_period)",
                "RSI(rsi_period) within [rsi_low, rsi_high]",
            ],
            exit_conditions=["close drops back below the pullback EMA, or below the macro SMA"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = SMA().calculate(df, {"period": p["macro_sma_period"], "source": "close"})
        out = EMA().calculate(out, {"period": p["pullback_ema_period"], "source": "close"})
        out = ADX().calculate(out, {"period": p["adx_period"]})
        out = RSI().calculate(out, {"period": p["rsi_period"], "source": "close"})
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        close = df["close"]
        sma = df[f"sma_{p['macro_sma_period']}"]
        ema = df[f"ema_{p['pullback_ema_period']}"]
        adx = df[f"adx_{p['adx_period']}"]
        rsi = df[f"rsi_{p['rsi_period']}"]
        prev_close, prev_ema = close.shift(1), ema.shift(1)

        cross_up = (close > ema) & (prev_close <= prev_ema)
        confluence = (
            (close > sma)
            & (adx > p["adx_threshold"])
            & cross_up
            & (rsi >= p["rsi_low"])
            & (rsi <= p["rsi_high"])
        )

        entries = pd.Series(None, index=df.index, dtype=object)
        entries[confluence] = TradeDirection.LONG
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        close = df["close"]
        sma = df[f"sma_{p['macro_sma_period']}"]
        ema = df[f"ema_{p['pullback_ema_period']}"]
        return (close < ema) | (close < sma)
