"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Gap Filling Strategy
Author       : alexgrover
Source URL   : https://www.tradingview.com/script/ghocsiv7-Gap-Filling-Strategy
Pine version : v4
Licence      : MPL 2.0
Type         : strategy
Status       : FULL
Converted    : 2026-10-09 by Claude (pine-to-python skill)

ses = change(time("D")) is true on the first bar of each day, so the strategy is meant for
intraday charts (on a daily chart every bar is a new session).

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, pmath, ta, truthy


class GapFillingStrategy(Script):
    TITLE = "Gap Filling Strategy"
    PINE_VERSION = 4
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "ghocsiv7", "author": "alexgrover", "licence": "MPL 2.0",
              "url": "https://www.tradingview.com/script/ghocsiv7-Gap-Filling-Strategy"}

    def init(self):
        self.invert = self.input(False)
        self.clw = self.input("New Session", "Close When:",
                              options=["New Session", "New Gap", "Reverse Position"])

    def on_bar(self):
        ses = truthy(ta.change(self.time_fn("D")))
        o, c = self.open, self.close
        upgap = o > self.high[1] and pmath.min(c.cur, o.cur) > pmath.max(c[1], o[1])
        dngap = o < self.low[1] and pmath.min(c[1], o[1]) > pmath.max(c.cur, o.cur)
        val = pmath.max(c[1], o[1]) if upgap else pmath.min(c[1], o[1])
        lim = ta.valuewhen(ses and (upgap or dngap), val, 0)
        st = self.strategy
        if self.clw == "New Session":
            close_when = ses
        elif self.clw == "New Gap":
            close_when = ses and (upgap or dngap)
        else:
            close_when = False
        if close_when:
            st.close_all()
        if self.invert:
            if ses and upgap:
                st.entry("Buy", st.long)
            if ses and dngap:
                st.entry("Sell", st.short)
        else:
            if ses and dngap:
                st.entry("Buy", st.long)
            if ses and upgap:
                st.entry("Sell", st.short)
        if self.invert:
            st.exit("ExitBuy", "Buy", stop=lim)
            st.exit("ExitSell", "Sell", stop=lim)
        else:
            st.exit("ExitBuy", "Buy", limit=lim)
            st.exit("ExitSell", "Sell", limit=lim)
        self.plot(lim, "Limit/Stop")
