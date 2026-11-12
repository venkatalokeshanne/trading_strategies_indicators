"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : TRADLEWARE-HODL
Author       : cs_lev
Source URL   : https://www.tradingview.com/script/wgsvzsT3-TRADLEWARE-HODL
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Buy and hold: one long from the start date, closed on the second to last bar
(its market order fills at the open of the last bar) or at the end date. `strategy.closedtrades == 0` makes
it a single trade. fill_orders_on_standard_ohlc has no effect on pinelib's fill model.

Deviations from the original: none.
Not carried over: the equity plot (data window only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color


class TradlewareHodl(Script):
    TITLE = "TRADLEWARE-HODL"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=99.95,
                    commission_type="percent", commission_value=0.1, slippage=3, pyramiding=0)
    SOURCE = {"id": "wgsvzsT3", "author": "cs_lev", "licence": "not stated",
              "url": "https://www.tradingview.com/script/wgsvzsT3-TRADLEWARE-HODL"}

    def init(self):
        self.start_year = self.input.int(2018, "Start year", minval=2000, maxval=2099, group="Date Range")
        self.start_month = self.input.int(1, "Start month", minval=1, maxval=12, group="Date Range")
        self.start_day = self.input.int(1, "Start day", minval=1, maxval=31, group="Date Range")
        self.end_year = self.input.int(2099, "End year", minval=2000, maxval=2099, group="Date Range")
        self.end_month = self.input.int(12, "End month", minval=1, maxval=12, group="Date Range")
        self.end_day = self.input.int(31, "End day", minval=1, maxval=31, group="Date Range")

    def on_bar(self):
        start_date = self.timestamp(self.start_year, self.start_month, self.start_day, 0, 0)
        end_date = self.timestamp(self.end_year, self.end_month, self.end_day, 23, 59)
        st = self.strategy
        if self.time >= start_date and st.closedtrades == 0 and st.position_size == 0:
            st.entry("hodl", st.long)
        if self.time >= end_date or self.bar_index >= self.last_bar_index - 1:
            st.close_all()
        self.plot(st.equity, title="Equity", color=color.teal)
