"""
Volume Dry Pullback.

A mean-reversion-in-uptrend entry: buys a pullback (price below a
short mean EMA, RSI in dip territory) that happens on BELOW-average
volume -- read as a low-conviction dip with little real selling
pressure behind it, as opposed to a high-volume dip that suggests
genuine distribution. This is the mirror image of this platform's
volume-SPIKE-confirmed setups (e.g. institutional_volume_spike): here
a lack of volume is the confirming signal, not a surge of it.

Entry: close above a longer "bull gate" EMA (uptrend context) AND
close below a shorter mean EMA AND RSI below a dip threshold AND
volume below a fraction of its own average AND close turned up vs the
prior bar.
Exit: close recovers back above the mean EMA, or the bull-gate
context breaks (close drops back below the gate EMA).
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.strategies.registry import strategy_registry


@strategy_registry.register("volume_dry_pullback")
class VolumeDryPullback(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="volume_dry_pullback",
            display_name="Volume Dry Pullback",
            description="Buys a dip inside an uptrend specifically when volume has DRIED UP during the dip -- read as little real selling conviction behind the pullback.",
            category="mean_reversion",
            indicators_used=[],
            default_params={
                "ema_gate_period": 50,
                "ema_mean_period": 20,
                "volume_ma_period": 20,
                "volume_dry_multiple": 0.7,
                "rsi_period": 14,
                "rsi_dip_level": 45.0,
                "require_price_turn_up": True,
            },
            entry_conditions=[
                "close > EMA(ema_gate_period) (uptrend context)",
                "close < EMA(ema_mean_period) AND RSI(rsi_period) < rsi_dip_level (pullback)",
                "volume < volume_dry_multiple * its own average (dried-up volume)",
                "close > prior close (optional, on by default)",
            ],
            exit_conditions=["close recovers back above the mean EMA, or the bull-gate EMA context breaks"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = df.copy()

        ema_gate = out["close"].ewm(span=p["ema_gate_period"], adjust=False, min_periods=p["ema_gate_period"]).mean()
        ema_mean = out["close"].ewm(span=p["ema_mean_period"], adjust=False, min_periods=p["ema_mean_period"]).mean()

        n = p["rsi_period"]
        delta = out["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
        avg_loss = loss.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
        rs = avg_gain / avg_loss.replace(0, pd.NA)
        rsi = 100 - (100 / (1 + rs))

        vol_ma = out["volume"].rolling(window=p["volume_ma_period"], min_periods=p["volume_ma_period"]).mean()

        in_bull = out["close"] > ema_gate
        is_pullback = (out["close"] < ema_mean) & (rsi < p["rsi_dip_level"])
        vol_dry = out["volume"] < vol_ma * p["volume_dry_multiple"]
        turn_up = (out["close"] > out["close"].shift(1)) if p["require_price_turn_up"] else True

        out["vdp_ema_gate"] = ema_gate
        out["vdp_ema_mean"] = ema_mean
        out["vdp_entry"] = in_bull & is_pullback & vol_dry & turn_up
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        self.validate_params(params)
        entries = pd.Series(None, index=df.index, dtype=object)
        entries[df["vdp_entry"]] = TradeDirection.LONG
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        self.validate_params(params)
        return (df["close"] > df["vdp_ema_mean"]) | (df["close"] < df["vdp_ema_gate"])
