"""
StochRSI Reversal.

StochRSI is far more sensitive than plain RSI (it's the Stochastic
formula applied to RSI itself), so it spends more time pinned at its
extremes -- useful for day trading, where a fast, early reversal read
matters more than a smooth one. Trades the %K/%D cross while both
lines sit inside the oversold or overbought zone.

Entry: %K crosses above %D while both are below the oversold
threshold (long); %K crosses below %D while both are above the
overbought threshold (short).
Exit: %K crosses %D again in the opposite zone.

This file contains ONLY strategy logic -- StochRSI math lives in
app.indicators.stochrsi and is reused as-is.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.stochrsi import StochRSI
from app.strategies.registry import strategy_registry


@strategy_registry.register("stoch_rsi_reversal")
class StochRSIReversal(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="stoch_rsi_reversal",
            display_name="StochRSI Reversal",
            description="Trades %K/%D crosses inside StochRSI's oversold/overbought zones -- an early, fast-reacting reversal read.",
            category="momentum",
            indicators_used=["stochrsi"],
            default_params={
                "rsi_period": 14,
                "stoch_period": 14,
                "k_period": 3,
                "d_period": 3,
                "oversold": 20.0,
                "overbought": 80.0,
                "direction": "both",
            },
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        return StochRSI().calculate(
            df,
            {
                "rsi_period": p["rsi_period"],
                "stoch_period": p["stoch_period"],
                "k_period": p["k_period"],
                "d_period": p["d_period"],
            },
        )

    def _cols(self, p: dict[str, Any]) -> tuple[str, str]:
        suffix = f"{p['rsi_period']}_{p['stoch_period']}"
        return f"stochrsi_k_{suffix}", f"stochrsi_d_{suffix}"

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        k_col, d_col = self._cols(p)
        k, d = df[k_col], df[d_col]
        prev_k, prev_d = k.shift(1), d.shift(1)

        cross_up = (k > d) & (prev_k <= prev_d) & (k < p["oversold"]) & (d < p["oversold"])
        cross_down = (k < d) & (prev_k >= prev_d) & (k > p["overbought"]) & (d > p["overbought"])

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[cross_up] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[cross_down] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        k_col, d_col = self._cols(p)
        k, d = df[k_col], df[d_col]
        prev_k, prev_d = k.shift(1), d.shift(1)

        cross_down_overbought = (k < d) & (prev_k >= prev_d) & (k > p["overbought"]) & (d > p["overbought"])
        cross_up_oversold = (k > d) & (prev_k <= prev_d) & (k < p["oversold"]) & (d < p["oversold"])
        return cross_down_overbought | cross_up_oversold
