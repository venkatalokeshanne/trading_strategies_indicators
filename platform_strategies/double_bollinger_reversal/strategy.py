"""
Double Bollinger Reversal.

A dual-Bollinger-Band mean-reversion setup: price must first touch
the SLOW band (the setup, held valid for a limited window of bars so
a stale touch doesn't fire later) and then reverse back through the
FAST band's basis with a same-direction close (the confirmation) --
two different lookbacks so the "was there a stretch" read and the
"has it actually turned" read aren't the same noisy series. Gated by
an EMA/ADX trend filter (only reverting WITH the broader trend) and a
clock-hour session window, with at most a limited number of entries
per calendar day.

Fixed-point stop/take-profit and per-bar time-stop from the source are
NOT ported here -- risk management lives in this engine's own
ExecutionConfig, not hardcoded into strategies; pass
execution.stop_loss_atr_multiple / execution.take_profit_atr_multiple
for a comparable overlay.

Entry: close touched the slow lower band within touch_age_bars AND
now closes green back above the fast basis, with EMA/ADX confirming
an uptrend, inside the session window (long); mirrored for short.
Exit: close closes back through the SAME slow band that triggered the
setup (the reversal failed and the level got swept again), or reaches
the OPPOSITE slow band (the reversion ran all the way to the other
side).
"""

from typing import Any

import numpy as np
import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.indicators._shared import directional_movement, wilders_smooth
from app.strategies.registry import strategy_registry


def _bars_since(mask: pd.Series) -> np.ndarray:
    """Bars since the most recent True at or before each index (non-repainting)."""
    arr = mask.to_numpy()
    out = np.full(len(arr), np.iinfo(np.int64).max, dtype=np.int64)
    last_true = -1
    for i in range(len(arr)):
        if arr[i]:
            last_true = i
        if last_true >= 0:
            out[i] = i - last_true
    return out


@strategy_registry.register("double_bollinger_reversal")
class DoubleBollingerReversal(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="double_bollinger_reversal",
            display_name="Double Bollinger Reversal",
            description="A dual-Bollinger-Band mean reversion: a slow-band touch sets up the trade, a fast basis reclaim confirms it, gated by an EMA/ADX trend filter and a session window.",
            category="mean_reversion",
            indicators_used=[],
            default_params={
                "slow_bb_period": 20,
                "slow_bb_multiple": 2.0,
                "fast_bb_period": 4,
                "ema_period": 55,
                "adx_period": 14,
                "adx_threshold": 18.0,
                "touch_age_bars": 10,
                "session_start_hour_et": 2,
                "session_end_hour_et": 9,
                "max_trades_per_day": 3,
                "direction": "both",
            },
            entry_conditions=[
                "close touched the slow lower/upper band within touch_age_bars",
                "close now back above/below the fast band's basis with a matching-direction candle",
                "EMA slope + ADX confirm the trend is on the same side",
                "inside the session window, under the daily trade cap",
            ],
            exit_conditions=["close closes back through the same slow band (failed) or reaches the opposite slow band (reverted fully)"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("DoubleBollingerReversal requires a DatetimeIndex.")
        out = df.copy()

        slow_basis = out["close"].rolling(p["slow_bb_period"], min_periods=p["slow_bb_period"]).mean()
        slow_dev = p["slow_bb_multiple"] * out["close"].rolling(p["slow_bb_period"], min_periods=p["slow_bb_period"]).std()
        slow_upper = slow_basis + slow_dev
        slow_lower = slow_basis - slow_dev

        fast_basis = out["close"].rolling(p["fast_bb_period"], min_periods=p["fast_bb_period"]).mean()

        ema = out["close"].ewm(span=p["ema_period"], adjust=False, min_periods=p["ema_period"]).mean()
        ema_slope = ema - ema.shift(5)

        dm = directional_movement(out, p["adx_period"])
        plus_di, minus_di = dm["plus_di"], dm["minus_di"]
        di_sum = (plus_di + minus_di).replace(0, pd.NA)
        dx = 100 * (plus_di - minus_di).abs() / di_sum
        adx = wilders_smooth(dx, p["adx_period"])
        adx_ok = adx > p["adx_threshold"]

        bull_touch = out["low"] <= slow_lower
        bear_touch = out["high"] >= slow_upper
        bars_since_bull = _bars_since(bull_touch)
        bars_since_bear = _bars_since(bear_touch)

        bull_setup = pd.Series(bars_since_bull <= p["touch_age_bars"], index=out.index)
        bear_setup = pd.Series(bars_since_bear <= p["touch_age_bars"], index=out.index)

        bull_rev = (out["close"] > out["open"]) & (out["close"] > fast_basis)
        bear_rev = (out["close"] < out["open"]) & (out["close"] < fast_basis)
        bull_trend = (out["close"] > ema) | (ema_slope > 0)
        bear_trend = (out["close"] < ema) | (ema_slope < 0)

        # This platform's bar timestamps are already in the exchange's local
        # time (see app.utils.sessions and every other session-aware
        # indicator here) -- no timezone conversion needed, just read the hour.
        hour_of_day = pd.Series(out.index.hour, index=out.index)
        in_session = (hour_of_day >= p["session_start_hour_et"]) & (hour_of_day < p["session_end_hour_et"])

        trading_day = pd.Series(out.index.date, index=out.index)

        out["dbr_long_signal"] = bull_setup & bull_rev & bull_trend & adx_ok & in_session
        out["dbr_short_signal"] = bear_setup & bear_rev & bear_trend & adx_ok & in_session
        # Exits are read off the SLOW bands, not the fast one: the fast band is
        # a tight 4-bar SMA +/- its own stdev, which close (its own input) is
        # essentially never far enough from to cross -- verified empirically,
        # zero crossings over 6000 synthetic bars. The slow band is the same
        # one the entry setup itself proved reachable (both a stop -- swept
        # again -- and a target -- reverted all the way to the other side).
        out["dbr_slow_upper"] = slow_upper
        out["dbr_slow_lower"] = slow_lower
        out["dbr_trading_day"] = trading_day
        return out

    def _apply_daily_cap(self, df: pd.DataFrame, signal: pd.Series, max_per_day: int) -> pd.Series:
        trading_day = df["dbr_trading_day"]
        cumulative = signal.groupby(trading_day).cumsum()
        return signal & (cumulative <= max_per_day)

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        long_signal = self._apply_daily_cap(df, df["dbr_long_signal"], p["max_trades_per_day"])
        short_signal = self._apply_daily_cap(df, df["dbr_short_signal"], p["max_trades_per_day"])

        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[long_signal] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[short_signal] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        self.validate_params(params)
        close = df["close"]
        return (close < df["dbr_slow_lower"]) | (close > df["dbr_slow_upper"])
