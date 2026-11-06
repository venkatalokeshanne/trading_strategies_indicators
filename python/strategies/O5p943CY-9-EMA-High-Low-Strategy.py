"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : 9 EMA (High/Low) Strategy
Author       : legalOatmeal29171
Source URL   : https://www.tradingview.com/script/O5p943CY-9-EMA-High-Low-Strategy
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. Inside the date range, a close above the 9 EMA of the highs goes long (a close below the 9 EMA of the lows goes short), closing the opposite side first; a percentage stop / target around the average price is re-issued at every bar of the position
(it works from the bar after the fill). Positions are closed outside the date range.

Deviations from the original: none.
Not carried over: the monthly P&L table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, ta


class NineEmaHighLow(Script):
    TITLE = "9 EMA (High/Low) Strategy"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=1, initial_capital=100000, commission_type="percent", commission_value=0)
    SOURCE = {"id": "O5p943CY", "author": "legalOatmeal29171", "licence": "not stated",
              "url": "https://www.tradingview.com/script/O5p943CY-9-EMA-High-Low-Strategy"}

    def init(self):
        i = self.input
        self.ema_len = i.int(9, "EMA Length", minval=1)
        self.tgt_pct = i.float(0.62, "Target %", minval=0.01, step=0.01)
        self.sl_pct = i.float(0.3, "Stop-Loss %", minval=0.01, step=0.01)
        self.start_date = i.int(1, "Start Date", minval=1, maxval=31)
        self.start_month = i.int(7, "Start Month", minval=1, maxval=12)
        self.start_year = i.int(2020, "Start Year", minval=1800, maxval=2100)
        self.end_date = i.int(31, "End Date", minval=1, maxval=31)
        self.end_month = i.int(12, "End Month", minval=1, maxval=12)
        self.end_year = i.int(2027, "End Year", minval=1800, maxval=2100)

    def on_bar(self):
        st = self.strategy
        tz = self.syminfo.timezone
        in_date_range = (self.time >= self.timestamp(tz, self.start_year, self.start_month, self.start_date, 0, 0)
                         and self.time < self.timestamp(tz, self.end_year, self.end_month, self.end_date, 0, 0))
        ema_high = ta.ema(self.high, self.ema_len)
        ema_low = ta.ema(self.low, self.ema_len)
        buy_signal = self.close > ema_high
        sell_signal = self.close < ema_low
        in_long = st.position_size > 0
        in_short = st.position_size < 0
        if in_date_range and buy_signal and not in_long:
            if in_short:
                st.close("Short", comment="Short->Long")
            st.entry("Long", st.long, comment="BUY")
        if in_date_range and sell_signal and not in_short:
            if in_long:
                st.close("Long", comment="Long->Short")
            st.entry("Short", st.short, comment="SELL")
        if not in_date_range:
            st.close_all(comment="Date Range End")
        entry_price = st.position_avg_price
        if in_long:
            st.exit("Long Exit", from_entry="Long", limit=entry_price * (1 + self.tgt_pct / 100), stop=entry_price * (1 - self.sl_pct / 100),
                    comment_profit="Long TP", comment_loss="Long SL")
        if in_short:
            st.exit("Short Exit", from_entry="Short", limit=entry_price * (1 - self.tgt_pct / 100), stop=entry_price * (1 + self.sl_pct / 100),
                    comment_profit="Short TP", comment_loss="Short SL")
