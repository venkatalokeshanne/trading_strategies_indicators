"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Percent Supertrend Strategy (Long Only)
Author       : MeinnameaufXYZ
Source URL   : https://www.tradingview.com/script/sPNx5Z74
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. finalUpper / finalLower / trend are var series whose [1] history goes through
H(); trend starts at 1 (`nz(trend[1], 1)`). The long opens when the trend flips from -1 to 1 and closes when
it flips back.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, na, nz, pmath


class PercentSupertrendLongOnly(Script):
    TITLE = "Percent Supertrend Strategy (Long Only)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "sPNx5Z74", "author": "MeinnameaufXYZ", "licence": "not stated",
              "url": "https://www.tradingview.com/script/sPNx5Z74"}

    def init(self):
        self.perc = self.input.float(20.0, "Prozent Abstand", step=0.1) / 100

    def on_bar(self):
        src = self.hl2
        upper_basic = src * (1 + self.perc)
        lower_basic = src * (1 - self.perc)
        prev_fu, prev_fl, prev_trend = self.H("fu")[1], self.H("fl")[1], self.H("trend")[1]
        if na(prev_fu):
            final_upper = upper_basic
        else:
            final_upper = upper_basic if self.close[1] > prev_fu else pmath.min(upper_basic, prev_fu)
        if na(prev_fl):
            final_lower = lower_basic
        else:
            final_lower = lower_basic if self.close[1] < prev_fl else pmath.max(lower_basic, prev_fl)
        trend = nz(prev_trend, 1)
        if self.close > prev_fu:
            trend = 1
        elif self.close < prev_fl:
            trend = -1
        self.H("fu").set(final_upper)
        self.H("fl").set(final_lower)
        self.H("trend").set(trend)
        long_signal = trend == 1 and prev_trend == -1
        exit_signal = trend == -1 and prev_trend == 1
        st = self.strategy
        if long_signal:
            st.entry("Long", st.long)
        if exit_signal:
            st.close("Long")
        line = final_lower if trend == 1 else final_upper
        self.plot(line, title="Percent Supertrend", linewidth=2, color=color.lime if trend == 1 else color.red)
        self.plotshape(long_signal, title="Long Entry")
        self.plotshape(exit_signal, title="Exit")
