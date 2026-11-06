"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : 1-2-3 Pattern + ATR Filter (Ineficient market)
Author       : abib14bis
Source URL   : https://www.tradingview.com/script/t578EfVb
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). Alternating confirmed pivots (high only while the last was a low or none, and vice versa) are kept in a three-slot list; when a new low
completes a higher-low "1-2-3" (point 3 above point 1 and below point 2) a long is signalled (the mirror gives a short), provided ATR% is not elevated against its 50-bar average. A signal
enters when flat; a take-profit limit and a stop around the average price are issued while in a position, and a time stop closes it after the configured number of bars.

Deviations from the original: none.
Not carried over: the 1-2-3 labels, pattern lines and the BUY / SELL shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, parray, ta


class OneTwoThree(Script):
    TITLE = "1-2-3 Pattern + ATR Filter"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="cash", default_qty_value=1000, commission_type="percent", commission_value=0.055,
                    slippage=2, process_orders_on_close=True, pyramiding=0)
    SOURCE = {"id": "t578EfVb", "author": "abib14bis", "licence": "not stated",
              "url": "https://www.tradingview.com/script/t578EfVb"}

    def init(self):
        g = "Signal"
        self.prd = self.input.int(20, "Pivot lookback (prd)", minval=2, group=g)
        self.atr_filter_max = self.input.float(0.85, "ATR ratio max (0 = off)", step=0.05, group=g)
        self.allow_long = self.input.bool(True, "Allow Long", group=g)
        self.allow_short = self.input.bool(True, "Allow Short", group=g)
        g = "Exits"
        self.tp_pct = self.input.float(0.98, "Take Profit %", step=0.01, minval=0.0, group=g)
        self.sl_pct = self.input.float(9.5, "Stop Loss %", step=0.1, minval=0.0, group=g)
        self.time_stop_bars = self.input.int(480, "Time stop (bars)", minval=1, group=g)
        self.pvts = [0.0, 0.0, 0.0]
        self.idx = [0, 0, 0]
        self.pos = 0
        self.pattern = True
        self.entry_bar = NA

    def on_bar(self):
        atr_val = ta.atr(14)
        atr_pct = div(atr_val, self.close) * 100
        atr_sma50 = ta.sma(atr_pct, 50)
        atr_ratio = div(atr_pct, atr_sma50) if atr_sma50 > 0 else 1.0
        atr_ok = self.atr_filter_max <= 0 or atr_ratio <= self.atr_filter_max
        pvt_hi = ta.pivothigh(self.high, self.prd, self.prd)
        pvt_lo = ta.pivotlow(self.low, self.prd, self.prd)
        just_added_high = False
        just_added_low = False
        if not na(pvt_hi) and self.pos <= 0:
            parray.pop(self.pvts)
            parray.pop(self.idx)
            parray.unshift(self.pvts, self.high[self.prd])
            parray.unshift(self.idx, self.bar_index - self.prd)
            self.pos = 1
            just_added_high = True
        if not na(pvt_lo) and self.pos >= 0:
            parray.pop(self.pvts)
            parray.pop(self.idx)
            parray.unshift(self.pvts, self.low[self.prd])
            parray.unshift(self.idx, self.bar_index - self.prd)
            self.pos = -1
            just_added_low = True
        long_sig = False
        short_sig = False
        if self.pattern and parray.get(self.idx, 2) > 0 and atr_ok:
            p0 = parray.get(self.pvts, 0)
            p1 = parray.get(self.pvts, 1)
            p2 = parray.get(self.pvts, 2)
            if just_added_low and p0 > p2 and p0 < p1:
                long_sig = True
                self.pattern = False
            if just_added_high and p0 < p2 and p0 > p1:
                short_sig = True
                self.pattern = False
        if ta.change(parray.get(self.pvts, 1)) != 0:
            self.pattern = True
        st = self.strategy
        if self.allow_long and long_sig and st.position_size == 0:
            st.entry("Long", st.long)
            self.entry_bar = self.bar_index
        if self.allow_short and short_sig and st.position_size == 0:
            st.entry("Short", st.short)
            self.entry_bar = self.bar_index
        avg = st.position_avg_price
        if st.position_size > 0:
            st.exit("Exit Long", "Long", limit=avg * (1 + self.tp_pct / 100), stop=avg * (1 - self.sl_pct / 100))
            if not na(self.entry_bar) and self.bar_index - self.entry_bar >= self.time_stop_bars:
                st.close("Long", comment="Time stop")
        if st.position_size < 0:
            st.exit("Exit Short", "Short", limit=avg * (1 - self.tp_pct / 100), stop=avg * (1 + self.sl_pct / 100))
            if not na(self.entry_bar) and self.bar_index - self.entry_bar >= self.time_stop_bars:
                st.close("Short", comment="Time stop")
        if st.position_size == 0:
            self.entry_bar = NA
