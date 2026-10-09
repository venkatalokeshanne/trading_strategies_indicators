"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Fast Scalper with Stops
Author       : stevenygabbyperez
Source URL   : https://www.tradingview.com/script/SL3hUrJG-Fast-Scalper-with-Stops
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-09 by Claude (pine-to-python skill)

strategy.exit is given trail_points but no trail_offset; Pine never activates a trailing
stop without an offset, so only the fixed 1 % stop works — reproduced exactly.
SL3hUrJG and nOqlAJrw are the same source code published twice.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, ta


class FastScalperWithStops(Script):
    TITLE = "Fast Scalper with Stops"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "SL3hUrJG", "author": "stevenygabbyperez", "licence": "not stated",
              "url": "https://www.tradingview.com/script/SL3hUrJG-Fast-Scalper-with-Stops"}

    def on_bar(self):
        fast = ta.ema(self.close, 5)
        slow = ta.ema(self.close, 13)
        self.plot(fast, color=color.blue)
        self.plot(slow, color=color.red)
        long_condition = ta.crossover(fast, slow)
        short_condition = ta.crossunder(fast, slow)
        st = self.strategy
        if long_condition:
            st.entry("Long", st.long)
            st.exit("Exit Long", "Long", stop=self.close * 0.99,
                    trail_points=div(self.close * 0.02, self.syminfo.mintick))
            self.alert("long")
        if short_condition:
            st.entry("Short", st.short)
            st.exit("Exit Short", "Short", stop=self.close * 1.01,
                    trail_points=div(self.close * 0.02, self.syminfo.mintick))
            self.alert("short")
