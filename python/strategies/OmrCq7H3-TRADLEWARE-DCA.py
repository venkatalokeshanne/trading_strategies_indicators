"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : TRADLEWARE-DCA
Author       : cs_lev
Source URL   : https://www.tradingview.com/script/OmrCq7H3-TRADLEWARE-DCA
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A dollar-cost-averaging buyer: inside the date range, every `X` bars (or on a fixed weekday) it buys a fixed quote amount at the bar close (process_orders_on_close; pyramiding
500) until the total invested reaches the initial capital. Everything is closed on the last confirmed historical bar (or after the end date).

Deviations from the original: none.
Not carried over: the equity plot.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, div


class TradlewareDca(Script):
    TITLE = "TRADLEWARE-DCA"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, commission_type="percent", commission_value=0.1, slippage=3, pyramiding=500,
                    process_orders_on_close=True)
    SOURCE = {"id": "OmrCq7H3", "author": "cs_lev", "licence": "not stated",
              "url": "https://www.tradingview.com/script/OmrCq7H3-TRADLEWARE-DCA"}

    def init(self):
        g = "Date Range"
        self.start_year = self.input.int(2018, "Start year", minval=2000, maxval=2099, group=g)
        self.start_month = self.input.int(1, "Start month", minval=1, maxval=12, group=g)
        self.start_day = self.input.int(1, "Start day", minval=1, maxval=31, group=g)
        self.end_year = self.input.int(2099, "End year", minval=2000, maxval=2099, group=g)
        self.end_month = self.input.int(12, "End month", minval=1, maxval=12, group=g)
        self.end_day = self.input.int(31, "End day", minval=1, maxval=31, group=g)
        g = "Frequency"
        self.based_on_day_of_week = self.input.bool(False, "Use Day of Week Mode", group=g)
        self.buy_on_day_of_week = self.input.int(2, "Day of Week", minval=1, maxval=7, group=g)
        self.based_on_x_bars = self.input.int(30, "Every X Bars", minval=1)
        self.to_invest_quote = self.input.float(100.0, "Amount per buy (quote currency)", minval=1.0, group="Strategy")
        self.invested_capital = 0.0
        self.last_buy_bar_index = 0

    def on_bar(self):
        start_date = self.timestamp(self.start_year, self.start_month, self.start_day, 0, 0)
        end_date = self.timestamp(self.end_year, self.end_month, self.end_day, 23, 59)
        to_invest_base = div(self.to_invest_quote, self.close)
        time_condition = self.time >= start_date and self.time <= end_date and not self.barstate.islastconfirmedhistory
        if self.based_on_day_of_week:
            freq_condition = self.dayofweek(self.time) == self.buy_on_day_of_week
        else:
            freq_condition = (self.last_buy_bar_index == 0) or (self.bar_index >= self.last_buy_bar_index + self.based_on_x_bars)
        long_condition = freq_condition and time_condition
        st = self.strategy
        if long_condition:
            self.last_buy_bar_index = self.bar_index
            if self.invested_capital + self.to_invest_quote <= st.initial_capital:
                st.entry("dca", st.long, qty=to_invest_base)
                self.invested_capital += self.to_invest_quote
        if self.barstate.islastconfirmedhistory or self.time > end_date:
            st.close_all()
