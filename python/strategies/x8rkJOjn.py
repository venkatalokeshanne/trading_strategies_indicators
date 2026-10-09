"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : anh Manh dep trai
Author       : tinhuyen412
Source URL   : https://www.tradingview.com/script/x8rkJOjn
Pine version : v6
Licence      : MPL 2.0
Type         : strategy
Status       : FULL
Converted    : 2026-10-09 by Claude (pine-to-python skill)

As written, the stop is multiplied by (1 + M) on every bar in a position (M = 1.0 doubles
it), so it soon sits above the price and the next bar exits — reproduced exactly.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, ta


class AnhManhDepTrai(Script):
    TITLE = "anh Manh dep trai"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "x8rkJOjn", "author": "tinhuyen412", "licence": "MPL 2.0",
              "url": "https://www.tradingview.com/script/x8rkJOjn"}

    def init(self):
        self.x = self.input.int(3, "Số nến xanh")
        self.n = self.input.int(5, "Nhập N")
        self.m = self.input.float(1.0, "Nhập M")
        self.count_green = 0          # var countGreen = 0
        self.stop_loss = NA           # var float stopLoss = na

    def on_bar(self):
        st = self.strategy
        self.count_green = self.count_green + 1 if self.open < self.close else 0
        avg_val = ta.sma(div(self.open + self.low, 2), self.n)
        if self.count_green == self.x and st.position_size == 0:
            st.entry("Buy", st.long)
            self.stop_loss = avg_val
        if st.position_size > 0:
            self.stop_loss = self.stop_loss * (1 + self.m)
        if st.position_size > 0:
            st.exit("Exit Buy", from_entry="Buy", stop=self.stop_loss)
        self.plot(self.close)
        self.plot(self.stop_loss, color=color.red)
