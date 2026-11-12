"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Grid Like Strategy
Author       : alexgrover
Source URL   : https://www.tradingview.com/script/oxvR5vMy-Grid-Like-Strategy
Pine version : v4
Licence      : CC BY-SA 4.0
Type         : strategy
Status       : FULL
Converted    : 2026-10-09 by Claude (pine-to-python skill)

Martingale sizing reads the strategy's own win/loss counters (change(strategy.losstrades)).
`point` is an absolute price distance (2.0), as in the original.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, nz, ta, truthy


class GridLikeStrategy(Script):
    TITLE = "Grid Like Strategy"
    PINE_VERSION = 4
    OVERLAY = True
    STRATEGY = dict(process_orders_on_close=True)
    SOURCE = {"id": "oxvR5vMy", "author": "alexgrover", "licence": "CC BY-SA 4.0",
              "url": "https://www.tradingview.com/script/oxvR5vMy-Grid-Like-Strategy"}

    def init(self):
        self.point = self.input(2.0)
        self.os = self.input(1, "Order Size")
        self.mf = self.input(2.0, "Martingale Multiplier")
        self.anti = self.input(False, "Anti Martingale")

    def on_bar(self):
        b_prev = self.H("baseline")[1]
        moved = self.close > b_prev + self.point or self.close < b_prev - self.point
        baseline = nz(self.close.cur if moved else b_prev, self.close.cur)
        self.H("baseline").set(baseline)
        upper = baseline + self.point
        lower = baseline - self.point
        st = self.strategy
        loss = ta.change(st.losstrades)
        win = ta.change(st.wintrades)
        size_prev = self.H("size")[1]
        if self.anti:
            size = size_prev * self.mf if truthy(win) else (self.os if truthy(loss) else nz(size_prev, self.os))
        else:
            size = size_prev * self.mf if truthy(loss) else (self.os if truthy(win) else nz(size_prev, self.os))
        self.H("size").set(size)
        if baseline > b_prev:
            st.entry("Buy", st.long, qty=size)
            st.exit("buy/tp/sl", "Buy", stop=lower, limit=upper)
        if baseline < b_prev:
            st.entry("Sell", st.short, qty=size)
            st.exit("sell/tp/sl", "Sell", stop=upper, limit=lower)
        self.plot(baseline, "Plot")
