"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Grover Llorens Activator [Strategy + Analysis]
Author       : alexgrover & Lucía Llorens
Source URL   : https://www.tradingview.com/script/VuYM89Tw-Grover-Llorens-Activator-Strategy-Analysis
Pine version : v4
Licence      : CC BY-SA 4.0
Type         : strategy
Status       : FULL
Converted    : 2026-10-09 by Claude (pine-to-python skill)

`ts` is a self-referencing series (ts[1]); kept as named history. The equity and its
running maximum are plotted as in the original.

Deviations from the original: none.
Not carried over: the fill colour between the equity plots (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, div, nz, pmath, ta


class GroverLlorensActivator(Script):
    TITLE = "Grover Llorens Activator"
    PINE_VERSION = 4
    OVERLAY = False
    STRATEGY = dict()
    SOURCE = {"id": "VuYM89Tw", "author": "alexgrover", "licence": "CC BY-SA 4.0",
              "url": "https://www.tradingview.com/script/VuYM89Tw-Grover-Llorens-Activator-Strategy-Analysis"}

    def init(self):
        self.length = self.input(480)
        self.mult = self.input(14)
        self.src = self.input(self.close)

    def on_bar(self):
        src = self.src
        ts_prev = self.H("ts")[1]
        diff = src - nz(ts_prev, src[1])
        atr = ta.atr(self.length)
        up = ta.crossover(diff, 0)
        dn = ta.crossunder(diff, 0)
        val = ta.valuewhen(up or dn, div(atr, self.length), 0)
        bars = ta.barssince(up or dn)
        if up:
            ts = nz(ts_prev, src.cur) - atr * self.mult
        elif dn:
            ts = nz(ts_prev, src.cur) + atr * self.mult
        else:
            ts = nz(ts_prev, src.cur) + pmath.sign(diff) * val * bars
        self.H("ts").set(ts)
        st = self.strategy
        if up:
            st.entry("Buy", st.long)
        if dn:
            st.entry("Sell", st.short)
        eq = st.equity
        rmax = pmath.max(eq, nz(self.H("rmax")[1]))
        self.H("rmax").set(rmax)
        self.plot(eq, "Equity")
        self.plot(rmax, "Maximum")
