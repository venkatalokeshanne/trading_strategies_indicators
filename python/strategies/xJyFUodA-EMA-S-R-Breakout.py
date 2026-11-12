"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EMA + S/R Breakout
Author       : ankurb171991
Source URL   : https://www.tradingview.com/script/xJyFUodA-EMA-S-R-Breakout
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The close crossing over the highest high of the 20 bars BEFORE this one (ta.highest(high[1], n)) with EMA9
above EMA20 goes long; crossing under the lowest low of the previous 20 bars with EMA9 below EMA20 goes short (reversing).
While a position is open at the close a 12 % target / 6 % stop around the average price is issued, so it first works on the bar
after the fill.

Deviations from the original: none.
Not carried over: the pivot lines, EMA plots and signal shapes (the pivot calls feed no order).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, ta


class EmaSrBreakout(Script):
    TITLE = "EMA + S/R Breakout"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "xJyFUodA", "author": "ankurb171991", "licence": "not stated",
              "url": "https://www.tradingview.com/script/xJyFUodA-EMA-S-R-Breakout"}

    def init(self):
        self.ema9_len = self.input.int(9, "EMA Fast")
        self.ema20_len = self.input.int(20, "EMA Slow")
        self.sr_lookback = self.input.int(20, "S/R Lookback Bars")
        self.target_pct = self.input.float(12.0, "Target %", step=0.5) / 100
        self.sl_pct = self.input.float(6.0, "Stop Loss %", step=0.5) / 100

    def on_bar(self):
        ema9 = ta.ema(self.close, self.ema9_len)
        ema20 = ta.ema(self.close, self.ema20_len)
        res = S(ta.highest(self.high, self.sr_lookback))[1]
        sup = S(ta.lowest(self.low, self.sr_lookback))[1]
        cross_up = ta.crossover(self.close, res)
        cross_dn = ta.crossunder(self.close, sup)
        long_signal = cross_up and ema9 > ema20
        short_signal = cross_dn and ema9 < ema20
        st = self.strategy
        if long_signal:
            st.entry("Long", st.long, comment="BUY")
        if short_signal:
            st.entry("Short", st.short, comment="SELL")
        if st.position_size > 0:
            st.exit("L-Exit", "Long", limit=st.position_avg_price * (1 + self.target_pct),
                    stop=st.position_avg_price * (1 - self.sl_pct), comment_profit="TP +12%", comment_loss="SL -6%")
        if st.position_size < 0:
            st.exit("S-Exit", "Short", limit=st.position_avg_price * (1 - self.target_pct),
                    stop=st.position_avg_price * (1 + self.sl_pct), comment_profit="TP +12%", comment_loss="SL -6%")
        self.plot(ema9, "EMA 9", color=color.orange, linewidth=2)
        self.plot(ema20, "EMA 20", color=color.blue, linewidth=2)
