"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Surgical Sweep - Original Restored
Author       : Abhivish
Source URL   : https://www.tradingview.com/script/25Ffpyo0-Surgical-Sweep-Original-Restored
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The latest confirmed pivot high / low (5 bars each side) are the resistance / support levels. A
liquidity sweep (prior bar's high and close above resistance, this close back below it, on a volume spike of 1.2 x SMA20)
sells; the mirror below support buys. Entries fire only on weekdays (exchange time zone) and reverse the open trade.
100% of equity per trade, no stops: positions are held until the opposite signal.

Deviations from the original: none.
Not carried over: the level lines, signal labels and the blue/red/purple sweep counters (they only drive a shape).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, na, ta


class SurgicalSweep(Script):
    TITLE = "Surgical Sweep - Original Restored"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "25Ffpyo0", "author": "Abhivish", "licence": "not stated",
              "url": "https://www.tradingview.com/script/25Ffpyo0-Surgical-Sweep-Original-Restored"}

    def init(self):
        self.lookback = self.input.int(5, "Pivot Sensitivity")
        self.vol_mult = self.input.float(1.2, "Volume Spike Filter")
        self.line_len = self.input.int(15, "Line Length")
        self.res_level = NA
        self.sup_level = NA

    def on_bar(self):
        avg_vol = ta.sma(self.volume, 20)
        is_high_vol = self.volume > (avg_vol * self.vol_mult)
        is_weekday = self.dayofweek() != 7 and self.dayofweek() != 1
        hi = ta.pivothigh(self.high, self.lookback, self.lookback)
        lo = ta.pivotlow(self.low, self.lookback, self.lookback)
        if not na(hi):
            self.res_level = hi
        if not na(lo):
            self.sup_level = lo
        h, c, l = S(self.high), S(self.close), S(self.low)
        sell_signal = h[1] > self.res_level and c[1] > self.res_level and c[0] < self.res_level and is_high_vol
        buy_signal = l[1] < self.sup_level and c[1] < self.sup_level and c[0] > self.sup_level and is_high_vol
        st = self.strategy
        if buy_signal and is_weekday:
            st.entry("Long", st.long)
        if sell_signal and is_weekday:
            st.entry("Short", st.short)
