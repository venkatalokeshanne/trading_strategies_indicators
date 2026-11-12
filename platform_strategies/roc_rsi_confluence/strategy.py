"""
ROC & RSI Confluence.

Trades when a ROC-crosses-zero event and an RSI-crosses-its-own-SMA
event both happen within a tolerance window of each other (either one
can fire first) -- a confluence read, requiring two independent
momentum measures to agree within a few bars rather than relying on
either alone.

The source script only defines entry signals (it's a plain "indicator"
with plotshape markers, not a strategy) -- exit here is the next
confluence signal in the opposite direction, the same "trade the next
opposite signal" convention used by every other cross-based strategy
in this library.

Entry: Long when ROC crosses above 0 with an RSI/signal cross-up
within `tolerance` bars (either order), or vice versa. Short is the
mirror image on the downside.
Exit: the next confluence signal in the opposite direction.

This file contains ONLY strategy logic -- ROC/RSI math lives in
app.indicators and is reused as-is.
"""

from typing import Any

import numpy as np
import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators.rsi import RSI
from app.indicators.roc import ROC
from app.strategies.registry import strategy_registry


def _bars_since(cond: pd.Series) -> pd.Series:
    """NaN before the first True; 0 on the bar it's True; counts up after."""
    idx = np.arange(len(cond))
    last_true_idx = np.where(cond.to_numpy(), idx, np.nan)
    last_true_idx = pd.Series(last_true_idx, index=cond.index).ffill()
    return pd.Series(idx, index=cond.index) - last_true_idx


@strategy_registry.register("roc_rsi_confluence")
class ROCRSIConfluence(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="roc_rsi_confluence",
            display_name="ROC & RSI Confluence",
            description="ROC crossing zero and RSI crossing its own SMA within a tolerance window of each other -- a two-signal confluence read.",
            category="momentum",
            indicators_used=["roc", "rsi"],
            default_params={"roc_period": 9, "rsi_period": 14, "rsi_signal_period": 14, "tolerance_bars": 2, "direction": "both"},
            entry_conditions=[
                "Long: ROC crosses above 0 and an RSI-signal cross-up happened within tolerance_bars (either order), or the mirror case",
                "Short: the same confluence on the downside (ROC below 0 / RSI-signal cross-down)",
            ],
            exit_conditions=["The next confluence signal in the opposite direction"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = ROC().calculate(df, {"period": p["roc_period"], "source": "close"})
        out = RSI().calculate(out, {"period": p["rsi_period"], "source": "close"})
        out[f"rsi_signal_{p['rsi_period']}_{p['rsi_signal_period']}"] = (
            out[f"rsi_{p['rsi_period']}"].rolling(window=p["rsi_signal_period"], min_periods=p["rsi_signal_period"]).mean()
        )
        return out

    def _signals(self, df: pd.DataFrame, p: dict[str, Any]) -> tuple[pd.Series, pd.Series]:
        roc = df[f"roc_{p['roc_period']}"]
        rsi = df[f"rsi_{p['rsi_period']}"]
        rsi_signal = df[f"rsi_signal_{p['rsi_period']}_{p['rsi_signal_period']}"]
        prev_roc, prev_rsi, prev_rsi_signal = roc.shift(1), rsi.shift(1), rsi_signal.shift(1)
        tolerance = p["tolerance_bars"]

        roc_up = (roc > 0) & (prev_roc <= 0)
        roc_down = (roc < 0) & (prev_roc >= 0)
        rsi_up = (rsi > rsi_signal) & (prev_rsi <= prev_rsi_signal)
        rsi_down = (rsi < rsi_signal) & (prev_rsi >= prev_rsi_signal)

        bars_since_rsi_up = _bars_since(rsi_up).fillna(tolerance + 1)
        bars_since_roc_up = _bars_since(roc_up).fillna(tolerance + 1)
        bars_since_rsi_down = _bars_since(rsi_down).fillna(tolerance + 1)
        bars_since_roc_down = _bars_since(roc_down).fillna(tolerance + 1)

        buy_signal = (roc_up & (bars_since_rsi_up <= tolerance)) | (rsi_up & (bars_since_roc_up <= tolerance))
        sell_signal = (roc_down & (bars_since_rsi_down <= tolerance)) | (rsi_down & (bars_since_roc_down <= tolerance))
        return buy_signal, sell_signal

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        buy_signal, sell_signal = self._signals(df, p)

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[buy_signal] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[sell_signal] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        buy_signal, sell_signal = self._signals(df, p)
        return buy_signal | sell_signal
