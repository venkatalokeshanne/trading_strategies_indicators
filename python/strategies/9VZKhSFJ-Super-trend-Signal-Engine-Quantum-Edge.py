"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Signal Engine Quantum Edge
Author       : Quantum-Edge-Capital
Source URL   : https://www.tradingview.com/script/9VZKhSFJ-Super-trend-Signal-Engine-Quantum-Edge
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A hand-written SuperTrend (ATR(10) x 3 around hl2: the bands stick to the previous value while the
previous close stays on the right side; the trend flips on a close beyond the previous bar's opposite band) enters long when
it turns up and short when it turns down (reversing, 1 contract), inside the From / To date window (default 2018-09-01 to
9999-01-01).

Deviations from the original: none.
Not carried over: the trend-line plots, signal shapes, highlighter fills and bar colouring (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, nz, pmath, ta


class SuperTrendSignalEngine(Script):
    TITLE = "Signal Engine Quantum Edge"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "9VZKhSFJ", "author": "Quantum-Edge-Capital", "licence": "not stated",
              "url": "https://www.tradingview.com/script/9VZKhSFJ-Super-trend-Signal-Engine-Quantum-Edge"}

    def init(self):
        self.periods = self.input.int(10, title="ATR Period")
        self.src = self.input.source(self.hl2, title="Source")
        self.multiplier = self.input.float(3.0, title="ATR Multiplier", step=0.1)
        self.change_atr = self.input.bool(True, title="Change ATR Calculation Method ?")
        self.from_month = self.input.int(9, title="From Month", minval=1, maxval=12)
        self.from_day = self.input.int(1, title="From Day", minval=1, maxval=31)
        self.from_year = self.input.int(2018, title="From Year", minval=999)
        self.to_month = self.input.int(1, title="To Month", minval=1, maxval=12)
        self.to_day = self.input.int(1, title="To Day", minval=1, maxval=31)
        self.to_year = self.input.int(9999, title="To Year", minval=999)
        self.up_prev = NA
        self.dn_prev = NA
        self.trend_prev = NA

    def on_bar(self):
        atr2 = ta.sma(ta.tr(False), self.periods)
        atr = ta.atr(self.periods) if self.change_atr else atr2
        up = self.src - self.multiplier * atr
        up1 = nz(self.up_prev, up)
        up = pmath.max(up, up1) if self.close[1] > up1 else up
        dn = self.src + self.multiplier * atr
        dn1 = nz(self.dn_prev, dn)
        dn = pmath.min(dn, dn1) if self.close[1] < dn1 else dn
        trend = nz(self.trend_prev, 1)
        trend = 1 if (trend == -1 and self.close > dn1) else (-1 if (trend == 1 and self.close < up1) else trend)
        buy_signal = trend == 1 and nz(self.trend_prev, 0) == -1
        sell_signal = trend == -1 and nz(self.trend_prev, 0) == 1
        self.up_prev, self.dn_prev, self.trend_prev = up, dn, trend
        start = self.timestamp(self.from_year, self.from_month, self.from_day, 0, 0)
        finish = self.timestamp(self.to_year, self.to_month, self.to_day, 23, 59)
        in_window = self.time >= start and self.time <= finish
        st = self.strategy
        if buy_signal:
            if in_window:
                st.entry("BUY", st.long)
        if sell_signal:
            if in_window:
                st.entry("SELL", st.short)
        self.plot(up if trend == 1 else NA, title="Up Trend", color=color.green, linewidth=2)
        self.plot(NA if trend == 1 else dn, title="Down Trend", color=color.red, linewidth=2)
