"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Simple ZigZag Double
Author       : hamster-bot
Source URL   : https://www.tradingview.com/script/3Q75d98D-Simple-ZigZag-Double
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. Two zig-zag detectors (triple-smoothed EMA turning points, with the lowest low / highest high of the detection window as the pivot price) give the last swing level on each side; a buy-stop at the long detector's up-swing level and a sell-stop at the short detector's down-swing level are renewed at every bar. Optionally only one direction is traded (the other detector's level then becomes the exit stop), a "strict position" tracker waits for a fresh breakout, and everything is closed after the end date.

Deviations from the original: none.
Not carried over: the zig-zag plots and offsets (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, pmath, ta

TIMESTAMP_START = 1388534400000     # timestamp("01 Jan 2014 00:00 +0000")
TIMESTAMP_END = 2556057540000       # timestamp("30 Dec 2050 23:59 +0000")


class SimpleZigZagDouble(Script):
    TITLE = "Simple ZigZag Double"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=100, pyramiding=0, commission_value=0.1)
    SOURCE = {"id": "3Q75d98D", "author": "hamster-bot", "licence": "not stated",
              "url": "https://www.tradingview.com/script/3Q75d98D-Simple-ZigZag-Double"}

    def init(self):
        i = self.input
        self.needlong = i.bool(True, "Use Long", inline="dir_long")
        self.needshort = i.bool(True, "Use Short", inline="dir_short")
        self.length = i.int(5, "Long Length", minval=2, inline="zz")
        self.detection = i.int(3, "Detection", minval=1, inline="zz")
        self.length2 = i.int(5, "Short Length", minval=2, inline="zz2")
        self.detection2 = i.int(3, "Detection", minval=1, inline="zz2")
        self.fixed_lot = i(False, "Fixed lot", inline="lot")
        self.lot_long = i.float(100, "Lot Long, %", minval=1, maxval=10000, inline="lot")
        self.lot_short = i.float(100, "Short, %", minval=1, maxval=10000, inline="lot")
        self.timestamp_start = i.time(TIMESTAMP_START, "Time Start", inline="time")
        self.timestamp_end = i.time(TIMESTAMP_END, "Time End  ", inline="time")
        self.strict_position = i.bool(False, "Strict position")
        self.LOT_LONG = NA
        self.LOT_SHORT = NA
        self.point = NA
        self.point2 = NA
        self.LEVEL_LONG = NA
        self.LEVEL_SHORT = NA
        self.LEVEL_LONG2 = NA
        self.LEVEL_SHORT2 = NA
        self.virtual_pos = 0

    def on_bar(self):
        st = self.strategy
        close = self.close
        true_time = self.time > self.timestamp_start and self.time < self.timestamp_end
        pos_h = self.H("pos")
        pos_prev = pos_h[1]
        pos_h.set(st.position_size)
        if not self.fixed_lot:
            if st.position_size != pos_prev:
                self.LOT_LONG = div(div(st.equity, close) * self.lot_long, 100)
                self.LOT_SHORT = div(div(st.equity, close) * self.lot_short, 100)
        else:
            self.LOT_LONG = self.lot_long
            self.LOT_SHORT = self.lot_short
        low_d = ta.lowest(self.detection)
        high_d = ta.highest(self.detection)
        ema1 = ta.ema(close, pmath.round(self.length / 3 * 3))
        ema2 = ta.ema(ema1, pmath.round(self.length / 3 * 2))
        ema3 = ta.ema(ema2, pmath.round(self.length / 3))
        e3_h = self.H("ema3")
        e3_1, e3_2 = e3_h[1], e3_h[2]
        e3_h.set(ema3)
        z = low_d if (ema3 >= e3_1 and e3_1 < e3_2) else (high_d if (ema3 < e3_1 and e3_1 >= e3_2) else 0.0)
        low_d2 = ta.lowest(self.detection2)
        high_d2 = ta.highest(self.detection2)
        ema12 = ta.ema(close, pmath.round(self.length2 / 3 * 3))
        ema22 = ta.ema(ema12, pmath.round(self.length2 / 3 * 2))
        ema32 = ta.ema(ema22, pmath.round(self.length2 / 3))
        e32_h = self.H("ema32")
        e32_1, e32_2 = e32_h[1], e32_h[2]
        e32_h.set(ema32)
        z2 = low_d2 if (ema32 >= e32_1 and e32_1 < e32_2) else (high_d2 if (ema32 < e32_1 and e32_1 >= e32_2) else 0.0)
        point_1, point2_1 = self.point, self.point2
        self.point = point_1 if z == 0.0 else z
        self.point2 = point2_1 if z2 == 0.0 else z2
        self.LEVEL_LONG = z if self.point > point_1 else self.LEVEL_LONG
        self.LEVEL_SHORT = z if self.point < point_1 else self.LEVEL_SHORT
        self.LEVEL_LONG2 = z2 if self.point2 > point2_1 else self.LEVEL_LONG2
        self.LEVEL_SHORT2 = z2 if self.point2 < point2_1 else self.LEVEL_SHORT2
        close_1 = close[1]
        if self.strict_position:
            if self.virtual_pos == 1 and close <= self.LEVEL_SHORT2 and close_1 > self.LEVEL_SHORT2:
                self.virtual_pos = 0
            if self.virtual_pos == -1 and close >= self.LEVEL_LONG and close_1 < self.LEVEL_LONG:
                self.virtual_pos = 0
            if self.virtual_pos != 1 and close >= self.LEVEL_LONG:
                self.virtual_pos = 1
            if self.virtual_pos != -1 and close <= self.LEVEL_SHORT2:
                self.virtual_pos = -1
        long_entry_condition = self.LEVEL_LONG > 0 and self.needlong and true_time and self.virtual_pos != 1
        short_entry_condition = self.LEVEL_SHORT2 > 0 and self.needshort and true_time and self.virtual_pos != -1
        if long_entry_condition:
            st.entry("Long", st.long, self.LOT_LONG, stop=self.LEVEL_LONG)
        if short_entry_condition:
            st.entry("Short", st.short, self.LOT_SHORT, stop=self.LEVEL_SHORT2)
        if not self.needlong:
            st.cancel("Long")
        if not self.needshort:
            st.exit("Exit Long", "Long", stop=self.LEVEL_SHORT2)
        if not self.needshort:
            st.cancel("Short")
        if not self.needlong:
            st.exit("Exit Short", "Short", stop=self.LEVEL_LONG)
        if self.time > self.timestamp_end:
            st.close_all()
            st.cancel("Long")
            st.cancel("Short")
            self.virtual_pos = 0
