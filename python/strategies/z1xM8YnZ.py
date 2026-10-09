"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : BB Mean Reversion Long + SL
Author       : a4nti
Source URL   : https://www.tradingview.com/script/z1xM8YnZ
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-09 by Claude (pine-to-python skill)

Up to 3 stacked entries (pyramiding=3), all named "Long"; each new signal re-issues
"Exit Long", which moves the stop and target of every open entry.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class BbMeanReversionLong(Script):
    TITLE = "BB Mean Reversion Long + SL"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=100, pyramiding=3)
    SOURCE = {"id": "z1xM8YnZ", "author": "a4nti", "licence": "not stated",
              "url": "https://www.tradingview.com/script/z1xM8YnZ"}

    def init(self):
        self.n = self.input.int(20, "Période SMA", minval=1)
        self.k = self.input.float(2.0, "Écarts-types", minval=0.1, step=0.1)
        self.sl_pct = self.input.float(1.5, "Stop Loss %", minval=0.1, step=0.1)

    def on_bar(self):
        middle, upper, lower = ta.bb(self.close, self.n, self.k)
        self.plot(middle, "Moyenne", color=color.gray)
        self.plot(upper, "Bande haute", color=color.red)
        self.plot(lower, "Bande basse", color=color.green)
        long_entry = ta.crossunder(self.close, lower)
        st = self.strategy
        if long_entry:
            st.entry("Long", st.long)
            st.exit("Exit Long", "Long", stop=self.close * (1 - self.sl_pct / 100), limit=middle)
        self.plotshape(long_entry, title="BUY")
