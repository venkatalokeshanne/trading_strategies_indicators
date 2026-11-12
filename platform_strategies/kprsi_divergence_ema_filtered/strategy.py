"""
KPRSI Divergence EMA Filtered.

RSI/price divergence, but only trusted while the trend (via an EMA
slope reading) already agrees with the divergence's implied
direction, and close is on the matching side of that same EMA --
divergence alone is a common false-reversal trap, this only takes it
when the immediate trend is already turning the same way. Also
treats near-equal pivot prices (within `price_tolerance_pct`) as a
valid divergence pair, not just strictly higher/lower -- a double-top
or double-bottom-ish pivot still counts. Distinct from
app.indicators.rsi_pivot_divergence (pure pivot divergence, no trend
filter or near-equal tolerance).

Entry: Long on a confirmed bullish RSI/price divergence where the EMA
is sloping up and close is above it. Short is the mirror image.
Exit: the opposite-direction confirmed divergence signal.
"""

from typing import Any

import numpy as np
import pandas as pd

from app.domain.interfaces.strategy import Strategy, StrategyMetadata, TradeDirection
from app.strategies.registry import strategy_registry


def _pivot_mask(values: pd.Series, left: int, right: int, is_high: bool) -> np.ndarray:
    """True at the CONFIRMATION bar (right bars after the actual pivot),
    non-repainting -- a rolling window ending at row k only ever uses
    data up to and including k, so this never claims to know about a
    pivot before it's actually confirmable. The pivot's own value sits
    `right` bars before wherever this is True.
    """
    window = left + right + 1

    def check(w: np.ndarray) -> bool:
        target = w.max() if is_high else w.min()
        return w[left] == target and (w == w[left]).sum() == 1

    mask = values.rolling(window=window, min_periods=window).apply(check, raw=True)
    return mask.fillna(0).astype(bool).to_numpy()


@strategy_registry.register("kprsi_divergence_ema_filtered")
class KPRSIDivergenceEMAFiltered(Strategy):
    @property
    def metadata(self) -> StrategyMetadata:
        return StrategyMetadata(
            name="kprsi_divergence_ema_filtered",
            display_name="KPRSI Divergence EMA Filtered",
            description="RSI/price divergence, only taken once an EMA slope reading and price's position relative to it already agree with the divergence's implied direction.",
            category="momentum",
            indicators_used=[],
            default_params={
                "ema_period": 20,
                "rsi_period": 14,
                "pivot_range": 5,
                "ema_slope_threshold_pct": 0.05,
                "price_tolerance_pct": 0.2,
                "direction": "both",
            },
            entry_conditions=[
                "Long: confirmed bullish RSI/price divergence AND EMA sloping up AND close above the EMA",
                "Short: confirmed bearish RSI/price divergence AND EMA sloping down AND close below the EMA",
            ],
            exit_conditions=["The opposite-direction confirmed divergence signal"],
        )

    def prepare(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.DataFrame:
        p = self.validate_params(params)
        out = df.copy()

        ema = out["close"].ewm(span=p["ema_period"], adjust=False, min_periods=p["ema_period"]).mean()
        ema_slope_pct = (ema - ema.shift(1)) / ema.shift(1) * 100
        ema_up = ema_slope_pct > p["ema_slope_threshold_pct"]
        ema_down = ema_slope_pct < -p["ema_slope_threshold_pct"]

        n = p["rsi_period"]
        delta = out["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
        avg_loss = loss.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))

        left = right = p["pivot_range"]
        high_mask = _pivot_mask(out["high"], left, right, is_high=True)
        low_mask = _pivot_mask(out["low"], left, right, is_high=False)
        high_arr, low_arr, rsi_arr = out["high"].to_numpy(), out["low"].to_numpy(), rsi.to_numpy()
        tol_pct = p["price_tolerance_pct"]

        length = len(out)
        bull_div = np.zeros(length, dtype=bool)
        bear_div = np.zeros(length, dtype=bool)

        prev_pl_price = prev_pl_rsi = np.nan
        prev_ph_price = prev_ph_rsi = np.nan

        for i in range(length):
            if low_mask[i]:
                pl_price, pl_rsi = low_arr[i - right], rsi_arr[i - right]
                if not np.isnan(prev_pl_price):
                    price_diff_pct = abs(pl_price - prev_pl_price) / prev_pl_price * 100
                    if (pl_price < prev_pl_price or price_diff_pct <= tol_pct) and pl_rsi > prev_pl_rsi:
                        bull_div[i] = True
                prev_pl_price, prev_pl_rsi = pl_price, pl_rsi

            if high_mask[i]:
                ph_price, ph_rsi = high_arr[i - right], rsi_arr[i - right]
                if not np.isnan(prev_ph_price):
                    price_diff_pct = abs(ph_price - prev_ph_price) / prev_ph_price * 100
                    if (ph_price > prev_ph_price or price_diff_pct <= tol_pct) and ph_rsi < prev_ph_rsi:
                        bear_div[i] = True
                prev_ph_price, prev_ph_rsi = ph_price, ph_rsi

        bull_div_s = pd.Series(bull_div, index=out.index)
        bear_div_s = pd.Series(bear_div, index=out.index)

        out["kprsi_long"] = bull_div_s & ema_up & (out["close"] > ema)
        out["kprsi_short"] = bear_div_s & ema_down & (out["close"] < ema)
        return out

    def generate_entries(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        p = self.validate_params(params)
        entries = pd.Series(None, index=df.index, dtype=object)
        if p["direction"] in ("both", "long_only"):
            entries[df["kprsi_long"]] = TradeDirection.LONG
        if p["direction"] in ("both", "short_only"):
            entries[df["kprsi_short"]] = TradeDirection.SHORT
        return entries

    def generate_exits(self, df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
        return df["kprsi_long"] | df["kprsi_short"]
