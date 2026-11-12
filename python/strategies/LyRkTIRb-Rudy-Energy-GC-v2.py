"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Rudy Energy GC v2
Author       : bigboo407
Source URL   : https://www.tradingview.com/script/LyRkTIRb-Rudy-Energy-GC-v2
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Long when EMA50 > SMA200, RSI below the cap, the close above EMA21 and the strength score
(2 for the regime, +1 RSI < 65, +1 momentum over SMA200 > 5 %, +1 close > EMA21) is at least 3, while flat. While a
position is open at the close, a trailing exit is re-issued every bar with trail_points = 8 % of the close and
trail_offset = 1 % of the close, converted to ticks, so it first works on the bar after the fill. A bearish regime
(EMA50 < SMA200) closes the long at the next open.

Deviations from the original: none.
Not carried over: the MA plots, background and BUY / EXIT shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, ta


class RudyEnergyGc(Script):
    TITLE = "Rudy Energy GC v2"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=20000, default_qty_type="percent_of_equity", default_qty_value=18,
                    commission_type="percent", commission_value=0.1)
    SOURCE = {"id": "LyRkTIRb", "author": "bigboo407", "licence": "not stated",
              "url": "https://www.tradingview.com/script/LyRkTIRb-Rudy-Energy-GC-v2"}

    def init(self):
        self.p_fast = self.input.int(50, "Fast EMA Period")
        self.p_slow = self.input.int(200, "Slow SMA Period")
        self.p_trend = self.input.int(21, "Trend EMA Period")
        self.p_rsi = self.input.int(14, "RSI Period")
        self.p_rsi_cap = self.input.int(75, "RSI Cap")
        self.p_min = self.input.int(3, "Minimum Signal Strength")
        self.p_trail = self.input.float(8.0, "Trailing Stop Pct") / 100
        self.p_offset = self.input.float(1.0, "Trail Offset Pct") / 100

    def on_bar(self):
        fast_ma = ta.ema(self.close, self.p_fast)
        slow_ma = ta.sma(self.close, self.p_slow)
        trend_ma = ta.ema(self.close, self.p_trend)
        rsi_val = ta.rsi(self.close, self.p_rsi)
        mom_pct = div(self.close - slow_ma, slow_ma) * 100
        strength = 0
        strength += 2 if fast_ma > slow_ma else 0
        strength += 1 if rsi_val < 65 else 0
        strength += 1 if mom_pct > 5 else 0
        strength += 1 if self.close > trend_ma else 0
        bull_regime = fast_ma > slow_ma
        bear_regime = fast_ma < slow_ma
        not_extended = rsi_val < self.p_rsi_cap
        trend_intact = self.close > trend_ma
        go_long = bull_regime and not_extended and trend_intact and strength >= self.p_min
        exit_signal = bear_regime
        st = self.strategy
        if go_long and st.position_size == 0:
            st.entry("GC_Long", st.long)
        if st.position_size > 0:
            t_pts = div(self.close * self.p_trail, self.syminfo.mintick)
            t_off = div(self.close * self.p_offset, self.syminfo.mintick)
            st.exit("GC_Trail", "GC_Long", trail_points=t_pts, trail_offset=t_off)
        if exit_signal and st.position_size > 0:
            st.close("GC_Long", comment="Regime Shift")
        self.plot(fast_ma, "Fast EMA", color=color.blue, linewidth=2)
        self.plot(slow_ma, "Slow SMA", color=color.red, linewidth=2)
        self.plot(trend_ma, "Trend EMA", color=color.orange)
