"""
VCP Trend Squeeze Breakout.

Long-only, layering a Minervini-style trend template on top of a
volatility squeeze -- distinct from app.strategies.squeeze_breakout,
which uses a Bollinger-inside-Keltner squeeze with no MA-stack trend
filter at all. Three independent gates must all hold on the same bar:

1. Trend template: close > SMA50 > SMA150 > SMA200, SMA200 rising
   over the trailing window, and SMA50 not falling -- the standard
   "stage 2 uptrend" read.
2. Volatility contraction ("VCP"): the recent high-low range, ranked
   against its own trailing history, sits in its bottom percentile
   (a squeeze), OR the recent close-only range is unusually tight.
3. Volume expansion: the breakout bar's volume clears a multiple of
   its own rolling average.

Entry fires on a close beyond the recent N-bar high while all three
gates hold -- a same-bar simplification of the source's pending
stop-order (`strategy.entry(..., stop=recentHigh[1])`), matching how
every other breakout strategy in this codebase (e.g. orb_breakout)
reads a close-through rather than modeling a resting stop order.

The source's tiered 25/50/100% partial take-profits aren't portable
(this engine has no partial-fill support, one position at a time) --
kept as a single position with a trend-invalidation exit instead; use
execution.stop_loss_pct/take_profit_atr_multiple for a comparable
hard-stop/target overlay.
"""

from typing import Any

import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.strategies.registry import strategy_registry


@strategy_registry.register("vcp_trend_squeeze_breakout")
class VCPTrendSqueezeBreakout(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="vcp_trend_squeeze_breakout",
            display_name="VCP Trend Squeeze Breakout",
            description="Long-only: a Minervini-style trend template, a volatility-contraction (VCP) squeeze, and a volume-expansion breakout above the recent high, all required on the same bar.",
            category="breakout",
            indicators_used=[],
            default_params={
                "fast_sma_period": 50,
                "mid_sma_period": 150,
                "slow_sma_period": 200,
                "slow_sma_rising_lookback": 20,
                "range_period": 3,
                "percentile_lookback": 150,
                "squeeze_percentile_max": 40.0,
                "close_range_pct_max": 4.0,
                "volume_avg_period": 20,
                "volume_multiple": 1.2,
                "breakout_lookback": 3,
            },
            entry_conditions=[
                "close > SMA(fast) > SMA(mid) > SMA(slow), SMA(slow) rising over its lookback, SMA(fast) not falling",
                "the recent high-low range's percentile rank <= squeeze_percentile_max, OR the recent close-only range% <= close_range_pct_max",
                "volume > volume_multiple * its own rolling average",
                "close crosses above the recent breakout_lookback-bar high",
            ],
            exit_conditions=["close closes back below SMA(fast) (the trend template breaks)"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = df.copy()

        fast_sma = out["close"].rolling(p["fast_sma_period"], min_periods=p["fast_sma_period"]).mean()
        mid_sma = out["close"].rolling(p["mid_sma_period"], min_periods=p["mid_sma_period"]).mean()
        slow_sma = out["close"].rolling(p["slow_sma_period"], min_periods=p["slow_sma_period"]).mean()

        slow_rising = slow_sma > slow_sma.shift(p["slow_sma_rising_lookback"])
        fast_not_falling = fast_sma >= fast_sma.shift(1)
        bullish_trend = (
            (out["close"] > fast_sma) & (fast_sma > mid_sma) & (mid_sma > slow_sma) & slow_rising & fast_not_falling
        )

        rp = p["range_period"]
        high_range = out["high"].rolling(rp, min_periods=rp).max()
        low_range = out["low"].rolling(rp, min_periods=rp).min()
        range_pct = (high_range - low_range) / high_range.replace(0, pd.NA) * 100

        high_close = out["close"].rolling(rp, min_periods=rp).max()
        low_close = out["close"].rolling(rp, min_periods=rp).min()
        close_range_pct = (high_close - low_close) / high_close.replace(0, pd.NA) * 100

        pb = p["percentile_lookback"]
        range_percentile = range_pct.rolling(window=pb + 1, min_periods=pb + 1).apply(
            lambda w: (w[:-1] < w[-1]).sum() / pb * 100, raw=True
        )

        range_squeeze = range_percentile <= p["squeeze_percentile_max"]
        close_squeeze = close_range_pct <= p["close_range_pct_max"]
        pivot = range_squeeze | close_squeeze

        volume_avg = out["volume"].rolling(p["volume_avg_period"], min_periods=p["volume_avg_period"]).mean()
        volume_ok = out["volume"] > volume_avg * p["volume_multiple"]

        recent_high = out["high"].rolling(p["breakout_lookback"], min_periods=p["breakout_lookback"]).max()
        prev_recent_high = recent_high.shift(1)
        close, prev_close = out["close"], out["close"].shift(1)
        breakout = (close > prev_recent_high) & (prev_close <= prev_recent_high.shift(1))

        out["vcp_long_signal"] = bullish_trend & pivot & volume_ok & breakout
        out["vcp_fast_sma"] = fast_sma
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        self.validate_params(params)
        entries = pd.Series(None, index=df.index, dtype=object)
        entries[df["vcp_long_signal"]] = TradeDirection.LONG
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        self.validate_params(params)
        return df["close"] < df["vcp_fast_sma"]
