"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Evasive SuperTrend Strategy [Source Select]
Author       : egoigor1976
Source URL   : https://www.tradingview.com/script/Zx1H2viP-Evasive-SuperTrend-Strategy-Source-Select
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. st_line and trend are var variables; st_line[1] goes through H(). `nz(st_line[1],
default)` falls back to the current band while the history is na. When the line is "noisy" (close within
threshold x ATR of it) it drifts away by alpha x ATR instead of following the band. A trend change opens the
position in the new direction (ta.change(trend) > 0 long, < 0 short).

Deviations from the original: none.
Not carried over: the solid / dotted band colouring (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, nz, pmath, ta


class EvasiveSuperTrend(Script):
    TITLE = "Evasive SuperTrend Strategy [Source Select]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="cash", default_qty_value=1000,
                    commission_type="percent", commission_value=0.05)
    SOURCE = {"id": "Zx1H2viP", "author": "egoigor1976", "licence": "not stated",
              "url": "https://www.tradingview.com/script/Zx1H2viP-Evasive-SuperTrend-Strategy-Source-Select"}

    def init(self):
        self.length_input = self.input.int(10, "ATR Length", minval=1, group="Supertrend Settings")
        self.multiplier_input = self.input.float(3.0, "Base Multiplier", minval=0.1, step=0.1, group="Supertrend Settings")
        self.src_input = self.input.source(self.hl2, "Source", group="Supertrend Settings")
        self.threshold_input = self.input.float(1.0, "Noise Threshold (xATR)", minval=0.0, step=0.1, group="Noise Avoidance Logic")
        self.alpha_input = self.input.float(0.5, "Expansion Alpha (xATR)", minval=0.0, step=0.1, group="Noise Avoidance Logic")
        self.trend = 1

    def on_bar(self):
        atr = ta.atr(self.length_input)
        upper_base = self.src_input + self.multiplier_input * atr
        lower_base = self.src_input - self.multiplier_input * atr
        prev_line = nz(self.H("st_line")[1], lower_base if self.trend == 1 else upper_base)
        is_noisy = pmath.abs(self.close - prev_line) < (atr * self.threshold_input)
        if self.trend == 1:
            st_line = prev_line - (atr * self.alpha_input) if is_noisy else pmath.max(lower_base, prev_line)
            if self.close < st_line:
                self.trend = -1
                st_line = upper_base
        else:
            st_line = prev_line + (atr * self.alpha_input) if is_noisy else pmath.min(upper_base, prev_line)
            if self.close > st_line:
                self.trend = 1
                st_line = lower_base
        self.H("st_line").set(st_line)
        self.plot(NA if is_noisy else st_line, "Solid Band", color=color.teal, linewidth=2)
        self.plot(st_line if is_noisy else NA, "Dotted Band", color=color.teal, linewidth=2)
        st = self.strategy
        if ta.change(self.trend) > 0:
            st.entry("Long", st.long)
        if ta.change(self.trend) < 0:
            st.entry("Short", st.short)
