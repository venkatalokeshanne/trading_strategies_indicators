"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : TASC 2026.08 An Ag Selling Model
Author       : PineCodersTASC
Source URL   : https://www.tradingview.com/script/VFzCk3HX-TASC-2026-08-An-Ag-Selling-Model
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A crop-year selling program: the harvest month (default November) starts a new crop year and
switches selling off; selling switches on again in the month `delayMonths + 1` after harvest (default February). While on, a
high at or above SMA(40) + 2.5 ATR(20) sells short ("First sale" when nothing is open; later "Sell" orders need at least
`dBetween` bars since the last sale, counted only while trades are open); up to 3 open sales (pyramiding 3). While selling
is off, every bar closes everything at the next open.

Deviations from the original: none.
Not carried over: the background colours and plots (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, na, ta


class AgSellingModel(Script):
    TITLE = "TASC 2026.08 An Ag Selling Model"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=15000000, pyramiding=3, slippage=1,
                    commission_type="cash_per_contract", commission_value=300)
    SOURCE = {"id": "VFzCk3HX", "author": "PineCodersTASC", "licence": "not stated",
              "url": "https://www.tradingview.com/script/VFzCk3HX-TASC-2026-08-An-Ag-Selling-Model"}

    def init(self):
        g1, g2 = "Average & sell level settings", "Strategy settings"
        self.src = self.input.source(self.close, "Source", group=g1)
        self.length = self.input.int(40, "MA length", group=g1)
        self.atr_len = self.input.int(20, "ATR length", group=g1)
        self.atr_multi = self.input.float(2.5, "ATR factor", group=g1)
        self.start_crop_year = self.input.int(11, "Month of harvest", minval=1, maxval=12, group=g2)
        self.delay_months = self.input.int(2, "Delay in months after harvest", minval=0, maxval=11, group=g2)
        self.d_between = self.input.int(30, "Days between trades", minval=1, group=g2)
        self.active = False
        self.d_since = 0

    def on_bar(self):
        st = self.strategy
        if st.opentrades > 0:
            self.d_since += 1
        trend = ta.sma(self.src, self.length)
        atr = ta.atr(self.atr_len)
        sell_level = trend + atr * self.atr_multi
        month = self.month()
        month_h, harvest_h = self.H("month"), self.H("harvest")
        prev_month = month_h[1]
        prev_harvest = harvest_h[1]
        prev_harvest = False if na(prev_harvest) else bool(prev_harvest)
        is_harvest_month = month == self.start_crop_year
        new_crop_yr = is_harvest_month and not prev_harvest
        begin_sale_month = (self.start_crop_year + self.delay_months + 1) % 12
        if begin_sale_month == 0:
            begin_sale_month = 12
        if new_crop_yr:
            self.active = False
            self.d_since = 0
        if month == begin_sale_month and prev_month != begin_sale_month:
            self.active = True
        if self.active and self.high >= sell_level:
            if st.opentrades == 0:
                st.entry("First sale", st.short)
                self.d_since = 0
            elif self.d_since >= self.d_between:
                st.entry("Sell", st.short)
                self.d_since = 0
        if not self.active:
            st.close_all("Cover")
        month_h.set(month)
        harvest_h.set(is_harvest_month)
        self.plot(trend, "Average", color=color.orange)
        self.plot(sell_level, "Sell level", color=color.blue)
