"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : SPY 200SMA +4% Entry -3% Exit Strategy
Author       : freefighter07
Source URL   : https://www.tradingview.com/script/QEVAQHl6-SPY-200SMA-4-Entry-3-Exit-Strategy-QQQ-TQQQ
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. After the start date, a close more than 4 % above SMA(200) enters long when flat (100 % of
equity); a close more than 3 % below it closes the long at the next open.

Deviations from the original: none.
Not carried over: the 366-day "anniversary" marker, the BUY / SELL labels and the SMA / threshold plots (cosmetic: they
feed no order).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class Spy200SmaBand(Script):
    TITLE = "SPY 200SMA +4% Entry -3% Exit Strategy"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "QEVAQHl6", "author": "freefighter07", "licence": "not stated",
              "url": "https://www.tradingview.com/script/QEVAQHl6-SPY-200SMA-4-Entry-3-Exit-Strategy-QQQ-TQQQ"}

    def init(self):
        self.sma_length = self.input.int(200, title="SMA Period", minval=1)
        self.entry_threshold = self.input.float(0.04, title="Entry Threshold (%)", step=0.01)
        self.exit_threshold = self.input.float(0.03, title="Exit Threshold (%)", step=0.01)
        self.start_year = self.input.int(1995, "Start Year")
        self.start_month = self.input.int(1, "Start Month")
        self.start_day = self.input.int(1, "Start Day")

    def on_bar(self):
        start_time = self.timestamp(self.start_year, self.start_month, self.start_day, 0, 0)
        is_after_start = self.time >= start_time
        sma200 = ta.sma(self.close, self.sma_length)
        upper_threshold = sma200 * (1 + self.entry_threshold)
        lower_threshold = sma200 * (1 - self.exit_threshold)
        enter_long = self.close > upper_threshold
        exit_long = self.close < lower_threshold
        st = self.strategy
        if is_after_start:
            if enter_long and st.position_size == 0:
                st.entry("Buy", st.long)
            if exit_long and st.position_size > 0:
                st.close("Buy")
        self.plot(sma200, title="200 SMA", color=color.fuchsia)
        self.plot(upper_threshold, title="Entry Threshold (+4%)", color=color.green)
        self.plot(lower_threshold, title="Exit Threshold (-3%)", color=color.red)
