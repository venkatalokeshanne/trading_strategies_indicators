"""
RSI Stoch Volatility Filtered.

RSI crossing back through an extreme (30/70), confirmed by where the
raw stochastic %K currently sits, and gated by two volatility filters:
ATR must be running hot relative to its own recent average (expansion,
not compression), and the recent range must be wide enough relative to
ATR to rule out a flat/ranging tape.

The source script also required a 1h-timeframe RSI/CCI confirmation
(via request.security) before firing -- dropped here since this
platform's Indicator interface operates on one timeframe at a time;
what's left is the full same-timeframe confluence (RSI + stochastic +
both volatility filters), not a partial signal.

Entry: Long when RSI crosses up through 30 AND stochastic %K > 20 AND
both volatility filters pass. Short is the mirror image (RSI crosses
down through 70, %K < 80).
Exit: the next opposite-direction signal.

This file contains ONLY strategy logic -- RSI/Stochastic/ATR math
lives in app.indicators and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.atr import ATR
from app.indicators.rsi import RSI
from app.indicators.stoch import Stochastic
from app.strategies.registry import strategy_registry


@strategy_registry.register("rsi_stoch_volatility_filtered")
class RSIStochVolatilityFiltered(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="rsi_stoch_volatility_filtered",
            display_name="RSI Stoch Volatility Filtered",
            description="RSI crossing back through 30/70, confirmed by stochastic %K, gated by ATR expansion and a not-flat range filter.",
            category="momentum",
            indicators_used=["rsi", "stoch", "atr"],
            default_params={
                "rsi_period": 14,
                "stoch_k_period": 14,
                "stoch_d_period": 3,
                "atr_period": 14,
                "use_atr_filter": True,
                "atr_filter_multiple": 1.1,
                "use_flat_filter": True,
                "flat_lookback": 20,
                "flat_multiple": 2.0,
                "direction": "both",
            },
            entry_conditions=[
                "Long: RSI crosses above 30, stochastic %K > 20, ATR filter and flat-range filter both pass",
                "Short: RSI crosses below 70, stochastic %K < 80, ATR filter and flat-range filter both pass",
            ],
            exit_conditions=["The next opposite-direction signal"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = RSI().calculate(df, {"period": p["rsi_period"], "source": "close"})
        # k_slowing=1 -> raw (unsmoothed) fast %K, matching the source's ta.stoch()
        out = Stochastic().calculate(out, {"k_period": p["stoch_k_period"], "k_slowing": 1, "d_period": p["stoch_d_period"]})
        out = ATR().calculate(out, {"period": p["atr_period"]})

        atr_col = f"atr_{p['atr_period']}"
        out["rsi_stoch_vol_atr_sma"] = out[atr_col].rolling(window=p["atr_period"], min_periods=p["atr_period"]).mean()
        out["rsi_stoch_vol_range"] = (
            out["high"].rolling(window=p["flat_lookback"], min_periods=p["flat_lookback"]).max()
            - out["low"].rolling(window=p["flat_lookback"], min_periods=p["flat_lookback"]).min()
        )
        return out

    def _signals(self, df: pd.DataFrame, p: dict[str, Any]) -> tuple[pd.Series, pd.Series]:
        rsi = df[f"rsi_{p['rsi_period']}"]
        prev_rsi = rsi.shift(1)
        stoch_k = df[f"stoch_k_{p['stoch_k_period']}_1_{p['stoch_d_period']}"]
        atr = df[f"atr_{p['atr_period']}"]

        atr_cond = (~p["use_atr_filter"]) | (atr > df["rsi_stoch_vol_atr_sma"] * p["atr_filter_multiple"])
        flat_cond = (~p["use_flat_filter"]) | (df["rsi_stoch_vol_range"] > atr * p["flat_multiple"])

        rsi_long_cross = (rsi > 30) & (prev_rsi <= 30)
        rsi_short_cross = (rsi < 70) & (prev_rsi >= 70)

        long_signal = rsi_long_cross & (stoch_k > 20) & atr_cond & flat_cond
        short_signal = rsi_short_cross & (stoch_k < 80) & atr_cond & flat_cond
        return long_signal, short_signal

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        long_signal, short_signal = self._signals(df, p)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[long_signal] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[short_signal] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        long_signal, short_signal = self._signals(df, p)
        return long_signal | short_signal
