"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Simple Long Only Bot
Author       : mikebarone1104
Source URL   : https://www.tradingview.com/script/7YZu94L1-Simple-Long-Only-Bot
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-09 by Claude (pine-to-python skill)

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class SimpleLongOnlyBot(Script):
    TITLE = "Simple Long Only Bot"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "7YZu94L1", "author": "mikebarone1104", "licence": "not stated",
              "url": "https://www.tradingview.com/script/7YZu94L1-Simple-Long-Only-Bot"}

    def on_bar(self):
        ema50 = ta.ema(self.close, 50)
        ema200 = ta.ema(self.close, 200)
        uptrend = self.close > ema200
        buy_signal = ta.crossover(self.close, ema50) and uptrend
        sell_signal = ta.crossunder(self.close, ema50)
        st = self.strategy
        if buy_signal:
            st.entry("LONG", st.long)
        if sell_signal:
            st.close("LONG")
        self.plot(ema50, color=color.blue)
        self.plot(ema200, color=color.red)
